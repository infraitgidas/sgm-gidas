import { buildInfo, buildInfoLabel } from "@/lib/buildInfo";

export default function Footer() {
  return (
    <footer className="w-full mt-10 flex justify-center">
      <div className="w-full max-w-7xl px-4">
        <div className="rounded-3xl border border-white/10 bg-slate-950 text-slate-200 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
          <div className="px-6 lg:px-8 py-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            
            <div>
              <p className="text-sm font-semibold text-white">
                GIDAS - UTN FRLP
              </p>
              <p className="text-sm text-slate-400">
                Grupo de I&amp;D aplicado a sistemas informáticos
              </p>
            </div>

            <div className="flex flex-col md:items-end text-sm text-slate-400 gap-1">
              <p>
                <span className="text-white font-medium">Contacto:</span>{" "}
                gidas@frlp.utn.edu.ar
              </p>

              <p className="flex items-center gap-2">
                <span className="text-white">©</span>
                <span>Seminario-Integrador 2026</span>
                <span className="text-slate-600">|</span>
                <span>UTN-FRLP</span>
              </p>

              <p
                className="text-xs text-slate-500"
                title={buildInfo.buildDate ? `Build: ${buildInfo.buildDate}` : undefined}
              >
                {buildInfoLabel()}
              </p>
            </div>

          </div>
        </div>
      </div>
    </footer>
  );
}