# FB Bot Scan — Vilnius Rental Scanner

Locally-run web app that scans private Facebook rental groups in Vilnius and surfaces relevant summer rental listings.

## Setup (Windows)

1. Install Python 3.11+
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `playwright install chromium`
6. Double-click `run.bat` (or run `python -m src.app`)
7. Open `http://localhost:5000` in your browser
8. Click "Login a Facebook" — a Chrome window opens, log in (2FA OK), session saved automatically

## Usage

- Click "Scansiona" to scan all enabled groups
- Use sticky filters at top of dashboard to narrow results without re-scanning
- Click on a card photo for full view; click "FB" to open original post
- Mark "Ignora" to hide a post from future views

## Data location

Cookies and database stored in `%APPDATA%\fb-bot-scan\` (NOT in this repo).

## Configuration

Edit defaults at `/config` page in the running app, or directly in `%APPDATA%\fb-bot-scan\config.json`.

## Design docs

- Spec: `docs/superpowers/specs/2026-05-11-fb-vilnius-rental-scanner-design.md`
- Plan: `docs/superpowers/plans/2026-05-11-fb-vilnius-rental-scanner.md`
