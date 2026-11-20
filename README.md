# Hirwa Children's Foundation – Website

Neue Website der Hirwa Children's Foundation (Kayonza, Ruanda), umgezogen von Wix (November 2026).
Aufbau wie bei ultranicecycling.com: Texte als Dateien, eine kleine Python-Datei baut daraus die fertige Seite, Cloudflare liefert sie aus. Laufende Kosten: 0 €.

## So ist das aufgebaut

| Ordner / Datei         | Inhalt                                                        |
|------------------------|---------------------------------------------------------------|
| `content/home.yml`     | Startseite (Texte, Zahlen, Patenschafts-Box, Gründer, Besuch) |
| `content/wishlist.yml` | „What your donation buys“ (Preise in USD)                      |
| `content/settings.yml` | Name, Kontakt, Menü, Social-Media-Links, Link zur DREAM-Seite |
| `content/projects/`    | Die Projekte, je eine Textdatei (Markdown)                    |
| `content/news/`        | Neuigkeiten, je eine Textdatei                                |
| `content/pages/`       | About, Donate (+ Money/Time/Items), Community Tourism, Contact |
| `images/`              | Alle Fotos (Originale; werden beim Bauen automatisch verkleinert) |
| `src/`                 | Design (Vorlagen, CSS, Schriften) – muss man nie anfassen      |
| `build.py`             | Baut alles zur fertigen Website (Ordner `_site/`)            |
| `_redirects`           | Alte Wix-Adressen → neue Seiten                                |

Patenschaften laufen weiter über die DREAM-Seite in Notion (https://sponsor-hirwa-dream.super.site/), die die Volunteers selbst pflegen. Die Website verlinkt nur dorthin.

## Inhalte bearbeiten

Im Browser unter **/admin** (Editor Sveltia CMS, Anmeldung mit GitHub). Jede Änderung landet direkt auf `main`, die Seite baut sich danach in 1–2 Minuten neu.

## Fotos

Fotos werden nie größer gezeigt, als ihre Auflösung erlaubt (viele Originale von Wix sind klein). Beim Bauen entstehen WebP-Fassungen in 400/640/960/1400 px Breite, gespeichert in `_imgcache/`.

## Lokal bauen (optional)

```
pip install -r requirements.txt
python3 build.py
```

## Hosting (Cloudflare Workers, kostenlos)

Cloudflare-Konto `hirwa-dream` → Workers & Pages → Create → Import a repository → `HirwaFoundation/homepage`.
Build command: `pip install -r requirements.txt && python3 build.py` · Deploy command: `npx wrangler deploy` (Einstellungen in `wrangler.jsonc`).

Der Login im Editor läuft über den Worker `sveltia-cms-auth` (gleiches Cloudflare-Konto). Kommt eine neue Domain dazu, dort unter Variables `ALLOWED_DOMAINS` ergänzen.

Schriften: Bricolage Grotesque und Atkinson Hyperlegible (SIL Open Font License, siehe `src/static/fonts/`), lokal eingebunden.
