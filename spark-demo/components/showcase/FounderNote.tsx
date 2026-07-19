export default function FounderNote() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-[720px]">
        <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface p-8 shadow-card sm:p-10">
          <div
            aria-hidden
            style={{ opacity: "var(--hero-glow-opacity)" }}
            className="pointer-events-none absolute -right-16 -top-16 -z-10 h-[240px] w-[240px] rounded-full spark-gradient-bg blur-3xl"
          />

          <div className="flex flex-col items-center gap-6 text-center sm:flex-row sm:items-start sm:text-left">
            {/* Gradient "SS" monogram */}
            <span
              aria-hidden
              className="flex h-16 w-16 flex-none items-center justify-center rounded-[var(--radius-lg)] spark-gradient-bg text-[24px] font-light tracking-tight text-white shadow-card"
            >
              SS
            </span>

            <div>
              <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-start">
                <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
                  Built solo
                </p>
                <span className="inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] border border-border-strong bg-surface-muted px-2.5 py-0.5 text-[11px] font-normal uppercase tracking-[0.1em] text-label">
                  One-person company
                </span>
              </div>

              <h2 className="mt-3 text-[clamp(1.6rem,3.5vw,2.25rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
                One founder. Twelve agents.
              </h2>

              <p className="mt-4 text-[17px] leading-[1.6] text-body">
                SPARK — the entire twelve-agent engine and this site — was
                designed and built end-to-end by one person:{" "}
                <span className="font-normal text-heading">Sukaimi Sukri</span>.
                No team, no agency. One founder orchestrating twelve agents that
                do the rebuild.
              </p>

              <p className="mt-4 text-[13px] leading-[1.5] text-label">
                Built for the OPC Hackathon — part of amber.ac&apos;s
                BUIDL_QUESTS 2026.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
