type Props = {
  label?: string;
  variant?: "detail" | "form" | "table" | "compact";
};

const bar = "rounded-md bg-slate-200/80";

export default function LoadingSkeleton({ label = "Cargando información…", variant = "detail" }: Props) {
  const compact = variant === "compact";
  const rows = variant === "table" ? 5 : variant === "form" ? 4 : compact ? 2 : 3;

  return (
    <div role="status" aria-live="polite" className={compact ? "space-y-2" : "space-y-5 py-4"}>
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="animate-pulse space-y-4 motion-reduce:animate-none">
        {!compact && <div className={`${bar} h-7 w-48 max-w-full`} />}
        <div className={compact ? "space-y-2" : "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"}>
          <div className="space-y-4">
            {Array.from({ length: rows }, (_, index) => (
              <div key={index} className={variant === "form" ? "space-y-2" : "flex gap-4"}>
                {variant === "form" && <div className={`${bar} h-3 w-28`} />}
                <div className={`${bar} h-4 ${index % 2 === 0 ? "w-full" : "w-3/4"}`} />
                {variant === "table" && <div className={`${bar} h-4 w-1/4`} />}
              </div>
            ))}
          </div>
        </div>
        {variant === "detail" && <div className="grid gap-4 sm:grid-cols-2"><div className={`${bar} h-24 rounded-2xl`} /><div className={`${bar} h-24 rounded-2xl`} /></div>}
      </div>
    </div>
  );
}
