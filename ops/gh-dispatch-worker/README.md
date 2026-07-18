# gh-dispatch-worker

Cloudflare Worker (cron) som triggar GitHub Actions-workflowen `update.yml` via
`workflow_dispatch`. **Ersätter homelab CT 130** — ingen LXC/VM att sköta, pålitlig
timing, gratis, på samma CF-konto som analytics-dashboarden. Löser post-mortem-risk #3
(homelab i produktionsloopen).

## Varför en Worker och inte en CT/VM
Robotens jobb är att avfyra ett HTTP-anrop var 10:e minut (GitHubs egen cron är för
opålitlig i tid). Att driva en burk för det är fel form. En serverless cron gör exakt
detta utan något att babysitta. Mellan cuper står den bara still.

## Setup

1. **Skapa en fine-grained GitHub PAT** (github.com → Settings → Developer settings →
   Fine-grained tokens): endast repo `martinwelen/ahk-beach`, behörighet **Actions:
   Read and write**. Kopiera token. *(Jag hanterar inte tokens åt dig — skapa den själv.)*

2. **Installera/logga in wrangler** (om ej gjort): `npm i -g wrangler && wrangler login`.

3. **Sätt hemligheter** i den här katalogen:
   ```
   wrangler secret put GITHUB_TOKEN     # klistra in PAT:en
   wrangler secret put TRIGGER_KEY      # valfritt, valfri sträng, skyddar /trigger
   ```

4. **(Valfritt) sätt cup-fönstret** i `wrangler.toml` (`ACTIVE_FROM`/`ACTIVE_UNTIL`) så den
   bara triggar under cupen. Utan fönster = alltid aktiv.

5. **Deploya:** `wrangler deploy`.

## Verifiera

- `GET https://gh-dispatch-worker.<ditt-subdomän>.workers.dev/` → visar konfig +
  `active_now`.
- `GET …/trigger?key=<TRIGGER_KEY>` → tvingar en dispatch nu; kör
  `gh run list --workflow="Uppdatera schema"` för att se att en körning startade.
- Cron-loggar: `wrangler tail`.

## Samspel med den befintliga workflowen

- Workflowen har egna `schedule`-cron (`*/30` + turneringsvecko-`*/10`). När du flyttar
  triggern hit kan du **ta bort `schedule:`-blocket** i `.github/workflows/update.yml`
  och låta Workern äga cadencen (annars kör båda). `force`-input och den race-härdade
  pushen är oförändrade.
- **Kom ihåg:** workflowen är just nu `disabled_manually` (cupen slut). Aktivera inför
  nästa cup med `gh workflow enable "Uppdatera schema"`.

## Filer
- `worker.js` — cron-handler + `/` (hälsa) + `/trigger` (manuell).
- `wrangler.toml` — namn, cron, vars (ej hemligheter).
