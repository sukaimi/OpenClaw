"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import trackerData from "@/fixtures/content-tracker.json";
import type {
  ContentTrackerRow,
  ImageIndexRow,
  StatusColors,
  TrackerData,
} from "./types";

const tracker = trackerData as TrackerData;
const statusColors: StatusColors = tracker.statusColors;

type TabId = "contentTracker" | "imageIndex" | "migrationSummary";

const TABS: { id: TabId; label: string }[] = [
  { id: "contentTracker", label: "Content Tracker" },
  { id: "imageIndex", label: "Image Index" },
  { id: "migrationSummary", label: "Migration Summary" },
];

function StatusPill({ status }: { status: string }) {
  const c = statusColors[status];
  if (!c) return <span className="text-body">{status}</span>;
  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded-[var(--radius-sm)] border px-2 py-0.5 text-[12px] font-medium"
      style={{
        color: c.hex,
        borderColor: `color-mix(in srgb, ${c.hex} 45%, transparent)`,
        backgroundColor: `color-mix(in srgb, ${c.hex} 14%, transparent)`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: c.hex }}
      />
      {c.label}
    </span>
  );
}

const thClass =
  "sticky top-0 z-20 whitespace-nowrap border-b border-border bg-surface-muted px-3 py-2 text-left text-[12px] font-semibold uppercase tracking-wide text-label";
// First-column header — sticky in both axes (corner), sits above everything.
const thFirstClass = `${thClass} left-0 z-30 border-r`;
const tdClass = "border-b border-border px-3 py-2 align-top text-[13px] text-body";

/**
 * Horizontal-scroll affordance: a right-edge fade that hides once you've
 * scrolled to the end, plus a small "Scroll" hint (phones). Wraps the
 * scroll container so sticky headers/columns keep working.
 */
function ScrollAffordance({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [atEnd, setAtEnd] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const max = el.scrollWidth - el.clientWidth;
      setAtEnd(max <= 1 || el.scrollLeft >= max - 1);
    };
    update();
    el.addEventListener("scroll", update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", update);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="relative">
      <div
        ref={ref}
        className="max-h-[440px] overflow-auto rounded-[var(--radius-md)] border border-border"
      >
        {children}
      </div>
      {/* Right-edge fade — content vanishes when there's more to scroll to */}
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-y-px right-px w-14 rounded-r-[var(--radius-md)] bg-gradient-to-l from-surface to-transparent transition-opacity duration-200 ${
          atEnd ? "opacity-0" : "opacity-100"
        }`}
      />
      {/* Scroll hint (phones) */}
      <div
        aria-hidden
        className={`pointer-events-none absolute bottom-2.5 right-2.5 rounded-full border border-border bg-surface/90 px-2 py-0.5 text-[11px] font-medium text-body shadow-card backdrop-blur-sm transition-opacity duration-200 sm:hidden ${
          atEnd ? "opacity-0" : "opacity-100"
        }`}
      >
        Scroll →
      </div>
    </div>
  );
}

function ContentTrackerTable() {
  const { columns, rows } = tracker.sheets.contentTracker;
  // Group by page: a non-empty page starts a new group; blank pages continue
  // the current one. Band alternate groups so the empty cells read as
  // intentional grouping, not a rendering bug.
  let group = -1;
  const grouped = rows.map((r: ContentTrackerRow) => {
    if (r.page) group++;
    return { row: r, g: group };
  });

  return (
    <ScrollAffordance>
      <table className="w-full min-w-[900px] border-collapse text-left">
        <thead>
          <tr>
            {columns.map((c, ci) => (
              <th key={c} className={ci === 0 ? thFirstClass : thClass}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grouped.map(({ row: r, g }, i) => {
            const banded = g % 2 === 1;
            const rowBg = banded ? "bg-surface-muted" : "bg-surface";
            return (
              <tr key={i} className={rowBg}>
                <td
                  className={`${tdClass} sticky left-0 z-10 whitespace-nowrap border-r border-border font-medium text-heading ${rowBg}`}
                >
                  {r.page}
                </td>
                <td className={`${tdClass} whitespace-nowrap font-mono text-[11.5px]`}>
                  {r.url}
                </td>
                <td className={`${tdClass} whitespace-nowrap`}>{r.section}</td>
                <td className={`${tdClass} whitespace-nowrap`}>{r.assetType}</td>
                <td className={`${tdClass} min-w-[160px]`}>{r.description}</td>
                <td className={`${tdClass} min-w-[220px]`}>{r.content}</td>
                <td className={`${tdClass} whitespace-nowrap font-mono text-[11.5px]`}>
                  {r.imageRef || "—"}
                </td>
                <td className={`${tdClass} whitespace-nowrap font-mono text-[11.5px]`}>
                  {r.hyperlink || "—"}
                </td>
                <td className={`${tdClass} min-w-[180px]`}>
                  {r.reviewNotes || "—"}
                </td>
                <td className={`${tdClass} whitespace-nowrap`}>
                  <StatusPill status={r.migrationStatus} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </ScrollAffordance>
  );
}

function ImageIndexTable() {
  const { columns, rows } = tracker.sheets.imageIndex;
  return (
    <ScrollAffordance>
      <table className="w-full min-w-[820px] border-collapse text-left">
        <thead>
          <tr>
            {columns.map((c, ci) => (
              <th key={c} className={ci === 0 ? thFirstClass : thClass}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r: ImageIndexRow, i) => {
            const lowRes = /low/i.test(r.resolution);
            const rowBg = i % 2 === 1 ? "bg-surface-muted" : "bg-surface";
            return (
              <tr key={i} className={rowBg}>
                <td
                  className={`${tdClass} sticky left-0 z-10 whitespace-nowrap border-r border-border font-mono text-[11.5px] text-heading ${rowBg}`}
                >
                  {r.referenceId}
                </td>
                <td className={`${tdClass} whitespace-nowrap font-mono text-[11.5px]`}>
                  {r.fileName}
                </td>
                <td className={`${tdClass} whitespace-nowrap`}>{r.page}</td>
                <td className={`${tdClass} whitespace-nowrap`}>{r.section}</td>
                <td className={`${tdClass} min-w-[200px]`}>{r.usage}</td>
                <td className={`${tdClass} whitespace-nowrap`}>
                  <span className={lowRes ? "font-medium text-warn" : ""}>
                    {r.resolution}
                  </span>
                </td>
                <td className={`${tdClass} min-w-[160px]`}>{r.migrationAction}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </ScrollAffordance>
  );
}

function MigrationSummary() {
  const { audit, painPoints } = tracker.sheets.migrationSummary;
  const counts = tracker.meta.statusCounts;

  return (
    <div className="flex flex-col gap-5">
      {/* Status distribution */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Object.entries(statusColors).map(([status, c]) => (
          <div
            key={status}
            className="rounded-[var(--radius-md)] border border-border bg-surface p-3"
            style={{ borderTopColor: c.hex, borderTopWidth: 3 }}
          >
            <div className="text-[26px] font-light tabular-nums text-heading">
              {counts[status] ?? 0}
            </div>
            <div className="text-[12.5px] text-body">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Audit metrics */}
      <div>
        <h4 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-label">
          Audit snapshot
        </h4>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {audit.map((m) => (
            <div
              key={m.metric}
              className="rounded-[var(--radius-md)] border border-border bg-surface-muted px-3 py-2.5"
            >
              <dt className="text-[12px] leading-tight text-body">{m.metric}</dt>
              <dd className="mt-1 text-[20px] font-light tabular-nums text-heading">
                {m.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Pain points */}
      <div>
        <h4 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-label">
          Pain points found
        </h4>
        <ul className="flex flex-col gap-2">
          {painPoints.map((p) => (
            <li
              key={p.id}
              className="flex gap-3 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2.5"
            >
              <span className="shrink-0 rounded-[var(--radius-sm)] bg-accent-magenta/15 px-2 py-0.5 text-[11px] font-semibold text-accent-ruby">
                {p.id}
              </span>
              <span className="text-[13px] leading-snug text-body">
                {p.finding}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function TrackerViewer() {
  const [tab, setTab] = useState<TabId>("contentTracker");

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-[19px] text-heading">Content Tracker workbook</h3>
          <p className="text-[13px] text-body">
            {tracker.meta.sourceFile} — 3 sheets, exported by the pipeline.
          </p>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Content tracker sheets"
        className="mb-3 inline-flex flex-wrap gap-1 rounded-[var(--radius-md)] border border-border bg-surface-muted p-1"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-[var(--radius-sm)] px-3 py-1.5 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
              tab === t.id
                ? "bg-surface text-heading shadow-card"
                : "text-body hover:text-heading"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === "contentTracker" && <ContentTrackerTable />}
        {tab === "imageIndex" && <ImageIndexTable />}
        {tab === "migrationSummary" && <MigrationSummary />}
      </div>
    </div>
  );
}
