import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = ts.transpileModule(readFileSync("src/modules/proyectos/components/PersonalProyectoField.tsx", "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;

function harness(initialValue: number[]) {
  const options = Array.from({ length: 12 }, (_, index) => ({ id: index + 1, nombre_apellido: `Persona ${index + 1}` }));
  const states: unknown[] = [];
  let cursor = 0;
  let value = initialValue;
  const module = { exports: {} as { default: (props: unknown) => unknown } };
  runInNewContext(source, { module, exports: module.exports, require: (name: string) => {
    if (name === "react") return {
      useId: () => "proyecto-personal",
      useState(initial: unknown) {
        const index = cursor++;
        if (!(index in states)) states[index] = initial;
        return [states[index], (next: unknown) => { states[index] = typeof next === "function" ? (next as (value: unknown) => unknown)(states[index]) : next; }];
      },
    };
    if (name === "@/components/Button") return { default: "Button" };
    return require(name);
  } });
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
  const render = () => { cursor = 0; return walk(module.exports.default({ value, options, label: "investigadores", onChange: (next: number[]) => { value = next; } })); };
  const button = (label: string) => render().find((node) => node.type === "Button" && node.props.children === label);
  const list = (label: string) => render().find((node) => node.type === "ul" && node.props["aria-label"] === label);
  return { render, button, list, value: () => value };
}

test("personal de proyecto pagina cinco candidatos, busca y conserva altas y bajas pendientes", () => {
  const h = harness([]);
  assert.equal(h.list("investigadores disponibles").props.children.length, 5);
  h.button("Siguiente").props.onClick();
  assert.equal(h.list("investigadores disponibles").props.children.length, 5);
  h.list("investigadores disponibles").props.children[0].props.children[1].props.onClick();
  assert.equal(JSON.stringify(h.value()), "[6]");

  h.render().find((node) => node.type === "input" && node.props.type === "search").props.onChange({ target: { value: "Persona 12" } });
  assert.equal(h.list("investigadores disponibles").props.children.length, 1);
  h.list("investigadores disponibles").props.children[0].props.children[1].props.onClick();
  assert.equal(JSON.stringify(h.value()), "[6,12]");
  h.list("investigadores seleccionados").props.children[0].props.children[1].props.onClick();
  assert.equal(JSON.stringify(h.value()), "[12]");
});

test("personal de proyecto limita también los seleccionados y conserva filas vacías de borradores", () => {
  const h = harness([1, 2, 3, 4, 5, 0]);
  assert.equal(h.list("investigadores seleccionados").props.children.length, 5);
  const next = h.render().filter((node) => node.type === "Button" && node.props.children === "Siguiente").at(-1);
  next.props.onClick();
  assert.equal(h.list("investigadores seleccionados").props.children.length, 1);
  h.list("investigadores disponibles").props.children[0].props.children[1].props.onClick();
  assert.equal(h.value()[5], 6);
  assert.equal(h.value().length, 6);
});
