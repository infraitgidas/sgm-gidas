from math import ceil

from flask import current_app, jsonify, request

from modules.search.services.search_service import SearchService
from modules.shared.controllers.responses import exception_response
from modules.shared.exceptions import ValidationError


class SearchController:

    @staticmethod
    def buscar():
        try:
            query_text = request.args.get("q", "").strip()
            orden = request.args.get("orden", "alf_asc")
            eliminados = request.args.get("eliminados", "false").strip().lower()
            page = SearchController._parse_positive_int("page", default=1)
            per_page = SearchController._parse_positive_int("per_page", default=9)
            per_page = min(per_page, current_app.config["SEARCH_MAX_PER_PAGE"])

            if not query_text:
                raise ValidationError('El parametro "q" es obligatorio')

            if len(query_text) < 2:
                raise ValidationError("El texto debe tener al menos 2 caracteres")

            if len(query_text) > current_app.config["SEARCH_MAX_QUERY_LENGTH"]:
                raise ValidationError(
                    "El texto de busqueda es demasiado largo. Ingrese una consulta mas breve."
                )

            if eliminados not in ("false", "true", "all"):
                raise ValidationError(
                    'El parametro "eliminados" debe ser "false", "true" o "all"'
                )

            paginated_results, total_resultados = SearchService.search_page(
                query_text=query_text,
                orden=orden,
                eliminados=eliminados,
                page=page,
                per_page=per_page,
                max_scan_per_model=current_app.config["SEARCH_MAX_SCAN_PER_MODEL"],
            )
            total_pages = max(1, ceil(total_resultados / per_page))

            response = jsonify({
                "query": query_text,
                "orden": orden,
                "eliminados": eliminados,
                "total_resultados": total_resultados,
                "resultados": paginated_results,
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_resultados,
                    "total_pages": total_pages,
                },
            })
            response.headers["Cache-Control"] = "private, no-store"
            return response, 200

        except Exception as error:
            return exception_response(error, operation="realizar busqueda global")

    @staticmethod
    def _parse_positive_int(param_name: str, default: int) -> int:
        raw_value = request.args.get(param_name, str(default))

        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ValidationError(f'El parametro "{param_name}" debe ser numerico') from exc

        if value < 1:
            raise ValidationError(f'El parametro "{param_name}" debe ser mayor o igual a 1')

        return value
