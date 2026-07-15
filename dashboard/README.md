# Privat live-dashboard (Cloudflare Web Analytics)

En liten mobil-dashboard som visar besökare senaste 5 min / timmen / idag + topp-sidor,
för AHK-sajten. Åtkomst via en **hemlig URL** (ingen inloggning). Datan kommer från din
befintliga Cloudflare Web Analytics via en Cloudflare Worker som håller API-token
server-side.

Källkoden ligger i [`stats-worker.js`](stats-worker.js). Deploy sker manuellt genom att
klistra in den i Cloudflare-dashboarden (se nedan). Inget CLI/Node behövs.

> **Om siffrorna:** Web Analytics är inte sekund-realtime – datan släpar någon/några
> minuter, och talen är samplade uppskattningar (skalas upp automatiskt), så de kan
> skilja någon procent mot Cloudflares egen vy. "Senaste 5 min" är det närmaste
> "just nu" vi kommer.

---

## Vad du behöver ta fram (3 saker)

### 1. Account ID
Cloudflare-dashboarden → välj din sajt/konto → högerspalten visar **Account ID**.
(Eller: URL:en i dashboarden innehåller `dash.cloudflare.com/<ACCOUNT_ID>/...`.)

### 2. Web Analytics "site tag"
Dashboarden → **Analytics & Logs → Web Analytics** → din sajt → **Manage site**
(eller kugghjulet). Site-taggen är strängen i JS-snippeten (`token: "xxxx…"`) – det är
`CF_SITE_TAG`.

### 3. API-token (håll hemlig!)
Dashboarden → översta högra menyn → **My Profile → API Tokens → Create Token →
Create Custom Token**:
- **Permissions:** `Account` · `Account Analytics` · `Read`
- **Account Resources:** Include → ditt konto
- Skapa och **kopiera token-strängen** (visas bara en gång). Det är `CF_API_TOKEN`.

Hitta även på en egen **hemlig path-sträng**, t.ex. `k9m2xq7p-besok` – det är `DASH_SECRET`.

---

## Skapa Workern

1. Dashboarden → **Workers & Pages → Create → Create Worker**.
2. Ge den ett namn, t.ex. `ahk-stats` (namnet blir en del av URL:en). **Deploy**.
3. Klicka **Edit code**. Radera allt i editorn och klistra in hela innehållet i
   [`stats-worker.js`](stats-worker.js). **Deploy** (uppe till höger).
4. Gå till Workerns **Settings → Variables and Secrets** och lägg till:

   | Namn | Typ | Värde |
   |------|-----|-------|
   | `CF_API_TOKEN` | Secret (Encrypt) | token från steg 3 |
   | `DASH_SECRET`  | Secret (Encrypt) | din hemliga path-sträng |
   | `CF_ACCOUNT_ID`| Text | account-id från steg 1 |
   | `CF_SITE_TAG`  | Text | site tag från steg 2 |

   **Deploy** igen så variablerna slår igenom.

---

## Använd den

Öppna på mobilen (spara som bokmärke / lägg till på hemskärmen):

```
https://ahk-stats.<ditt-subhandle>.workers.dev/<DASH_SECRET>
```

- `<ditt-subhandle>` ser du på Workerns översikt (Triggers → Routes, eller "Visit").
- Utan rätt `<DASH_SECRET>` i sökvägen svarar Workern `404`.

Snabbtest av rådatan (JSON): lägg till `/api` på slutet:
```
https://ahk-stats.<ditt-subhandle>.workers.dev/<DASH_SECRET>/api
```

---

## Felsökning

- **`404`** – fel/saknad `DASH_SECRET` i URL:en, eller variabeln inte satt/deployad.
- **`{"error":"Saknar variabler: …"}`** – någon av `CF_API_TOKEN`/`CF_ACCOUNT_ID`/`CF_SITE_TAG`
  saknas på Workern.
- **`{"error":"..."}` med GraphQL-text** – token saknar `Account Analytics: Read`, fel
  account-id, eller fel site tag. Felmeddelandet från Cloudflare visas rakt av.
- **Bara nollor** – rätt uppsatt men inga (samplade) besök i fönstret ännu, eller fel
  site tag. Jämför med Cloudflares egen Web Analytics-vy.
