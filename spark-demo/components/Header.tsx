import Link from "next/link";
import ThemeToggle from "./ThemeToggle";

const navLinks = [
  { href: "/", label: "Showcase" },
  { href: "/sandbox", label: "Sandbox" },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1080px] items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2">
          <span className="spark-gradient-bg inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-md)] text-[15px] font-semibold text-white">
            S
          </span>
          <span className="text-[17px] tracking-[-0.02em] text-heading">
            SPARK
            <span className="ml-1 text-body">v1</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-[var(--radius-md)] px-3 py-2 text-[14px] font-normal text-heading [font-feature-settings:'ss01'] transition-colors hover:bg-surface-muted"
            >
              {link.label}
            </Link>
          ))}
          <span className="mx-2 hidden h-5 w-px bg-border sm:block" />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
