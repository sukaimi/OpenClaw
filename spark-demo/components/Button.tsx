import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

type Variant = "gradient" | "primary" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] px-4 py-2 text-[15px] font-normal [font-feature-settings:'ss01'] transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  gradient:
    "spark-gradient-bg text-white shadow-card hover:brightness-110 hover:-translate-y-px",
  primary:
    "bg-primary text-white hover:bg-primary-hover shadow-card hover:-translate-y-px",
  ghost:
    "bg-transparent text-primary border border-border-strong hover:bg-primary/5",
};

type CommonProps = {
  variant?: Variant;
  children: ReactNode;
  className?: string;
};

type ButtonAsLink = CommonProps & { href: string } & Omit<
    ComponentProps<typeof Link>,
    "href" | "className" | "children"
  >;

type ButtonAsButton = CommonProps & { href?: undefined } & Omit<
    ComponentProps<"button">,
    "className" | "children"
  >;

export default function Button(props: ButtonAsLink | ButtonAsButton) {
  const { variant = "gradient", children, className = "" } = props;
  const classes = `${base} ${variants[variant]} ${className}`;

  if (props.href !== undefined) {
    const { variant: _v, children: _c, className: _cn, href, ...rest } = props;
    return (
      <Link href={href} className={classes} {...rest}>
        {children}
      </Link>
    );
  }

  const { variant: _v, children: _c, className: _cn, href: _h, ...rest } = props;
  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}
