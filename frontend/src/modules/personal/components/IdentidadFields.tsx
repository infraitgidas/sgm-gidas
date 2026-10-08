import Field from "@/components/Field";

type Props = {
  prefix: string;
  dni: string;
  cuil: string;
  errors: Record<string, string>;
  onDniChange: (value: string) => void;
  onCuilChange: (value: string) => void;
};

export default function IdentidadFields({ prefix, dni, cuil, errors, onDniChange, onCuilChange }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Field label="DNI" name="dni" required error={errors.dni}>
        <input id={`${prefix}-dni`} className="input" inputMode="numeric" autoComplete="off"
          placeholder="12345678" maxLength={8} value={dni} aria-invalid={Boolean(errors.dni)}
          onChange={(event) => onDniChange(event.target.value)} />
      </Field>
      <Field label="CUIL" name="cuil" required error={errors.cuil}>
        <input id={`${prefix}-cuil`} className="input" inputMode="numeric" autoComplete="off"
          placeholder="XX-XXXXXXXX-X" maxLength={13} value={cuil} aria-invalid={Boolean(errors.cuil)}
          onChange={(event) => onCuilChange(event.target.value)} />
      </Field>
    </div>
  );
}
