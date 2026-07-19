// cc-verify-watch: Mac-side intake "Verify" worker for SharePoint source capture.
// The capture popup MUST run on the operator's Mac (authed browser), and the Mac can't
// accept inbound calls — so this polls a SERVER-side queue (the rendezvous), runs
// cc-sp-capture for each request, ships the bundle, and writes a result the server
// reconciles back onto the Intake Briefs list (sets AccessVerified).
//
// Queue contract (on the server):
//   /srv/verify-queue/<id>.json         request  {itemId, url, job?}
//   /srv/verify-queue/<id>.lock         in-progress marker (this worker)
//   /srv/verify-queue/<id>.result.json  result   {ok, pages, images, error?, capturedAt}
//   /srv/intake-captures/<id>/          the shipped capture/ bundle
//
// Config (~/.codecraft/verify-watch.json, mode 600, NOT committed):
//   { "host": "...", "user": "root", "pass": "..." }   (or env CC_SP_HOST/USER/PASS)
//
// Usage: node cc-verify-watch.mjs [--once] [--interval 15]
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const CAPTURE = join(HERE, "cc-sp-capture.mjs");
const argv = process.argv.slice(2);
const ONCE = argv.includes("--once");
const INTERVAL = Number((argv[argv.indexOf("--interval") + 1]) || 15) * 1000;

function loadCfg() {
  const p = process.env.HOME + "/.codecraft/verify-watch.json";
  const fromFile = existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : {};
  const host = process.env.CC_SP_HOST || fromFile.host;
  const user = process.env.CC_SP_USER || fromFile.user || "root";
  const pass = process.env.CC_SP_PASS || fromFile.pass;
  if (!host || !pass) { console.error("cc-verify-watch: need host+pass in ~/.codecraft/verify-watch.json or env CC_SP_HOST/CC_SP_PASS"); process.exit(2); }
  return { host, user, pass };
}
const CFG = loadCfg();
// SECURITY (MITM): trust-on-first-use. accept-new records an unknown host key on the first
// connect (won't break automation) but REJECTS a subsequently CHANGED key, which is the
// signature of a man-in-the-middle. Never use "no" here — that blindly accepts any key.
const SSH = ["-o", "StrictHostKeyChecking=accept-new", `${CFG.user}@${CFG.host}`];

function ssh(cmd) { return execFileSync("sshpass", ["-p", CFG.pass, "ssh", ...SSH, cmd], { encoding: "utf8" }); }
function scpDir(localDir, remoteParent) {
  // SECURITY (MITM): same trust-on-first-use policy for the capture-bundle transfer.
  execFileSync("sshpass", ["-p", CFG.pass, "scp", "-r", "-o", "StrictHostKeyChecking=accept-new", localDir, `${CFG.user}@${CFG.host}:${remoteParent}`], { stdio: "ignore" });
}
function writeRemoteJson(path, obj) {
  const b64 = Buffer.from(JSON.stringify(obj, null, 2)).toString("base64");
  ssh(`echo ${b64} | base64 -d > ${path}`);
}
function hostOf(url) { try { return new URL(url).host; } catch { return "client"; } }

function pending() {
  const out = ssh(
    'for f in /srv/verify-queue/*.json; do [ -e "$f" ] || continue; ' +
    'case "$f" in *.result.json) continue;; esac; id=$(basename "$f" .json); ' +
    '[ -e "/srv/verify-queue/$id.result.json" ] && continue; ' +
    '[ -e "/srv/verify-queue/$id.lock" ] && continue; echo "$id"; done'
  ).trim();
  return out ? out.split("\n").filter(Boolean) : [];
}

function capture(url, id) {
  const out = `/tmp/cc-verify/${id}`;
  rmSync(out, { recursive: true, force: true });
  const state = `${process.env.HOME}/.codecraft/verify-${hostOf(url)}.json`;
  const base = [CAPTURE, url, "--job", `VERIFY-${id}`, "--out", out, "--state", state];
  // 1) try silently with any persisted per-client session; 2) fall back to a login popup.
  for (const mode of [[], ["--login"]]) {
    try {
      const res = execFileSync("node", [...base, ...mode], { cwd: HERE, encoding: "utf8" }).trim();
      const j = JSON.parse(res.split("\n").pop());
      if (j.ok) return { ...j, out };
    } catch (e) {
      const tail = String(e.stdout || e.message).trim().split("\n").pop();
      if (mode.length) return { ok: false, error: tail?.slice(0, 200) || "capture failed" };
      // else: headless failed (likely needs login) -> loop retries with --login
    }
  }
  return { ok: false, error: "capture failed (login)" };
}

function processOne(id) {
  // Security: `id` is derived from a remote queue filename and is interpolated into
  // shell commands below. Reject anything that isn't a plain slug to prevent command
  // injection / path traversal, then quote the path args as defense in depth.
  if (!/^[A-Za-z0-9_-]+$/.test(id)) {
    console.error(`[verify] skipping invalid id: ${JSON.stringify(id)}`);
    return;
  }
  let req;
  try { req = JSON.parse(ssh(`cat '/srv/verify-queue/${id}.json'`)); } catch { return; }
  if (!req.url) { writeRemoteJson(`/srv/verify-queue/${id}.result.json`, { ok: false, error: "no url" }); return; }
  ssh(`touch '/srv/verify-queue/${id}.lock'`);
  console.log(`[verify] ${id}: capturing ${req.url}`);
  const r = capture(req.url, id);
  try {
    if (r.ok) {
      ssh(`rm -rf '/srv/intake-captures/${id}' && mkdir -p '/srv/intake-captures/${id}'`);
      scpDir(`${r.out}/.`, `/srv/intake-captures/${id}/`);
      writeRemoteJson(`/srv/verify-queue/${id}.result.json`, { ok: true, pages: r.pages, images: r.images, capturedAt: new Date().toISOString() });
      console.log(`[verify] ${id}: OK (${r.pages} pages, ${r.images} images) -> /srv/intake-captures/${id}`);
    } else {
      writeRemoteJson(`/srv/verify-queue/${id}.result.json`, { ok: false, error: r.error });
      console.log(`[verify] ${id}: FAILED — ${r.error}`);
    }
  } finally {
    ssh(`rm -f '/srv/verify-queue/${id}.lock'`);
  }
}

function tick() {
  let ids = [];
  try { ids = pending(); } catch (e) { console.error("[verify] poll error:", String(e.message).slice(0, 120)); return; }
  if (ids.length) console.log(`[verify] ${ids.length} pending: ${ids.join(", ")}`);
  for (const id of ids) { try { processOne(id); } catch (e) { console.error(`[verify] ${id} error:`, String(e.message).slice(0, 160)); } }
}

if (ONCE) { tick(); }
else { console.log(`[verify] watching (every ${INTERVAL / 1000}s); Ctrl-C to stop`); tick(); setInterval(tick, INTERVAL); }
