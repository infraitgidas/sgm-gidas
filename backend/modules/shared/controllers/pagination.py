from flask import current_app, g, has_request_context
from sqlalchemy import String, cast, func, or_, true
from sqlalchemy.sql.sqltypes import String as StringType

from modules.shared.exceptions import ValidationError
from modules.shared.services.tenant_scope import _read_entity_predicate

from modules.shared.controllers.responses import error_response, paginated_response


DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 9
DEFAULT_MAX_PER_PAGE = 100
PAGINATION_PARAMS = {"page", "per_page"}
VALID_ACTIVOS_VALUES = {"true", "false", "all"}
VALID_ORDER_VALUES = {"asc", "desc"}


def pagination_requested(args) -> bool:
    return any(param in args for param in PAGINATION_PARAMS)


def _positive_int(value, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} debe ser un numero entero positivo") from exc

    if parsed < 1:
        raise ValueError(f"{field_name} debe ser un numero entero positivo")

    return parsed


def parse_pagination_params(args):
    default_per_page = current_app.config.get(
        "PAGINATION_DEFAULT_PER_PAGE",
        DEFAULT_PER_PAGE,
    )
    max_per_page = current_app.config.get(
        "PAGINATION_MAX_PER_PAGE",
        DEFAULT_MAX_PER_PAGE,
    )

    page = _positive_int(args.get("page", DEFAULT_PAGE), "page")
    per_page = _positive_int(args.get("per_page", default_per_page), "per_page")

    if per_page > max_per_page:
        raise ValueError(f"per_page no puede superar {max_per_page}")

    activos = args.get("activos", "true").strip().lower()
    if activos not in VALID_ACTIVOS_VALUES:
        raise ValueError("activos debe ser true, false o all")

    orden = args.get("orden", "asc").strip().lower()
    if orden not in VALID_ORDER_VALUES:
        raise ValueError("orden debe ser asc o desc")

    return {
        "page": page,
        "per_page": per_page,
        "activos": activos,
        "orden": orden,
    }


def paginate_query(query, page: int, per_page: int):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


def catalog_page_response(service, args):
    try:
        params = parse_pagination_params(args)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
    data, total = service.get_page(**params)
    return paginated_response(
        data,
        page=params["page"],
        per_page=params["per_page"],
        total=total,
        meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
    )


def filtered_page_response(service, filters, args):
    try:
        params = parse_pagination_params(args)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
    data, total = service.get_page(filters, params["page"], params["per_page"])
    return paginated_response(
        data,
        page=params["page"],
        per_page=params["per_page"],
        total=total,
        meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
    )


def table_scope_predicate(model):
    group_id = getattr(g, "current_grupo_utn_id", None) if has_request_context() else None
    predicate = _read_entity_predicate(model, group_id) if group_id is not None else None
    return predicate if predicate is not None else true()


def table_query_page(query, model, args, fields, *, default_sort,
                     searchable, facets=(), facet_labels=None, extra_search=None,
                     facet_joins=None, filter_conditions=None, sortable=None):
    """Filter/count in SQL; serialize only the requested page.

    Facets belong to the full active/memory scope, before user filters, so
    dropdown options do not disappear when selecting a page or another filter.
    Expressions are supplied by each domain service, never by the client.
    """
    # Count/projection statements may have no entity in column_descriptions.
    # Keep the root UCT predicate explicit for totals and every facet as well.
    query = query.filter(table_scope_predicate(model))
    try:
        params = parse_pagination_params(args)
        if "ids" in args:
            raw_ids = args.get("ids", "")
            if len(raw_ids) > 100000:
                raise ValueError("Revise el filtro de memoria.")
            ids = [int(value) for value in raw_ids.split(",") if value]
            if any(value < 1 for value in ids):
                raise ValueError("Revise el filtro de memoria.")
            query = query.filter(model.id.in_(ids))
        sort = args.get("sort", default_sort)
        direction = args.get("direction", "asc")
        if sort not in fields or (sortable is not None and sort not in sortable) or direction not in VALID_ORDER_VALUES:
            raise ValueError("Revise el orden solicitado.")
        needle = args.get("q", "").strip()
        if len(needle) > 200:
            raise ValueError("La busqueda admite hasta 200 caracteres.")
    except (ValueError, TypeError) as error:
        raise ValidationError(str(error)) from error

    options = {}
    for key in facets:
        expression = fields[key]
        label = (facet_labels or {}).get(key, expression)
        facet_query = (facet_joins or {}).get(key, lambda scoped: scoped)(query)
        values = facet_query.order_by(None).with_entities(expression, label).distinct().all()
        pairs = {(str(value), str(name or value)) for value, name in values
                 if value is not None and str(value)}
        options[key] = [{"value": value, "label": name}
                        for value, name in sorted(pairs, key=lambda pair: pair[1].lower())]

    if needle:
        conditions = [func.lower(cast(fields[key], String)).contains(needle.lower(), autoescape=True)
                      for key in searchable]
        if extra_search is not None:
            conditions.append(extra_search(needle.lower()))
        query = query.filter(or_(*conditions))
    for key in facets:
        value = args.get(f"filter_{key}", "").strip()
        if value:
            condition = (filter_conditions or {}).get(key)
            query = query.filter(condition(value) if condition else
                                 func.lower(func.trim(cast(fields[key], String))) == value.lower())

    total = query.order_by(None).count()
    expression = fields[sort]
    if isinstance(expression.type, StringType):
        expression = func.lower(expression)
    ordering = expression.desc() if direction == "desc" else expression.asc()
    rows = query.order_by(None).order_by(ordering, model.id.asc()).offset(
        (params["page"] - 1) * params["per_page"]
    ).limit(params["per_page"]).all()
    return [row.serialize() for row in rows], total, options


def table_page_response(service, filters, args):
    try:
        params = parse_pagination_params(args)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    data, total, options = service.get_table_page(filters, args)
    return paginated_response(data, params["page"], params["per_page"], total,
                              meta={"options": options})
