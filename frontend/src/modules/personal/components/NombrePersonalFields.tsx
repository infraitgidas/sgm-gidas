import Field from "@/components/Field";

interface Props {
  prefix: string;
  nombre: string;
  apellido: string;
  errors: Record<string, string>;
  onNombreChange: (value: string) => void;
  onApellidoChange: (value: string) => void;
}

export default function NombrePersonalFields({ prefix, nombre, apellido, errors, onNombreChange, onApellidoChange }: Props) {
  return <div className="space-y-4">
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="Nombre" name="nombre" required error={errors.nombre}>
        <input id={`${prefix}-nombre`} className="input" value={nombre} maxLength={60}
          placeholder="Ingrese el nombre" autoComplete="given-name" onChange={(event) => onNombreChange(event.target.value)} onBlur={() => onNombreChange(nombre)} />
      </Field>
      <Field label="Apellido" name="apellido" required error={errors.apellido}>
        <input id={`${prefix}-apellido`} className="input" value={apellido} maxLength={60}
          placeholder="Ingrese el apellido" autoComplete="family-name" onChange={(event) => onApellidoChange(event.target.value)} onBlur={() => onApellidoChange(apellido)} />
      </Field>
    </div>
  </div>;
}
