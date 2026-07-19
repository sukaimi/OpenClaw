const pains = [
  "Months of consulting time",
  "Page-by-page, by hand",
  "No proof nothing dropped",
];

export default function ProblemSection() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-[680px] text-center">
        <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
          The problem
        </p>
        <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
          Classic → modern is a months-long, manual slog.
        </h2>
        <p className="mt-5 text-[17px] leading-[1.6] text-body">
          Thousands of organizations still run classic SharePoint intranets —
          dated, unresponsive, on a platform Microsoft is winding down.
          Migrating them is done by hand, page by page: an agency reads the old
          site, re-keys every page, and hopes nothing was dropped. It&apos;s
          slow, expensive, and &ldquo;did we carry everything over?&rdquo; gets
          answered by eyeballing, not evidence.
        </p>
      </div>

      <div className="mx-auto mt-12 grid max-w-[820px] gap-5 sm:grid-cols-3">
        {pains.map((pain) => (
          <div
            key={pain}
            className="flex items-center gap-3 rounded-[var(--radius-lg)] border border-border bg-surface px-5 py-5 shadow-card"
          >
            <span
              aria-hidden
              className="flex h-6 w-6 flex-none items-center justify-center rounded-full text-[13px] leading-none"
              style={{
                background: "color-mix(in srgb, var(--accent-ruby) 12%, transparent)",
                color: "var(--accent-ruby)",
              }}
            >
              ✕
            </span>
            <span className="text-[15px] leading-[1.3] text-heading">
              {pain}
            </span>
          </div>
        ))}
      </div>

      <p className="mx-auto mt-10 max-w-[680px] text-center text-[19px] font-light leading-[1.4] text-heading">
        SPARK runs the whole migration as one autonomous job —{" "}
        <span className="spark-gradient-text">and proves the result.</span>
      </p>
    </section>
  );
}
