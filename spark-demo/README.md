# SPARK v1 — SharePoint Autonomous Rebuild Kit

Hackathon demo. Phase 1 = themed foundation only (no interactive feature pages yet).

Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · React 19.
Fully static-capable: no runtime backend, no env vars, no external network calls, no secrets.

## Run locally

```bash
cd spark-demo
npm install   # first time only
npm run dev   # http://localhost:3000
```

Production build:

```bash
npm run build
npm run start
```

## Routes

- `/` — Showcase / landing (SPARK hero + gradient + CTA to sandbox).
- `/sandbox` — placeholder "Interactive sandbox coming" panel.

## Design system

Stripe-inspired. The reference lives at [`DESIGN.md`](./DESIGN.md).
Tokens are implemented as CSS custom properties in `app/globals.css` and mapped
into Tailwind utilities via the v4 `@theme` block. The UI is theme-aware:
light is default, dark follows `prefers-color-scheme`, and a manual toggle sets
`data-theme` on `<html>` (persisted in `localStorage`, applied pre-paint to
avoid flashes).

## Deployment

Target production domain: **spark-demo.codeandcraft.ai**.

`vercel.json` pins the Next.js framework preset and clean URLs. The custom
domain is assigned in Vercel project settings (not in `vercel.json`).
**Not deployed yet** — this is Phase 1 scaffold only.
