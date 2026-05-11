# FB Bot Scan — Vilnius Rental Scanner

**Status:** Draft for review
**Date:** 2026-05-11
**Author:** Matas (proprietario), assistito da Claude

---

## 1. Obiettivo

Costruire un'applicazione locale a uso personale che, su comando manuale dell'utente, scansioni 4 gruppi privati Facebook di affitti a Vilnius, estragga i post pubblicati nelle ultime 36 ore, applichi un set di filtri (date estive, budget, quartiere) e mostri i risultati su una dashboard web locale ordinati per priorità, con traduzione italiana del testo originale lituano.

L'utente cerca un alloggio in affitto per l'estate 2026 a Vilnius (1 giugno – 1 settembre, con tolleranza: inizio ≤ 10 giugno, fine ≥ 27 agosto), budget ≤ €600/mese (max €650), preferendo quartieri centrali.

## 2. Non-goal

- Niente invio automatico di messaggi su Messenger (rischio ban troppo alto)
- Niente uso di LLM per parsing (regex + keyword sufficienti, traduzione via servizio gratuito)
- Niente scansione automatica programmata (cron) → trigger sempre manuale
- Niente multi-utente, niente autenticazione della webapp (gira solo in locale)
- Niente supporto a piattaforme diverse da Vilnius/lituano

## 3. Vincoli e considerazioni

- **Termini di servizio Facebook**: lo scraping automatizzato viola i TOS. Mitigazioni: trigger manuale, browser visibile, delay umani, nessuna programmazione cron, uso della sessione autenticata dell'utente
- **Account FB dell'utente è in gioco**: salviamo i cookie in locale (`auth_state.json`), mai committati su git
- **Gruppi privati**: richiedono sessione autenticata; l'utente è già membro dei 4 gruppi
- **Lingua**: prevalentemente lituano, occasionalmente inglese o russo
- **Volume**: ~50 post/giorno totali tra i 4 gruppi
- **Piattaforma utente**: Windows 11, Python 3.11+ richiesto

## 4. Architettura

```
┌─────────────────────────────────────────────────────────────┐
│  Browser dell'utente (http://localhost:5000)                │
│  Dashboard Flask: filtri sticky + griglia card di risultati │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP
              ┌───────▼────────┐
              │   Flask app    │  src/app.py
              └───────┬────────┘
                      │
       ┌──────────────┼──────────────────────────┐
       ▼              ▼                          ▼
 ┌──────────┐   ┌─────────────┐          ┌──────────────┐
 │ Scanner  │   │  Analyzer   │          │  Translator  │
 │ (async)  │   │  (regex +   │          │  (deep-      │
 │ Playwright│  │   keyword)  │          │   translator)│
 │ scanner.py│  │ analyzer.py │          │translator.py │
 └────┬─────┘   └──────┬──────┘          └──────┬───────┘
      │                │                        │
      └────────────────▼────────────────────────┘
                ┌──────────────┐
                │   SQLite     │  data/posts.db
                │   db.py      │
                └──────────────┘
```

**Flusso end-to-end:**

1. Utente apre `http://localhost:5000`, clicca "Scansiona"
2. Flask lancia uno scan job (background thread, non blocca la UI)
3. Scanner carica `auth_state.json`, apre Chromium con Playwright (headed, sempre visibile), va sui 4 gruppi uno per volta
4. Per ogni gruppo: scrolla finché trova post più vecchi di 36h (con cutoff di sicurezza dopo N post)
5. Estrae per ogni post: ID, URL, autore, timestamp, testo, URL foto
6. Per ogni post nuovo (non in DB): Analyzer assegna tier + estrae prezzo/date/quartiere; Translator traduce testo in italiano
7. Salva nel DB con timestamp di scoperta
8. UI fa polling su `/api/status` finché completo, poi `/api/posts` per renderizzare

## 5. Componenti

### 5.1 Scanner (`src/scanner.py`)

**Libreria:** `playwright` (sync API)

**Responsabilità:**
- Caricare `auth_state.json` (cookie + storage)
- Per ogni gruppo in config: navigare a `https://www.facebook.com/groups/<id>`
- Risolvere i `share/g/<hash>` link al primo avvio: Playwright li segue e cattura l'URL finale, da cui si estrae il group ID
- Scroll incrementale: scroll → wait 2-6s random → fino a quando l'ultimo post visibile è più vecchio di `lookback_hours` (default 36) o si raggiunge `max_posts_per_group` (default 80)
- Estrazione DOM: selettori robusti basati su `role="article"` / `data-pagelet` (NB: i selettori FB cambiano spesso, isolarli in `selectors.py` per facilitare manutenzione)
- Per ogni post: `post_id`, `post_url`, `author_name`, `author_url`, `posted_at`, `text`, `photo_urls[]`

**Anti-detection:**
- Browser headed, sempre `--no-headless`
- Random delay 2-6s tra scroll/azioni
- Random delay 5-15s tra un gruppo e l'altro
- User-agent reale (Playwright default va bene)
- Viewport 1280x800
- Non lanciare mai in concorrenza con altre scansioni

**Errori gestiti:**
- Sessione scaduta → flag "session_expired" su `/api/status`, UI mostra "Re-login" che apre il browser per nuova autenticazione
- Gruppo non accessibile (rimosso, ban, ...) → segna nel log, continua con i successivi
- DOM cambiato → log dei post falliti, continua

### 5.2 Analyzer (`src/analyzer.py`)

**Responsabilità:** dato un testo grezzo, ritornare un dict:

```python
{
  "price_eur": int | None,
  "date_start": date | None,
  "date_end": date | None,
  "neighborhood": str | None,
  "neighborhood_tier": "green" | "yellow" | "red" | None,
  "duration_signal": "summer" | "available_now" | "short_term" | "long_term" | None,
  "tier": "S" | "A" | "B" | "C" | "D" | "E" | "over_budget" | "skip",
  "match_reasons": [str],  # debug: cosa ha fatto scattare il tier
}
```

**Regex prezzi:**
- Pattern principale: `(\d{2,4})\s*(?:€|EUR|eur|Eur|euro|eurų|EU)\b`
- Pattern inverso: `(?:€|EUR|eur)\s*(\d{2,4})`
- Pattern "x €/mėn": `(\d{2,4})\s*€?\s*/?\s*mėn`
- Filtro: 100 ≤ valore ≤ 2000 (esclude depositi misinterpretati e numeri di telefono parziali)
- Sceglie il **massimo** trovato (di solito il mensile)
- Soglie tier-relevant: `≤ 600` (top), `≤ 650` (ok), `≤ 700` (vicino al budget, sezione separata), `> 700` (skip)

**Regex date:**
- Numerico range: `(\d{1,2})[\.\-/](\d{1,2})\s*[-–—]\s*(\d{1,2})[\.\-/](\d{1,2})`
  Esempio: "06.01-09.01" o "1/6 - 1/9"
- ISO: `(\d{4})[\.\-/](\d{1,2})[\.\-/](\d{1,2})` con range opzionale
- Mesi LT (sia nominativo che genitivo):
  - giugno: `birželis|birželio|birzelis|birzelio|bir\\.`
  - luglio: `liepa|liepos|liep\\.`
  - agosto: `rugpjūtis|rugpjūčio|rugpjutis|rugpjucio|rugpj\\.`
  - settembre: `rugsėjis|rugsėjo|rugsejis|rugsejo|rugs\\.`
- Mesi EN: `January|February|...|September` (full e abbr.)
- Mesi RU: `июнь|июля|август|августа|сентябрь|сентября`
- Heuristic: se trovo un range di mesi senza giorno (es. "birželis-rugpjūtis"), assumo giorno 1 inizio e giorno 30/31 fine

**Disambiguazione anno:** assumi anno corrente se non specificato; se data calcolata < oggi-30 giorni, assumi anno successivo.

**Date logica tier:**
- ⭐ `summer_explicit_match` = (`date_start` ≤ 10 giugno) **AND** (`date_end` ≥ 27 agosto)
- 👍 `available_now` = matcha keyword `iškart|nuo dabar|šiandien|laisvas|available now|free now|move in|сразу`
- 🤷 `dates_unclear` = niente date estratte
- ❌ `dates_conflict` = date trovate ma fuori finestra (es. tutto l'anno scolastico, settembre-giugno)

**Keyword durata:**
- Summer-preferred (positivi): `vasarai|vasaros|vasarą|на лето|summer rent|for summer`
- Short-term (positivi soft): `trumpalaikė|trumpam|short-term|short term`
- Long-term (negativi soft, declassano): `ilgalaikė|ilgam|long-term|long term|metams`

**Keyword quartiere (case+accent insensitive, normalizzati):**
- 🟢 green: `senamiestis, užupis, naujamiestis, žvėrynas, paupys, šnipiškės, antakalnis`
- 🟡 yellow: `šeškinė, žirmūnai`
- 🟢 green-landmark: `katedra, gediminas, gedimino` (centro storico)
- 🟡 yellow-landmark: `ozas, akropolis`
- 🔴 red: `fabijoniškės, karoliniškės, viršuliškės, lazdynai, justiniškės, pilaitė, naujininkai, baltupiai, jeruzalė`

**Tier finale (decisione):**

| Tier | Condizione |
|------|------------|
| ⭐ S | `summer_explicit_match` + green + price ≤ 650 |
| ⭐ A | `summer_explicit_match` + yellow + price ≤ 650 |
| 👍 B | `available_now` + green + price ≤ 650 |
| 🤷 C | `dates_unclear` + green + (price ≤ 650 or no price) + non `long_term` |
| 🟡 D | (`available_now` or `dates_unclear`) + yellow + price ≤ 650 |
| 🔴 E | (`summer_explicit_match` or `available_now`) + red + price ≤ 650 |
| 💸 over_budget | tutti gli altri ma `650 < price ≤ 700` |
| skip | `dates_conflict`, `long_term` esplicito senza match estate, `price > 700`, oppure tutti red + dates_unclear |

`match_reasons` registra le keyword/regex che hanno fatto scattare ogni decisione (utile per debug nella UI).

### 5.3 Translator (`src/translator.py`)

**Libreria:** `deep-translator` (Python, free, wrappa Google Translate web)

- Input: testo originale + lingua sorgente (auto-detect, default `lt`)
- Output: testo tradotto in italiano
- Cache: già tradotto → riusa (chiave: hash del testo + lingua sorgente)
- Errori (rate-limit/timeout): ritorna `None`, la UI mostra "Traduzione non disponibile, mostro originale"
- Throttle: max 1 chiamata ogni 0.5s per non farsi rate-limitare

**Backup se deep-translator viene rate-limitato:** in V2 valuteremo LibreTranslate self-hosted o l'API Claude (opt-in nell'UI).

### 5.4 Web app (`src/app.py`)

**Framework:** Flask (semplice, sync, perfetto per locale single-user)

**Endpoints:**
- `GET /` — dashboard HTML
- `POST /api/scan` — avvia uno scan job in background thread, ritorna `{job_id}`
- `GET /api/status` — `{state: "idle|running|done|error", progress: {group: N/total}, last_run: ts}`
- `GET /api/posts?tier=S,A,B&...filters` — JSON dei post filtrati lato server
- `POST /api/posts/<id>/ignore` — segna post come ignorato
- `GET /config` — pagina HTML config
- `POST /api/config` — salva config
- `POST /api/login` — apre Playwright per login interattivo, salva nuovo `auth_state.json`

**Scan job:** lancio in `threading.Thread`, stato in variabile globale protetta da lock. Una sola scansione alla volta (bottone disabilitato se `running`).

### 5.5 Storage (`src/db.py`)

**SQLite** in `data/posts.db`. Schema:

```sql
CREATE TABLE posts (
  id TEXT PRIMARY KEY,           -- FB post ID
  group_id TEXT NOT NULL,
  url TEXT NOT NULL,
  author_name TEXT,
  author_url TEXT,
  posted_at TIMESTAMP,
  text_original TEXT,
  text_translated TEXT,
  language TEXT,                  -- lt/en/ru/...
  price_eur INTEGER,
  date_start DATE,
  date_end DATE,
  neighborhood TEXT,
  neighborhood_tier TEXT,         -- green/yellow/red
  duration_signal TEXT,
  tier TEXT NOT NULL,             -- S/A/B/C/D/E/over_budget/skip
  match_reasons TEXT,             -- JSON array
  photo_urls TEXT,                -- JSON array
  discovered_at TIMESTAMP NOT NULL,
  is_ignored INTEGER DEFAULT 0
);

CREATE INDEX idx_tier ON posts(tier, discovered_at DESC);
CREATE INDEX idx_posted ON posts(posted_at DESC);

CREATE TABLE scan_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  status TEXT,                    -- running/done/error
  posts_found INTEGER DEFAULT 0,
  posts_new INTEGER DEFAULT 0,
  error_message TEXT
);
```

**Dedup:** primary key è il FB post ID (estratto dall'URL del post). Inserimento con `INSERT OR IGNORE`.

## 6. UI — Dashboard

**Layout:** una pagina, una colonna principale con filtri sticky in cima e griglia di card sotto.

```
┌────────────────────────────────────────────────────────────────┐
│ 🏠 FB Bot Scan — Vilnius Estate 2026          [⚙ Config]        │
│                                                                │
│ [🔄 Scansiona]  Ultimo: 11/05/2026 14:30  ✅ Sessione attiva   │
│ 📊 47 nuovi · ⭐ 3 · 👍 7 · 🤷 12 · 🟡 5 · 🔴 2 · 💸 3          │
└────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────┐
│ FILTRI (sticky)                                                │
│ Prezzo: [____ €] – [____ €]   Quartieri: [🟢] [🟡] [🔴]        │
│ Date: [_____] – [_____]       Tier: [⭐][👍][🤷][🟡][🔴][💸]   │
│ ☐ Solo non visti  ☐ Nascondi ignorati                          │
└────────────────────────────────────────────────────────────────┘

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ [🖼 foto grande] │ │ [🖼 foto grande] │ │ [🖼 foto grande] │
│ [🖼][🖼][🖼]     │ │ [🖼][🖼]         │ │                  │
│ ──────────────── │ │ ──────────────── │ │ ──────────────── │
│ ⭐ S · €580/mese │ │ 👍 B · €600/mese │ │ 🤷 C · prezzo?   │
│ 📅 5/6 → 30/8    │ │ 📅 disp. subito  │ │ 📅 ?             │
│ 📍 Užupis        │ │ 📍 Naujamiestis  │ │ 📍 Antakalnis    │
│ ──────────────── │ │ ──────────────── │ │ ──────────────── │
│ Affitto monolo-  │ │ Disponibile da   │ │ Cerco inquilino  │
│ cale per estate… │ │ subito appart…   │ │ per camera…      │
│ [Mostra LT]      │ │ [Mostra LT]      │ │ [Mostra LT]      │
│ ──────────────── │ │ ──────────────── │ │ ──────────────── │
│ [🔗 FB] [✖ ign.] │ │ [🔗 FB] [✖ ign.] │ │ [🔗 FB] [✖ ign.] │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

- Griglia responsive: 3 colonne su desktop largo, 2 su laptop, 1 su mobile
- Foto: prima foto in alto grande, altre come thumbnail
- Click su foto → lightbox
- Tier in alto come badge colorato + emoji
- "Mostra LT" toggle che mostra il testo originale sotto la traduzione
- "Ignora" → animazione di dissolvenza, post nascosto (può essere ripristinato da `/config`)
- Le card sono ordinate per (tier_rank asc, posted_at desc)

**Auto-refresh durante scan:** mentre uno scan è in corso, la dashboard mostra una progress bar in cima ("Scansionando gruppo 2/4...") e fa polling su `/api/status` ogni 3s. Quando done, ricarica i post.

## 7. Pagina `/config`

Editabile direttamente nella UI:
- **Gruppi FB**: lista di URL/ID + nome amichevole, possibilità di disabilitare temporaneamente
- **Budget**: ideale, max, near-budget threshold
- **Date estate**: inizio max, fine min
- **Quartieri**: liste green/yellow/red modificabili
- **Keyword**: liste duration/availability con possibilità di aggiungere
- **Scan options**: `lookback_hours`, `max_posts_per_group`, delay range
- **Sessione FB**: bottone "Re-login" che lancia Playwright in modalità interattiva
- **Reset DB**: bottone per cancellare tutti i post (utile per ri-analizzare con regole nuove)

Salvataggio in `config.json` (gitignored).

## 8. Login flow

**Primo avvio:**
1. UI rileva che `auth_state.json` non esiste
2. Mostra "Effettua login a Facebook"
3. Click → backend lancia Playwright headed
4. Utente fa login a mano (anche 2FA)
5. Quando utente preme "Salva sessione" sulla UI (o quando rileva un cookie session valido), Playwright salva `auth_state.json`

**Run successivi:**
- Playwright carica `storage_state="auth_state.json"`
- Se durante lo scan riceve redirect a login page → emette `session_expired`, UI prompta re-login

## 9. Struttura del progetto

```
FB Bot Scan/                      # repo git (codice + spec)
├── .gitignore
├── README.md
├── requirements.txt
├── config.example.json          # template committato (no dati reali)
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-11-fb-vilnius-rental-scanner-design.md
├── src/
│   ├── __init__.py
│   ├── app.py                   # Flask
│   ├── scanner.py               # Playwright
│   ├── selectors.py             # selettori DOM FB isolati
│   ├── analyzer.py              # regex + keyword
│   ├── translator.py            # deep-translator wrapper
│   ├── db.py                    # SQLite layer
│   ├── models.py                # dataclasses
│   └── config.py                # caricamento config.json
├── static/
│   ├── style.css
│   └── app.js
├── templates/
│   ├── base.html
│   ├── index.html               # dashboard
│   └── config.html
├── tests/
│   ├── test_analyzer.py         # parsing regex su esempi lituani
│   └── test_db.py
└── run.bat                      # avvio one-click su Windows

%APPDATA%/fb-bot-scan/            # dati runtime (fuori dal repo)
├── config.json                  # config utente
├── auth_state.json              # cookie sessione FB
└── posts.db                     # database SQLite
```

Al primo avvio l'app crea `%APPDATA%/fb-bot-scan/` se non esiste e copia `config.example.json` come `config.json` iniziale.

## 10. Dipendenze (requirements.txt)

```
flask>=3.0
playwright>=1.41
deep-translator>=1.11
python-dateutil>=2.8
```

Setup post-install: `playwright install chromium`.

## 11. Sicurezza & Privacy

- **Nulla esce dal locale** tranne: (a) request al sito Google Translate via deep-translator (testo del post), (b) connessioni a facebook.com con la sessione utente
- **Cookie FB e DB**: salvati in `%APPDATA%/fb-bot-scan/` (su Windows: `C:\Users\<utente>\AppData\Roaming\fb-bot-scan\`). Fuori da OneDrive, fuori dal repo git. Il path è risolto a runtime via `os.environ['APPDATA']` (Windows) o `~/.local/share/fb-bot-scan/` (Linux/macOS, per portabilità futura)
- **Git**: `.gitignore` esclude `auth_state.json`, `config.json`, `data/*.db`. Solo `config.example.json` viene committato
- **Credenziali**: niente username/password salvati nel codice; tutto basato su cookie post-login interattivo

## 12. Test

Unit test focalizzati sull'Analyzer perché è il pezzo con la logica più complessa:
- Suite di ~30 esempi reali di post in lituano/inglese/russo con expected output (price, date, neighborhood, tier)
- Test edge case: prezzo singolo vs range, date senza anno, date con anno passato, post senza date
- Test dedup DB

Scanner e Translator: smoke test manuali in dev.

## 13. Open question (da risolvere prima/durante implementazione)

1. ~~**Spostare auth_state fuori da OneDrive?**~~ **RISOLTO 2026-05-11:** auth_state, config e DB stanno in `%APPDATA%/fb-bot-scan/`. Codice e spec restano nella cartella di progetto OneDrive (ok perché niente sensibile)
2. **Cosa fare se i selettori FB cambiano?** — Mitigazione: `selectors.py` isolato, log esplicito, fallback su parsing più permissivo
3. **Rate limit di deep-translator?** — V1: throttle 0.5s/req. Se diventa problema, opzione "usa Claude API" attivabile in `/config`
4. **Quanti scroll massimi prima di fermarsi?** — Default 80 post/gruppo, configurabile
5. **Come gestire post sponsorizzati o reshare?** — V1: log e skip

## 14. Roadmap iterazioni

**V1 (questo spec):**
- Tutto il sopra elencato, una scansione end-to-end funzionante
- 4 gruppi noti, criteri filtraggio definiti
- UI dashboard + config

**V2 (eventuale, fuori scope):**
- Notifiche desktop/Telegram quando un ⭐ S appare
- Auto-archiviazione di post vecchi >30gg
- Diff tra scansioni: "questo annuncio è cambiato"
- Export CSV
- Statistiche: prezzi medi per quartiere, ecc.

## 15. Repository git

Codice da pushare su `https://github.com/matas300/Playwright.git` (repo vuoto dell'utente).

Setup:
1. `git init`
2. Aggiungere `.gitignore` con i file sensibili
3. Primo commit con scheletro + spec
4. `git remote add origin https://github.com/matas300/Playwright.git`
5. `git push -u origin main`

⚠️ **Prima del primo push**, verificare che `auth_state.json` e `config.json` non finiscano nel commit.
