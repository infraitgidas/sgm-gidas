import { ChevronRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { stripSuccessMessageState } from "@/lib/memoriaNavigation";
import { getRouteBreadcrumbs } from "@/modules/shared/utils/routeBreadcrumbs";

export default function RouteBreadcrumbs() {
  const location = useLocation();
  const items = getRouteBreadcrumbs(location.pathname);
  if (items.length === 0) return null;

  const navigationState = stripSuccessMessageState(location.state);

  return (
    <nav aria-label="Ruta de navegación" className="mb-4 text-sm text-slate-600">
      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
            {index > 0 && <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-slate-400" />}
            {item.to ? (
              <Link
                to={item.to}
                state={navigationState}
                className="rounded-sm underline-offset-2 hover:text-sky-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
              >
                {item.label}
              </Link>
            ) : (
              <span aria-current="page" className="font-medium text-slate-900">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
