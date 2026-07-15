# Privat live-dashboard för Cloudflare Web Analytics

**Datum:** 2026-07-15
**Status:** Godkänd design

## Mål

En liten, privat mobil-dashboard som visar besöksstatistik för AHK-sajten "live",
enklare än Cloudflares egen vy. Åtkomst via en hemlig URL (ingen inloggning behövs).

## Verklighetskoll

Sajten mäts med **Cloudflare Web Analytics** (cookieless RUM). Den datan är inte
sekund-realtime — den släpar typiskt någon/några minuter. "Besök senaste 5 min" är
det närmaste "just nu" vi kommer. Detta är accepterat.

## Arkitektur

En enda Cloudflare Worker (ett JS-fil som klistras in i dashboard-editorn) med två roller
beroende på path:

- `GET /<DASH_SECRET>` → serverar dashboard-sidan: självständig HTML med inline CSS/JS,
  mobil-först, mörkt tema.
- `GET /<DASH_SECRET>/api` → hämtar statistik server-side från Cloudflares GraphQL
  Analytics API och returnerar JSON.
- Allt annat (fel/saknad secret) → `404` utan att avslöja att sidan finns.

Hemlig URL: `https://ahk-stats.<subhandle>.workers.dev/<DASH_SECRET>`.
API-token ligger som Worker-secret och exponeras aldrig mot klienten.

## Konfiguration (Worker-variabler/secrets, sätts i CF-dashboarden)

| Namn | Typ | Beskrivning |
|------|-----|-------------|
| `CF_API_TOKEN` | Secret | Cloudflare API-token med *Account Analytics: Read* |
| `CF_ACCOUNT_ID` | Var | Cloudflare account-id |
| `CF_SITE_TAG` | Var | Web Analytics site tag (CF > Web Analytics) |
| `DASH_SECRET` | Secret | Hemlig path-sträng som gate |

## Data

GraphQL-endpoint: `https://api.cloudflare.com/client/v4/graphql`.
Dataset: `rumPageloadEventsAdaptiveGroups` under `viewer.accounts`, filtrerat på `siteTag`.

Fyra snitt hämtas per `/api`-anrop:

1. Besök + sidvisningar senaste 5 min (`datetime_geq = now-5min`).
2. Besök + sidvisningar senaste 60 min.
3. Besök + sidvisningar sedan midnatt (Europe/Stockholm — beräknas i Workern som kör UTC).
4. Topp-sidor senaste 60 min: grupperat på sökväg, sorterat på antal desc, topp ~8.

Headline-siffra = **besök** (`sum.visits`). Sidvisningar (`count`) visas sekundärt.
Exakta GraphQL-fältnamn verifieras mot CF-docs vid implementation.

## Beteende

- Sidan pollar `/<DASH_SECRET>/api` var 30:e sekund (ingen helsides-reload).
- Visar stora siffror + "uppdaterad kl. HH:MM:SS".
- Vid API-fel: behåll senast kända siffror, visa diskret varning.

## Felhantering

- Saknad/fel secret → `404`.
- GraphQL-fel eller token-fel → `/api` svarar med `{ error }`; klienten behåller senaste värden.

## Leverans

- Källkod i repot som referens: `dashboard/stats-worker.js`.
- Setup-guide: `dashboard/README.md` (skapa token, hitta site tag & account-id,
  skapa worker, klistra in, sätt variabler, testa på mobil).
- Deploy sker manuellt via copy-paste i CF-dashboarden (ej i CI).

## Test / verifiering

- Manuell checklista: öppna hemlig URL på mobil, jämför siffror grovt mot CF:s egen
  Web Analytics-vy (får släpa någon minut), verifiera att fel secret ger 404.
