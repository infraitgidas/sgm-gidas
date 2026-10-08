import { Check, ChevronDown } from "lucide-react";
import { Select } from "radix-ui";

export type TableFilterOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type Props = {
  label: string;
  value?: string;
  placeholder: string;
  options: TableFilterOption[];
  onValueChange: (value: string | undefined) => void;
  className?: string;
  disabled?: boolean;
};

const EMPTY_VALUE = "__table_filter_all__";

export default function TableFilterSelect({
  label,
  value,
  placeholder,
  options,
  onValueChange,
  className = "",
  disabled = false,
}: Props) {
  return (
    <Select.Root
      disabled={disabled}
      value={value ?? EMPTY_VALUE}
      onValueChange={(nextValue) =>
        onValueChange(nextValue === EMPTY_VALUE ? undefined : nextValue)
      }
    >
      <Select.Trigger
        aria-label={label}
        className={`inline-flex h-8 min-w-44 shrink-0 items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 outline-none transition hover:border-slate-400 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-slate-500 ${className}`}
      >
        <Select.Value placeholder={placeholder} />
        <Select.Icon asChild>
          <ChevronDown aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-slate-500" />
        </Select.Icon>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          position="popper"
          sideOffset={6}
          align="start"
          collisionPadding={12}
          className="z-[80] max-h-[min(18rem,var(--radix-select-content-available-height))] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl"
        >
          <Select.Viewport>
            <FilterItem value={EMPTY_VALUE} label={placeholder} />
            {options.map((option) => (
              <FilterItem key={option.value} {...option} />
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

function FilterItem({ value, label, disabled = false }: TableFilterOption) {
  return (
    <Select.Item
      value={value}
      disabled={disabled}
      className="relative flex cursor-default select-none items-center rounded-lg py-2 pl-3 pr-8 text-xs text-slate-700 outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-slate-100 data-[highlighted]:text-slate-950"
    >
      <Select.ItemText>{label}</Select.ItemText>
      <Select.ItemIndicator className="absolute right-2 inline-flex items-center">
        <Check aria-hidden="true" className="h-3.5 w-3.5" />
      </Select.ItemIndicator>
    </Select.Item>
  );
}
