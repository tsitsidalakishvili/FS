import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Variant = "success" | "warning" | "info" | "muted";

const variantClasses: Record<Variant, string> = {
  success: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-900",
  info: "bg-blue-100 text-blue-900",
  muted: "bg-slate-100 text-slate-700",
};

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: Variant;
};

export function Badge({ className, variant = "muted", ...props }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
