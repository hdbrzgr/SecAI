import Link from "next/link";
import type { ComponentProps } from "react";

type Props = ComponentProps<typeof Link> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
};

/** A link styled as a @secai/ui Button, for navigation that looks like an action. */
export function ButtonLink({ variant = "secondary", size = "md", className = "", ...props }: Props) {
  return <Link className={`sx-btn sx-btn-${variant} sx-btn-${size} ${className}`} {...props} />;
}
