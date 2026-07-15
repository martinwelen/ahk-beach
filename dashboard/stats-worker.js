/**
 * AHK – privat live-dashboard för Cloudflare Web Analytics.
 *
 * En enda Cloudflare Worker. Klistras in i CF dashboard > Workers-editorn.
 * Se dashboard/README.md för setup (token, site tag, variabler).
 *
 * Routes (allt annat -> 404):
 *   GET /<DASH_SECRET>       -> dashboard-sidan (HTML)
 *   GET /<DASH_SECRET>/api   -> statistik som JSON
 *
 * Variabler/secrets som måste sättas på Workern:
 *   CF_API_TOKEN   (secret) – token med "Account Analytics: Read"
 *   CF_ACCOUNT_ID  (var)    – ditt Cloudflare account-id
 *   CF_SITE_TAG    (var)    – Web Analytics site tag
 *   DASH_SECRET    (secret) – hemlig path-sträng
 */

const GRAPHQL_ENDPOINT = "https://api.cloudflare.com/client/v4/graphql";
const TZ = "Europe/Stockholm";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const secret = env.DASH_SECRET;
    const parts = url.pathname.split("/").filter(Boolean);

    // Gate: fel eller saknad secret avslöjar inget.
    if (!secret || parts[0] !== secret) {
      return new Response("Not found", { status: 404 });
    }

    if (parts.length === 1) {
      return new Response(pageHtml(secret), {
        headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
      });
    }

    if (parts.length === 2 && parts[1] === "api") {
      return handleApi(env);
    }

    return new Response("Not found", { status: 404 });
  },
};

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function handleApi(env) {
  try {
    const missing = ["CF_API_TOKEN", "CF_ACCOUNT_ID", "CF_SITE_TAG"].filter((k) => !env[k]);
    if (missing.length) {
      return json({ error: `Saknar variabler: ${missing.join(", ")}` }, 500);
    }

    const now = new Date();
    const nowIso = now.toISOString();
    const since5 = new Date(now.getTime() - 5 * 60_000).toISOString();
    const since60 = new Date(now.getTime() - 60 * 60_000).toISOString();
    const sinceDay = new Date(stockholmMidnightUtc(now)).toISOString();

    const query = buildQuery(env.CF_SITE_TAG, { nowIso, since5, since60, sinceDay });

    const resp = await fetch(GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${env.CF_API_TOKEN}`,
      },
      body: JSON.stringify({
        query,
        variables: { accountTag: env.CF_ACCOUNT_ID },
      }),
    });

    const body = await resp.json();
    if (body.errors && body.errors.length) {
      return json({ error: body.errors.map((e) => e.message).join("; ") }, 502);
    }

    const acct = body?.data?.viewer?.accounts?.[0];
    if (!acct) {
      return json({ error: "Inget account-data i svaret (kolla account-id/token)." }, 502);
    }

    return json({
      updated: nowIso,
      last5: agg(acct.last5),
      last60: agg(acct.last60),
      today: agg(acct.today),
      topPages: (acct.topPages || []).map((row) => ({
        path: row?.dimensions?.requestPath || "(okänd)",
        views: est(row.count, row.avg?.sampleInterval),
      })),
    });
  } catch (err) {
    return json({ error: String(err) }, 500);
  }
}

// Adaptivt samplat: skalar upp med genomsnittligt sampleInterval för att
// uppskatta verkliga tal (matchar ~CF:s egen vy; kan skilja någon %).
function est(count, sampleInterval) {
  const si = sampleInterval || 1;
  return Math.round((count || 0) * si);
}

function agg(rows) {
  const r = rows && rows[0];
  if (!r) return { visits: 0, views: 0 };
  const si = r.avg?.sampleInterval || 1;
  return {
    visits: Math.round((r.sum?.visits || 0) * si),
    views: Math.round((r.count || 0) * si),
  };
}

function buildQuery(siteTag, t) {
  // Datetime-värden interpoleras direkt (server-genererade ISO-strängar, ingen
  // injektionsrisk). siteTag likaså – kommer från env.
  const win = (geq, leq) =>
    `filter: { siteTag: "${siteTag}", datetime_geq: "${geq}", datetime_leq: "${leq}" }`;
  return `
    query ($accountTag: String!) {
      viewer {
        accounts(filter: { accountTag: $accountTag }) {
          last5: rumPageloadEventsAdaptiveGroups(limit: 1, ${win(t.since5, t.nowIso)}) {
            count
            sum { visits }
            avg { sampleInterval }
          }
          last60: rumPageloadEventsAdaptiveGroups(limit: 1, ${win(t.since60, t.nowIso)}) {
            count
            sum { visits }
            avg { sampleInterval }
          }
          today: rumPageloadEventsAdaptiveGroups(limit: 1, ${win(t.sinceDay, t.nowIso)}) {
            count
            sum { visits }
            avg { sampleInterval }
          }
          topPages: rumPageloadEventsAdaptiveGroups(
            limit: 8, orderBy: [count_DESC], ${win(t.since60, t.nowIso)}
          ) {
            count
            avg { sampleInterval }
            dimensions { requestPath }
          }
        }
      }
    }`;
}

// UTC-tidpunkten för senaste midnatt i svensk tid.
function stockholmMidnightUtc(now) {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const p = {};
  for (const part of dtf.formatToParts(now)) p[part.type] = part.value;
  // Offset (lokal vägg-tid tolkad som UTC) - verklig UTC.
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  const offset = asUtc - now.getTime();
  // Lokal midnatt tolkad som UTC, minus offset = verklig UTC-tidpunkt.
  return Date.UTC(+p.year, +p.month - 1, +p.day, 0, 0, 0) - offset;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

// ---------------------------------------------------------------------------
// Dashboard-sidan
// ---------------------------------------------------------------------------

function pageHtml(secret) {
  const apiPath = `/${secret}/api`;
  return `<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>AHK · besökare</title>
<style>
  :root { --bg:#0b0f14; --card:#141b24; --line:#20303f; --fg:#e8eef5; --muted:#7d92a6; --accent:#38bdf8; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; background:var(--bg); color:var(--fg);
    font:16px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:520px; margin:0 auto; padding:20px 16px 48px; }
  header { display:flex; align-items:baseline; justify-content:space-between; gap:8px; margin-bottom:16px; }
  h1 { font-size:18px; margin:0; font-weight:700; }
  .upd { font-size:12px; color:var(--muted); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; }
  .card.wide { grid-column:1 / -1; }
  .label { font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
  .big { font-size:44px; font-weight:800; line-height:1; margin:8px 0 2px; font-variant-numeric:tabular-nums; }
  .sub { font-size:13px; color:var(--muted); }
  .live .big { color:var(--accent); }
  ul { list-style:none; margin:8px 0 0; padding:0; }
  li { display:flex; justify-content:space-between; gap:12px; padding:7px 0; border-top:1px solid var(--line);
    font-variant-numeric:tabular-nums; }
  li:first-child { border-top:0; }
  li .p { color:var(--fg); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  li .n { color:var(--muted); flex:0 0 auto; }
  .warn { display:none; margin-top:14px; font-size:13px; color:#fca5a5; }
  .warn.show { display:block; }
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--accent);
    margin-right:6px; vertical-align:middle; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }
  footer { margin-top:22px; font-size:11px; color:var(--muted); text-align:center; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="dot"></span>AHK · besökare</h1>
    <span class="upd" id="upd">…</span>
  </header>

  <div class="grid">
    <div class="card live">
      <div class="label">Senaste 5 min</div>
      <div class="big" id="v5">–</div>
      <div class="sub"><span id="pv5">–</span> sidvisningar</div>
    </div>
    <div class="card">
      <div class="label">Senaste timmen</div>
      <div class="big" id="v60">–</div>
      <div class="sub"><span id="pv60">–</span> sidvisningar</div>
    </div>
    <div class="card wide">
      <div class="label">Idag</div>
      <div class="big" id="vday">–</div>
      <div class="sub"><span id="pvday">–</span> sidvisningar</div>
    </div>
    <div class="card wide">
      <div class="label">Topp-sidor · senaste timmen</div>
      <ul id="top"><li><span class="p">…</span></li></ul>
    </div>
  </div>

  <div class="warn" id="warn"></div>
  <footer>Cloudflare Web Analytics · samplat, uppdateras var 30:e sek · siffror kan släpa någon minut</footer>
</div>

<script>
const API = ${JSON.stringify(apiPath)};
const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat("sv-SE");

function paint(d) {
  $("v5").textContent   = nf.format(d.last5.visits);
  $("pv5").textContent  = nf.format(d.last5.views);
  $("v60").textContent  = nf.format(d.last60.visits);
  $("pv60").textContent = nf.format(d.last60.views);
  $("vday").textContent = nf.format(d.today.visits);
  $("pvday").textContent= nf.format(d.today.views);

  const top = $("top");
  if (d.topPages && d.topPages.length) {
    top.innerHTML = d.topPages
      .map((r) => '<li><span class="p">' + esc(r.path) + '</span><span class="n">' + nf.format(r.views) + "</span></li>")
      .join("");
  } else {
    top.innerHTML = '<li><span class="p">Inga besök senaste timmen</span></li>';
  }

  const t = new Date(d.updated);
  $("upd").textContent = "kl. " + t.toLocaleTimeString("sv-SE");
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
}

async function tick() {
  try {
    const r = await fetch(API, { cache: "no-store" });
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    paint(d);
    $("warn").classList.remove("show");
  } catch (e) {
    const w = $("warn");
    w.textContent = "⚠ Kunde inte uppdatera (" + e.message + ") – visar senaste kända.";
    w.classList.add("show");
  }
}

tick();
setInterval(tick, 30000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
</script>
</body>
</html>`;
}
