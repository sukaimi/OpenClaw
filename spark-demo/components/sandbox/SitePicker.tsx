"use client";

type SitePickerProps = {
  onRebuild: () => void;
  disabled?: boolean;
};

const comingSoon = [
  { name: "Northwind Traders — Sales Portal", host: "northwind.sharepoint.com/sites/Sales" },
  { name: "Fabrikam — HR Hub", host: "fabrikam.sharepoint.com/sites/PeopleHub" },
];

export default function SitePicker({ onRebuild, disabled }: SitePickerProps) {
  return (
    <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      {/* Selected sample source site */}
      <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-border-strong bg-surface shadow-card ring-1 ring-primary/20">
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-3">
          <span className="inline-flex items-center gap-2 text-[13px] font-medium text-heading">
            <span className="spark-gradient-bg h-2 w-2 rounded-full" />
            Selected source site
          </span>
          <span className="rounded-[var(--radius-sm)] border border-border bg-surface-muted px-2 py-0.5 text-[12px] text-body">
            Classic intranet
          </span>
        </div>

        <div className="grid gap-4 p-5 sm:grid-cols-[200px_1fr]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/crestfield/before-home.png"
            alt="Crestfield Foods classic intranet homepage"
            className="h-[130px] w-full rounded-[var(--radius-md)] border border-border object-cover object-top"
          />
          <div className="min-w-0">
            <h3 className="text-[19px] leading-tight text-heading">
              Crestfield Foods — Classic Intranet
            </h3>
            <p className="mt-1 font-mono text-[12.5px] text-body break-all">
              contoso.sharepoint.com/sites/CrestfieldClassic
            </p>
            <p className="mt-3 text-[14px] leading-[1.45] text-body">
              A dated SharePoint classic publishing site: fixed-width tables,
              low-res logos, and a 15-item nav. Point SPARK at it and watch the
              rebuild.
            </p>
            <button
              type="button"
              onClick={onRebuild}
              disabled={disabled}
              className="spark-gradient-bg mt-4 inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] px-4 py-2 text-[15px] font-medium text-white shadow-card transition-all duration-150 hover:-translate-y-px hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50"
            >
              Rebuild this site
              <span aria-hidden>→</span>
            </button>
          </div>
        </div>
      </div>

      {/* Coming-soon (non-interactive) */}
      <div className="flex flex-col gap-3">
        {comingSoon.map((s) => (
          <div
            key={s.host}
            aria-disabled="true"
            className="rounded-[var(--radius-lg)] border border-dashed border-border bg-surface-muted/60 px-4 py-4 opacity-60"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[15px] text-heading">{s.name}</span>
              <span className="rounded-[var(--radius-sm)] border border-border bg-surface px-2 py-0.5 text-[11px] uppercase tracking-wide text-body">
                Soon
              </span>
            </div>
            <p className="mt-1 font-mono text-[12px] text-body break-all">
              {s.host}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
