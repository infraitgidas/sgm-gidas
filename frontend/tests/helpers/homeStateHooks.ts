import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import * as values from "../../src/modules/shared/utils/homeState.ts";

// Ejecuta el hook de producción con el mismo runtime de hooks que la página bajo prueba.
export function loadHomeStateHooks(react: unknown, auth: unknown, router: unknown, storage?: Storage) {
  const code = ts.transpileModule(readFileSync("src/modules/shared/hooks/useHomeState.ts", "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText;
  const dependencies: Record<string, unknown> = {
    react, "@/context/AuthContext": auth, "react-router-dom": router,
    "@/modules/shared/utils/homeState": { ...values, homeStorage: () => storage },
  };
  const module = { exports: {} as any };
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (!(name in dependencies)) throw new Error(`Dependencia inesperada: ${name}`);
    return dependencies[name];
  } });
  return module.exports;
}
