import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
  elevated?: boolean;
};

export default function Card({
  children,
  className = "",
  elevated = false,
}: CardProps) {
  return (
    <div
      className={`rounded-[var(--radius-lg)] border border-border bg-surface p-6 ${
        elevated ? "shadow-elevated" : "shadow-card"
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-[22px] leading-[1.1] tracking-[-0.22px] text-heading">
      {children}
    </h3>
  );
}

export function CardBody({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-[16px] leading-[1.4] text-body">{children}</p>;
}
