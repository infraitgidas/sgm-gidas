import type React from "react";
import { Children, isValidElement, useEffect, useId, useRef } from "react";

function hasInlineError(children: React.ReactNode, error: string): boolean {
  return Children.toArray(children).some(child => {
    if (!isValidElement<{ children?: React.ReactNode }>(child)) return false;
    return (child.type === "p" && child.props.children === error) ||
      hasInlineError(child.props.children, error);
  });
}

interface FieldProps {
  label: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  name?: string;
}

export default function Field({
  label,
  children,
  error,
  required,
  name,
}: FieldProps) {
  const root = useRef<HTMLDivElement>(null);
  const id = useId();
  const inlineError = !!error && hasInlineError(children, error);
  useEffect(() => {
    const controls = Array.from(root.current?.querySelectorAll<HTMLElement>("input:not([type=hidden]), select, textarea, [role=combobox]") ?? []);
    const label = root.current?.querySelector("label");
    if (!controls.length) return;
    if (!controls[0].id) controls[0].id = `${id}-control`;
    if (label) label.htmlFor = controls[0].id;
    if (!error) return;
    const paragraph = Array.from(root.current?.querySelectorAll("p") ?? []).find(node => node.textContent === error);
    if (!paragraph) return;
    if (!paragraph.id) paragraph.id = `${id}-error`;
    paragraph.setAttribute("role", "alert");
    const previous = controls.map(control => {
      const invalid = control.getAttribute("aria-invalid");
      const describedBy = control.getAttribute("aria-describedby");
      const description = Array.from(new Set([...(describedBy?.split(/\s+/).filter(Boolean) ?? []), paragraph.id])).join(" ");
      control.setAttribute("aria-invalid", "true");
      control.setAttribute("aria-describedby", description);
      return { control, invalid, describedBy, description };
    });
    return () => {
      for (const { control, invalid, describedBy, description } of previous) {
        if (control.getAttribute("aria-invalid") === "true") {
          if (invalid === null) control.removeAttribute("aria-invalid");
          else control.setAttribute("aria-invalid", invalid);
        }
        if (control.getAttribute("aria-describedby") === description) {
          if (describedBy === null) control.removeAttribute("aria-describedby");
          else control.setAttribute("aria-describedby", describedBy);
        }
      }
    };
  }, [children, error, id]);
  return (
    <div ref={root} data-error-field={name} tabIndex={error ? -1 : undefined} className={error ? "[&_input]:!border-rose-500 [&_select]:!border-rose-500 [&_textarea]:!border-rose-500" : undefined}>
      <label className="block text-sm font-medium mb-2">
        {label}
        {required && <span className="text-rose-500 ml-1">*</span>}
      </label>
      {children}
      {error && !inlineError && (
        <p id={`${id}-error`} role="alert" className="text-xs text-rose-600 mt-1.5">{error}</p>
      )}
    </div>
  );
}
