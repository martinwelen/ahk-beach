/**
 * gh-dispatch-worker — Cloudflare Worker (cron) som triggar en GitHub Actions
 * workflow_dispatch. Ersätter homelab CT 130: ingen burk att sköta, pålitlig timing,
 * gratis. Kör redan CF Workers (analytics-dashboarden) → samma konto/infra.
 *
 * Miljö (wrangler.toml [vars] + secrets):
 *   GITHUB_TOKEN  (secret)  fine-grained PAT: Actions = Read and write på repot
 *   GH_OWNER                t.ex. "martinwelen"
 *   GH_REPO                 t.ex. "ahk-beach"
 *   GH_WORKFLOW             workflow-filnamn, t.ex. "update.yml"
 *   GH_REF                  branch, t.ex. "main"
 *   ACTIVE_FROM  (valfritt) ISO-datum "YYYY-MM-DD" – triggar tidigast denna dag
 *   ACTIVE_UNTIL (valfritt) ISO-datum "YYYY-MM-DD" – triggar senast denna dag
 *   FORCE        (valfritt) "true" → skickar inputs.force=true (bygg om oavsett data)
 *   TRIGGER_KEY  (valfritt secret) skyddar /trigger-routen
 *
 * Sätt ACTIVE_FROM/UNTIL per cup → Workern no-oppar utanför fönstret, alltså
 * "av mellan cuper" helt automatiskt. Saknas båda: alltid aktiv.
 */

function withinWindow(env, now) {
  const from = env.ACTIVE_FROM ? Date.parse(env.ACTIVE_FROM + "T00:00:00Z") : null;
  const until = env.ACTIVE_UNTIL ? Date.parse(env.ACTIVE_UNTIL + "T23:59:59Z") : null;
  if (from !== null && now < from) return false;
  if (until !== null && now > until) return false;
  return true;
}

async function dispatch(env) {
  const wf = env.GH_WORKFLOW || "update.yml";
  const url = `https://api.github.com/repos/${env.GH_OWNER}/${env.GH_REPO}/actions/workflows/${wf}/dispatches`;
  const body = { ref: env.GH_REF || "main" };
  if (env.FORCE === "true") body.inputs = { force: "true" };
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "gh-dispatch-worker",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  // GitHub returnerar 204 No Content vid lyckad dispatch.
  return { ok: res.status === 204, status: res.status, error: res.status === 204 ? null : await res.text() };
}

export default {
  // Cron-triggern (wrangler.toml [triggers].crons) landar här.
  async scheduled(event, env, ctx) {
    if (!withinWindow(env, Date.now())) {
      console.log("gh-dispatch: utanför aktivt fönster – hoppar över");
      return;
    }
    const r = await dispatch(env);
    console.log(`gh-dispatch: ${r.ok ? "OK (204)" : "FEL " + r.status} ${r.error || ""}`);
  },

  // HTTP: GET /        → hälsa/konfig-status
  //       GET /trigger → tvinga en dispatch nu (kräver ?key=TRIGGER_KEY om satt)
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/trigger") {
      if (env.TRIGGER_KEY && url.searchParams.get("key") !== env.TRIGGER_KEY) {
        return new Response("forbidden", { status: 403 });
      }
      const r = await dispatch(env);
      return Response.json(r, { status: r.ok ? 200 : 502 });
    }
    return Response.json({
      worker: "gh-dispatch-worker",
      active_now: withinWindow(env, Date.now()),
      window: { from: env.ACTIVE_FROM || null, until: env.ACTIVE_UNTIL || null },
      target: `${env.GH_OWNER}/${env.GH_REPO} :: ${env.GH_WORKFLOW || "update.yml"} @ ${env.GH_REF || "main"}`,
      force: env.FORCE === "true",
    }, { headers: { "cache-control": "no-store" } });
  },
};
