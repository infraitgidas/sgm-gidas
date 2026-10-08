import { useLocation, useNavigate } from "react-router-dom";
import { useSearch } from "@/modules/search/hooks/useSearch";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { highlight } from "@/utils/highlight";
import { Search, X, Filter, BookOpen, Users, Folder, FileText, Award, TrendingUp, Microscope, Briefcase, Calendar as CalendarIcon, Building, Zap } from "lucide-react";
import { useState, useMemo } from "react";
import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import { parseCivilDate, toCivilDateString } from "@/utils/dateTime";
import {
  resolveFrontendUrl,
  SEARCH_MAX_QUERY_LENGTH,
  type Orden,
  type SearchResult,
} from "@/modules/search/services/searchService";

// Configuración de colores e iconos por tipo de entidad
const TYPE_CONFIG: Record<string, { color: string; bgColor: string; icon: React.ElementType }> = {
  "Autor": { color: "text-blue-700", bgColor: "bg-blue-50", icon: BookOpen },
  "Documentación": { color: "text-blue-700", bgColor: "bg-blue-50", icon: FileText },
  "Investigador": { color: "text-purple-700", bgColor: "bg-purple-50", icon: Microscope },
  "Becario": { color: "text-indigo-700", bgColor: "bg-indigo-50", icon: Users },
  "Proyecto de Investigación": { color: "text-green-700", bgColor: "bg-green-50", icon: Folder },
  "Tipo de Proyecto": { color: "text-green-600", bgColor: "bg-green-50", icon: Folder },
  "Transferencia Socio Productiva": { color: "text-orange-700", bgColor: "bg-orange-50", icon: TrendingUp },
  "Tipo de Contrato": { color: "text-orange-600", bgColor: "bg-orange-50", icon: Briefcase },
  "Actividad de Docencia": { color: "text-teal-700", bgColor: "bg-teal-50", icon: Award },
  "Equipamiento": { color: "text-cyan-700", bgColor: "bg-cyan-50", icon: Zap },
  "Participación Relevante": { color: "text-pink-700", bgColor: "bg-pink-50", icon: CalendarIcon },
  "Registro de Propiedad": { color: "text-red-700", bgColor: "bg-red-50", icon: FileText },
  "Tipo Registro Propiedad": { color: "text-red-600", bgColor: "bg-red-50", icon: FileText },
  "Trabajo en Reunión Científica": { color: "text-violet-700", bgColor: "bg-violet-50", icon: Users },
  "Trabajo en Revista con Referato": { color: "text-violet-700", bgColor: "bg-violet-50", icon: BookOpen },
  "Artículo de Divulgación": { color: "text-amber-700", bgColor: "bg-amber-50", icon: FileText },
  "Directivo": { color: "text-slate-700", bgColor: "bg-slate-100", icon: Building },
  "Categoría de Erogación": { color: "text-rose-700", bgColor: "bg-rose-50", icon: TrendingUp },
  "Movimiento financiero": { color: "text-emerald-700", bgColor: "bg-emerald-50", icon: TrendingUp },
  "Fuente de Financiamiento": { color: "text-emerald-700", bgColor: "bg-emerald-50", icon: Building },
  "Tipo Personal": { color: "text-slate-700", bgColor: "bg-slate-100", icon: Users },
  "Persona": { color: "text-slate-700", bgColor: "bg-slate-100", icon: Users },
};

// Función para obtener configuración de tipo (con fallback)
const getTypeConfig = (tipo: string) => {
  return TYPE_CONFIG[tipo] || { color: "text-slate-700", bgColor: "bg-slate-100", icon: FileText };
};

type ExtraItem = {
  id?: number;
  url?: string;
  nombre?: string;
  titulo?: string;
  nombre_apellido?: string;
  articulo?: string;
  descripcion?: string;
  evento?: string;
};

const getExtraArray = (extra: Record<string, unknown>, key: string): ExtraItem[] => {
  const value = extra[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is ExtraItem => Boolean(item) && typeof item === "object"
      )
    : [];
};

const getExtraItemName = (item: ExtraItem): string | null => {
  const value =
    item.nombre_apellido ??
    item.nombre ??
    item.titulo ??
    item.articulo ??
    item.descripcion ??
    item.evento;
  return typeof value === "string" && value.trim() ? value.trim() : null;
};

const getExtraNames = (extra: Record<string, unknown>, key: string): string[] =>
  getExtraArray(extra, key)
    .map(getExtraItemName)
    .filter((value): value is string => value !== null);

const isOrder = (value: string): value is Orden =>
  ["alf_asc", "alf_desc", "fecha_asc", "fecha_desc"].includes(value);

const getExtraString = (extra: Record<string, unknown>, key: string): string | null => {
  const value = extra[key];
  return typeof value === "string" ? value : null;
};

export default function SearchPage() {
  const nav = useNavigate();
  const location = useLocation();
  const { uctGuard } = useUctGuard();
  const {
    q, setQ,
    orden, setOrden,
    selectedTypes,
    toggleType,
    dateFrom, setDateFrom,
    dateTo, setDateTo,
    availableTypes,
    loading,
    results,
    totalRaw,
    error,
    clearAll,
    executeSearch,
    executeImmediateSearch,
    hasSearched,
    page,
    setPage,
    meta,
  } = useSearch();

  const [showAdvanced, setShowAdvanced] = useState(false);
  const searchReturnTo = `${location.pathname}${location.search}`;

  const navigateFromSearch = (to: string) => {
    nav(to, {
      state: {
        searchReturnTo,
      },
    });
  };

  const ORDEN_OPTIONS = [
    { value: "alf_asc", label: "Alfabético A → Z" },
    { value: "alf_desc", label: "Alfabético Z → A" },
    { value: "fecha_desc", label: "Más recientes primero" },
    { value: "fecha_asc", label: "Más antiguos primero" },
  ];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeImmediateSearch();
  };

  const handleOrdenChange = (newOrden: string) => {
    if (isOrder(newOrden)) setOrden(newOrden);
  };

  // Función para extraer items relacionados con URLs del campo extra
  const extractRelatedItems = (result: SearchResult): Array<{ id: number; nombre: string; url: string; tipo?: string }> => {
    if (!result.extra) return [];

    const items: Array<{ id: number; nombre: string; url: string; tipo?: string }> = [];
    const extra = result.extra;

    // Buscar arrays que contengan objetos con id, nombre/título y url
    const possibleArrays = [
      { key: "documentos", tipo: "Documento" },
      { key: "proyectos", tipo: "Proyecto" },
      { key: "becarios", tipo: "Becario" },
      { key: "investigadores", tipo: "Investigador" },
      { key: "autores", tipo: "Autor" },
      { key: "participaciones_relevantes", tipo: "Participación" },
      { key: "trabajos_reunion", tipo: "Trabajo" },
      { key: "erogaciones_recientes", tipo: "Movimiento" },
      { key: "transferencias", tipo: "Transferencia" },
      { key: "registros", tipo: "Registro" },
      { key: "personal", tipo: "Personal" },
    ];

    possibleArrays.forEach(({ key, tipo }) => {
      const arr = extra[key as keyof typeof extra];
      if (Array.isArray(arr)) {
        getExtraArray(extra, key).forEach((item) => {
          if (typeof item.id === "number" && typeof item.url === "string") {
            const nombre = getExtraItemName(item) ?? "Item";
            items.push({
              id: item.id,
              nombre: String(nombre).substring(0, 35),
              url: item.url,
              tipo,
            });
          }
        });
      }
    });

    // Eliminar duplicados por ID
    const uniqueItems = items.filter((item, index, self) =>
      index === self.findIndex((t) => t.id === item.id)
    );

    return uniqueItems;
  };

  // Función para generar preview del equipo/relaciones
  const renderEquipoPreview = (result: SearchResult): { texto: string; count: number } | null => {
    if (!result.extra) return null;

    const extra = result.extra;
    let items: string[] = [];
    let label = "Equipo";

    switch (result.tipo) {
      case "Proyecto de Investigación":
        const invProy = getExtraNames(extra, "investigadores");
        const becProy = getExtraNames(extra, "becarios");
        items = [...invProy, ...becProy];
        break;

      case "Trabajo en Reunión Científica":
      case "Trabajo en Revista con Referato":
        items = getExtraNames(extra, "autores");
        label = "Autores";
        break;

      case "Investigador":
        items = getExtraNames(extra, "proyectos");
        label = "Proyectos";
        break;

      case "Becario":
        items = getExtraNames(extra, "proyectos");
        label = "Proyectos";
        break;

      case "Autor":
        items = getExtraNames(extra, "documentos");
        label = "Documentos";
        break;

      case "Documentación":
        items = getExtraNames(extra, "autores");
        label = "Autores";
        break;

      case "Tipo de Proyecto":
        items = getExtraNames(extra, "proyectos");
        label = "Proyectos";
        break;

      case "Fuente de Financiamiento":
        items = getExtraNames(extra, "proyectos");
        label = "Proyectos";
        break;

      case "Categoría de Erogación":
        items = getExtraNames(extra, "erogaciones_recientes");
        label = "Movimientos";
        break;

      case "Tipo de Contrato":
        items = getExtraNames(extra, "transferencias");
        label = "Transferencias";
        break;

      case "Tipo Personal":
        items = getExtraNames(extra, "personal");
        label = "Personal";
        break;

      case "Tipo Registro Propiedad":
        items = getExtraNames(extra, "registros");
        label = "Registros";
        break;

      case "Actividad de Docencia":
        const investigador = getExtraString(extra, "investigador");
        if (investigador) {
          items = [investigador];
        }
        label = "Docente";
        break;

      default:
        return null;
    }

    if (items.length === 0) return null;

    return {
      texto: `${label}: ${items.join(", ")}`,
      count: items.length
    };
  };

  // Tipo para items expandidos
  type ExpandedItem = {
    id: string;
    origin: SearchResult;
    relatedItem: { id: number; nombre: string; url: string; tipo?: string } | null;
    fecha: string | null;
  };

  // Expandir resultados
  const expandResults = (searchResults: SearchResult[]): ExpandedItem[] => {
    const expanded: ExpandedItem[] = [];

    searchResults.forEach((result) => {
      const relatedItems = extractRelatedItems(result);

      // NO expandir Personal/Becario/Investigador - mostrar como cards únicas
      const tiposNoExpandir = ["Persona", "Becario", "Investigador", "Directivo"];
      if (tiposNoExpandir.includes(result.tipo)) {
        expanded.push({
          id: `${result.tipo}-${result.id}-main`,
          origin: result,
          relatedItem: null,
          fecha: result.fecha,
        });
        return;
      }

      if (relatedItems.length === 0) {
        expanded.push({
          id: `${result.tipo}-${result.id}-main`,
          origin: result,
          relatedItem: null,
          fecha: result.fecha,
        });
      } else {
        relatedItems.forEach((item) => {
          expanded.push({
            id: `${result.tipo}-${result.id}-rel-${item.id}`,
            origin: result,
            relatedItem: item,
            fecha: result.fecha,
          });
        });
      }
    });

    return expanded;
  };

  const expandedResults = expandResults(results);

  // Agrupar resultados por tipo
  const groupedResults = useMemo(() => {
    const groups: Record<string, ExpandedItem[]> = {};
    expandedResults.forEach((item) => {
      const tipo = item.origin.tipo;
      if (!groups[tipo]) {
        groups[tipo] = [];
      }
      groups[tipo].push(item);
    });
    return groups;
  }, [expandedResults]);

  // Sugerencias para empty state
  const getSuggestions = () => {
    if (!q || q.length < 2) return [];

    const suggestions = [];
    const lowerQ = q.toLowerCase();

    // Sugerencias comunes basadas en el query
    if (lowerQ.includes("rober")) {
      suggestions.push({ text: "Robert", type: "Corrección" });
      suggestions.push({ text: "Roberto", type: "Alternativa" });
    }
    if (lowerQ.includes("proy")) {
      suggestions.push({ text: "Proyecto", type: "Completa" });
    }
    if (lowerQ.includes("inv")) {
      suggestions.push({ text: "Investigador", type: "Completa" });
    }

    return suggestions.slice(0, 3);
  };

  const suggestions = getSuggestions();

  return (
    <section className="w-full">
      <h2 className="text-2xl md:text-3xl font-semibold leading-none">
        Búsqueda
      </h2>

      {/* ─── BARRA DE BÚSQUEDA ─── */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 space-y-6 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Search className="w-5 h-5 text-slate-400" />
            </div>
            <input
              className="input !pl-11 pr-10 w-full"
              placeholder="Buscar personas, proyectos, documentos..."
              value={q}
              maxLength={SEARCH_MAX_QUERY_LENGTH}
              onChange={(e) => setQ(e.target.value)}
              autoFocus
            />
            {q && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                onClick={clearAll}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            className="hidden sm:flex items-center gap-2"
            disabled={loading}
           loading={loading}
           loadingText="Buscando..."
         >
            <Search className="w-4 h-4" />
            Buscar
          </Button>

          <Button
            type="button"
            variant={showAdvanced ? "primary" : "secondary"}
            size="md"
            className="flex items-center gap-2"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Filter className="w-4 h-4" />
            <span className="hidden sm:inline">{selectedTypes.length > 0 ? `Filtros (${selectedTypes.length})` : "Filtros"}</span>
          </Button>
        </form>

        {/* ─── FILTROS AVANZADOS ─── */}
        {showAdvanced && (
          <div className="pt-6 border-t border-slate-100 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in slide-in-from-top-2 duration-300">
            <Field label="Ordenar por">
              <select
                className="input"
                value={orden}
                onChange={(e) => handleOrdenChange(e.target.value)}
              >
                {ORDEN_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </Field>

            <Calendar
              label="Desde"
              institutionalRange={false}
              value={parseCivilDate(dateFrom)}
              onChange={(d) => setDateFrom(toCivilDateString(d) ?? undefined)}
              placeholder="Fecha desde"
            />

            <Calendar
              label="Hasta"
              institutionalRange={false}
              value={parseCivilDate(dateTo)}
              onChange={(d) => setDateTo(toCivilDateString(d) ?? undefined)}
              placeholder="Fecha hasta"
            />

            {availableTypes.length > 0 && (
              <div className="sm:col-span-2 lg:col-span-3">
                <Field label="Filtrar por tipo">
                  <div className="flex flex-wrap gap-2 mt-2">
                    {availableTypes.map((tipo) => {
                      const isActive = selectedTypes.includes(tipo);
                      const config = getTypeConfig(tipo);
                      const Icon = config.icon;

                      return (
                        <button
                          key={tipo}
                          type="button"
                          onClick={() => toggleType(tipo)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition-all ${isActive
                              ? `${config.color} ${config.bgColor} border-transparent shadow-sm`
                              : "bg-white border-slate-300 text-slate-600 hover:bg-slate-50"
                            }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          {tipo}
                        </button>
                      );
                    })}
                    {selectedTypes.length > 0 && (
                      <button
                        type="button"
                        onClick={clearAll}
                        className="px-3 py-1.5 text-xs font-medium text-red-600 hover:underline"
                      >
                        Limpiar filtros
                      </button>
                    )}
                  </div>
                </Field>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ─── RESULTADOS ─── */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {loading && (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-3 p-4 rounded-xl bg-slate-50">
                <div className="flex items-center gap-2">
                  <div className="h-5 w-16 bg-slate-200 rounded" />
                </div>
                <div className="h-6 w-3/4 bg-slate-200 rounded" />
                <div className="h-4 w-1/2 bg-slate-100 rounded" />
                <div className="h-6 w-32 bg-slate-200 rounded-full" />
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm border border-red-100">
            Error al buscar: {error}
          </div>
        )}

        {!loading && !error && !hasSearched && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-slate-500 font-medium text-lg">Comienza tu búsqueda</p>
            <p className="text-slate-400 text-sm mt-2 max-w-md mx-auto">
              Ingresa al menos 2 caracteres. Buscaremos automáticamente cuando dejes de escribir.
            </p>
          </div>
        )}

        {!loading && !error && hasSearched && results.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-slate-500 font-medium text-lg">Sin resultados para "{q}"</p>
            <p className="text-slate-400 text-sm mt-2">Prueba ajustando los filtros o usando otras palabras clave.</p>

            {suggestions.length > 0 && (
              <div className="mt-6">
                <p className="text-sm text-slate-500 mb-3">¿Quizás quisiste decir?</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.map((sug) => (
                    <button
                      key={sug.text}
                      onClick={() => {
                        setQ(sug.text);
                        executeSearch(sug.text);
                      }}
                      className="px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm font-medium hover:bg-blue-100 transition-colors"
                    >
                      {sug.text}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!loading && !error && hasSearched && expandedResults.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-700">
                  {expandedResults.length} resultado{expandedResults.length !== 1 ? "s" : ""}
                </span>
                {Object.keys(groupedResults).length > 1 && (
                  <span className="text-xs text-slate-400">
                    en {Object.keys(groupedResults).length} categorías
                  </span>
                )}
              </div>
              {totalRaw > results.length && (
                <span className="text-xs text-slate-400 italic">
                  Filtrado de {totalRaw} totales
                </span>
              )}
            </div>

            <div className="space-y-6">
              {Object.entries(groupedResults).map(([tipo, items]) => {
                const config = getTypeConfig(tipo);
                const Icon = config.icon;

                return (
                  <div key={tipo} className="space-y-2">
                    {/* Header del grupo */}
                    <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                      <div className={`p-1.5 rounded-lg ${config.bgColor}`}>
                        <Icon className={`w-4 h-4 ${config.color}`} />
                      </div>
                      <h3 className="font-semibold text-slate-800">{tipo}</h3>
                      <span className="text-xs text-slate-400 font-medium">
                        ({items.length})
                      </span>
                    </div>

                    {/* Items del grupo - Diseño minimalista */}
                    <ul className="divide-y divide-slate-50">
                      {items.map((item) => (
                        <li
                          key={item.id}
                          className="group py-4 px-2 -mx-2 cursor-pointer hover:bg-slate-50 rounded-lg transition-all"
                          onClick={() =>
                            navigateFromSearch(
                              item.relatedItem
                                ? resolveFrontendUrl(item.relatedItem.url)
                                : item.origin.href
                            )
                          }
                        >
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                            <div className="space-y-1.5 flex-1">
                              {/* ORIGEN - Resultado principal */}
                              <div className="space-y-1">
                                <span className={`inline-block text-[10px] uppercase tracking-wider font-bold ${config.color} ${config.bgColor} px-2 py-0.5 rounded`}>
                                  {item.origin.tipo}
                                </span>
                                <h3 className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors leading-tight">
                                  {highlight(item.origin.titulo, q)}
                                </h3>
                                {item.origin.subtitulo && (
                                  <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">
                                    {highlight(item.origin.subtitulo, q)}
                                  </p>
                                )}
                              </div>

                              {/* PREVIEW DEL EQUIPO/RELACIONES */}
                              {(() => {
                                // Caso especial: Becario/Investigador con proyectos - mostrar como chips clickeables
                                if ((item.origin.tipo === "Becario" || item.origin.tipo === "Investigador") && item.origin.extra?.proyectos) {
                                  const proyectos = getExtraArray(
                                    item.origin.extra,
                                    "proyectos"
                                  ).filter(
                                    (proyecto) =>
                                      typeof proyecto.id === "number" &&
                                      getExtraItemName(proyecto) !== null
                                  );
                                  if (proyectos.length === 0) return null;

                                  return (
                                    <div className="mt-2">
                                      <div className="flex items-center gap-1.5 flex-wrap">
                                        <span className="text-xs text-slate-500 font-medium">Proyectos:</span>
                                        {proyectos.map((proy) => {
                                          // Construir URL del proyecto si no viene del backend
                                          const proyectoUrl =
                                            typeof proy.url === "string"
                                              ? proy.url
                                              : `/proyectos/${proy.id}`;
                                          return (
                                            <button
                                              key={proy.id}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                navigateFromSearch(resolveFrontendUrl(proyectoUrl));
                                              }}
                                              className="inline-flex items-center px-2 py-0.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full hover:bg-green-100 transition-colors"
                                            >
                                              {getExtraItemName(proy)}
                                            </button>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  );
                                }

                                // Resto de tipos - mostrar como preview de equipo
                                const preview = renderEquipoPreview(item.origin);
                                if (!preview) return null;

                                // Separar el label de los items
                                const [label, ...itemsPart] = preview.texto.split(': ');
                                const items = itemsPart.join(': ').split(', ');

                                return (
                                  <div className="mt-1.5 text-xs text-slate-500">
                                    <div className="flex items-start gap-1.5">
                                      <Users className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                      <span className="flex flex-wrap gap-1">
                                        <span className="font-medium">{label}:</span>
                                        {items.map((nombre, idx) => {
                                          // Verificar si este nombre coincide con la búsqueda
                                          const searchTerms = q.toLowerCase().split(' ').filter(t => t.length > 0);
                                          const nombreLower = nombre.toLowerCase();
                                          const isMatch = searchTerms.some(term => nombreLower.includes(term));

                                          return (
                                            <span key={idx}>
                                              {isMatch ? (
                                                <span className="bg-yellow-200 px-1 rounded font-medium text-slate-700">
                                                  {nombre.trim()}
                                                </span>
                                              ) : (
                                                nombre.trim()
                                              )}
                                              {idx < items.length - 1 && ','}
                                            </span>
                                          );
                                        })}
                                      </span>
                                    </div>
                                  </div>
                                );
                              })()}

                              {/* ITEM RELACIONADO - Chip simple */}
                              {item.relatedItem && (
                                <div className="mt-2">
                                  <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-100 rounded-full">
                                    {highlight(item.relatedItem.nombre, q)}
                                  </span>
                                </div>
                              )}
                            </div>

                            {item.fecha && (
                              <div className="text-xs font-medium text-slate-400 whitespace-nowrap pt-1">
                                {new Date(item.fecha + "T12:00:00").toLocaleDateString("es-AR", {
                                  day: "2-digit",
                                  month: "short",
                                  year: "numeric"
                                })}
                              </div>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {!loading && !error && hasSearched && meta.total_pages > 1 && (
          <div className="mt-8">
            <nav aria-label="Paginación" className="flex flex-wrap items-center justify-center gap-2">
              <Button type="button" size="sm" variant="secondary" aria-label="Página anterior"
                disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                {"<"}
              </Button>
              {[...Array(meta.total_pages)].map((_, index) => {
                const pageNumber = index + 1;
                return (
                  <button type="button" key={pageNumber} aria-label={`Página ${pageNumber}`}
                    aria-current={page === pageNumber ? "page" : undefined}
                    onClick={() => setPage(pageNumber)}
                    className={`rounded-lg px-3 py-1 text-sm ${
                      page === pageNumber ? "bg-slate-800 text-white" : "bg-slate-100 hover:bg-slate-200"
                    }`}>
                    {pageNumber}
                  </button>
                );
              })}
              <Button type="button" size="sm" variant="secondary" aria-label="Página siguiente"
                disabled={page >= meta.total_pages} onClick={() => setPage((current) => current + 1)}>
                {">"}
              </Button>
            </nav>
          </div>
        )}
      </div>
      {uctGuard}
    </section>
  );
}
