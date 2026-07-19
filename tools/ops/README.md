# tools/ops — Web/EDM + Stripe + Kanban + dispatch ops code

**The only committed copy of the Web/EDM + Stripe + Kanban-board + dispatch ops code.** These are
point-in-time snapshots captured from the live VPS around **June 2026** — they are **stale**.
**DIFF against the live VPS (`/root/.openclaw/...`, `/srv/...`) before reusing anything here.**

They were previously mis-filed under `docs/_archive/_ux-input/` (they are code, not documentation)
and were relocated here unmodified during the 2026-07-19 docs consolidation. None of these files are
tracked anywhere else in the repo — this directory is their sole record.

Coverage (distinct from the live `tools/sp-provision/` SharePoint code):

- **Kanban / board:** `board_cli.py`, `board_{read,rollup,stages,views}.py`, `kanban_create.py`,
  `kanban_inspect.py`, `{open,close,move,finalize,phase1,phase2}_cards.py`, `close_cleanup.py`,
  `sp_view_sort.py`.
- **Delivery pipeline:** `cc_intake.py`, `cc_build.py`, `cc_deploy.py`, `cc_fulfil.py`,
  `cc_closeout.py`, `cc_autocloseout.py`, `cc_assets.py`, `cc_go.py`, `cc_ops.py`, `cc_slots.py`,
  `cc_paylink.py`, `cc_notify_client.py`, `cc_read_mail.py`, `cc_resend.py`, `cc_archive_purge.py`,
  `cc_bounce_watch.py`.
- **Verify:** `cc_verify_client.py`, `cc_verify_sweep.py`, `verify.py`, `webhook_selftest.py`.
- **Stripe:** `stripe_setup.py`, `stripe_deactivate.py`, `cc_stripe_webhook.py`, `create_webhook.py`.
- **Infra units:** `cc-dispatch.service`, `cc-dispatch-loop.sh`, `cc-autocloseout.cron`,
  `cc-verify-sweep.cron`, `gw_{discover,discover2,fix,verify}.sh`, `fix_agents.py`,
  `edit_welcome_card.py`, `merge_images.py`.
- **Test harness:** `e2e-run.sh`.
- **Ops docs:** `CLIENT-BUILD.md`, `DISPATCH.md` (documentation for the above code, kept alongside it).
