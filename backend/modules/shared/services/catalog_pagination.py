"""SQL pagination for catalogs with the standard active-state filter."""


def catalog_page(model, name_column, *, activos, orden, page, per_page):
    query = model.query
    if activos == "true":
        query = query.filter(model.deleted_at.is_(None))
    elif activos == "false":
        query = query.filter(model.deleted_at.isnot(None))

    total = query.count()
    direction = name_column.desc() if orden == "desc" else name_column.asc()
    items = (
        query.order_by(direction, model.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [item.serialize() for item in items], total
