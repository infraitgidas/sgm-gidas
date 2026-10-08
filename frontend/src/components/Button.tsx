import type { ButtonHTMLAttributes } from "react";
import { LoaderCircle } from "lucide-react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  loadingText?: string;
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  loading = false,
  loadingText = "Procesando...",
  disabled,
  children,
  ...rest
}: Props) {
  const sizeClasses =
    size === "sm"
      ? "text-sm px-3 py-1.5"
      : size === "lg"
        ? "text-lg px-6 py-3"
        : "text-base px-4 py-2";

  const variantClasses =
    variant === "primary"
      ? "bg-slate-900 text-white hover:opacity-90"
      : "bg-slate-200 text-slate-900 hover:bg-slate-300";

  return (
    <button
      type={type}
      className={`rounded-lg font-medium transition disabled:opacity-50 ${sizeClasses} ${variantClasses} ${className}`}
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || rest["aria-busy"]}
    >
      {loading ? (
        <span role="status" className="inline-flex items-center justify-center gap-2">
          <LoaderCircle className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
          {loadingText}
        </span>
      ) : children}
    </button>
  );
}
