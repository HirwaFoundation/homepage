#!/usr/bin/env python3
"""Baut die Website der Hirwa Children's Foundation aus content/ und images/.

Aufruf:  python3 build.py        -> fertige Seite liegt danach im Ordner _site/
Aufbau wie ultranicecycling.com (Jinja2-Vorlagen, Markdown/YAML, Fotos automatisch verkleinert).
"""
import datetime as dt
import html
import io
import json
import re
import shutil
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
CONTENT = ROOT / "content"
CACHE = ROOT / "_imgcache"  # fertig verkleinerte Bilder (spart Zeit beim Bauen)
WIDTHS = (400, 640, 960, 1400)  # erzeugte Bildbreiten (nie größer als das Original)


# ---------- Texte ----------
def load_yaml(name):
    p = CONTENT / name
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_md(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        return yaml.safe_load(m.group(1)) or {}, m.group(2)
    return {}, text


MD = markdown.Markdown(extensions=["extra", "sane_lists"])


def md(text):
    MD.reset()
    return Markup(responsive_images(MD.convert(str(text or ""))))


def inline_md(text):
    return Markup(re.sub(r"^<p>(.*)</p>$", r"\1", str(md(text)).strip(), flags=re.S))


# ---------- Bilder ----------
_image_cache = {}
MANIFEST = CACHE / "manifest.json"
try:
    _manifest = json.loads(MANIFEST.read_text())
except Exception:
    _manifest = {}
_SRGB = ImageCms.createProfile("sRGB")


def to_srgb(im):
    icc = im.info.get("icc_profile")
    if not icc:
        return im
    try:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        if "srgb" in ImageCms.getProfileDescription(src).lower():
            return im
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        return ImageCms.profileToProfile(im.convert(mode), src, _SRGB, outputMode=mode)
    except Exception:
        return im


def process_image(src):
    """Verkleinert ein Bild aus /images/... in mehrere Breiten (WebP). Gibt {w, h, variants} zurück."""
    if src in _image_cache:
        return _image_cache[src]
    info = None
    path = ROOT / str(src).lstrip("/")
    if str(src).startswith("/images/") and path.exists():
        key = f"{path.name}:{path.stat().st_size}"
        cached = _manifest.get(key)
        if cached and all((CACHE / Path(n).name).exists() for _, n in cached["variants"]):
            _image_cache[src] = cached
            return cached
        try:
            with Image.open(path) as im:
                im = to_srgb(ImageOps.exif_transpose(im))
                w, h = im.size
                alpha = im.mode in ("RGBA", "LA", "P") and path.suffix.lower() == ".png"
                if not alpha:
                    im = im.convert("RGB")
                variants = []
                for tw in WIDTHS:
                    if tw >= w and variants:
                        break
                    tw = min(tw, w)
                    name = f"/img/{path.stem}-{tw}.webp"
                    dest = CACHE / Path(name).name
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        r = im.resize((tw, round(h * tw / w)), Image.LANCZOS) if tw != w else im
                        r.save(dest, "WEBP", quality=90 if alpha else 78, method=4)
                    variants.append([tw, name])
                    if tw == w:
                        break
                info = {"w": w, "h": h, "variants": variants}
                _manifest[key] = info
        except Exception as e:
            print("Bild konnte nicht verarbeitet werden:", src, e)
    else:
        if src:
            print("Bild nicht gefunden:", src)
    _image_cache[src] = info
    return info


def img(src, alt="", sizes="(max-width: 760px) 100vw, 640px", cls="", eager=False):
    """<img> mit srcset. Breite/Höhe = Originalgröße, damit das Foto nie größer als seine Auflösung erscheint."""
    info = process_image(src)
    alt = html.escape(str(alt or ""), quote=True)
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ""
    if not info:
        return Markup(f'<img src="{html.escape(str(src or ""))}" alt="{alt}"{c} {load} decoding="async">')
    v = info["variants"]
    srcset = ", ".join(f"{n} {w}w" for w, n in v)
    return Markup(f'<img src="{v[min(1, len(v) - 1)][1]}" srcset="{srcset}" sizes="{sizes}" '
                  f'width="{info["w"]}" height="{info["h"]}" alt="{alt}"{c} {load} decoding="async">')


def responsive_images(html_text):
    def repl(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if not src or not src.group(1).startswith("/images/"):
            return tag
        return str(img(src.group(1), html.unescape(alt.group(1)) if alt else ""))
    return re.sub(r"<img\b[^>]*>", repl, html_text)


# ---------- Inhalte ----------
def load_folder(folder, prefix):
    items = []
    for p in sorted((CONTENT / folder).glob("*.md")):
        meta, body = read_md(p)
        if meta.get("draft"):
            continue
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", p.stem)
        d = meta.get("date")
        if isinstance(d, str):
            d = dt.date.fromisoformat(d[:10])
        if isinstance(d, dt.datetime):
            d = d.date()
        items.append({**meta, "slug": slug, "url": f"/{prefix}/{slug}/", "date": d, "body": md(body)})
    return items


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    site = load_yaml("settings.yml")
    home = load_yaml("home.yml")
    wishlist = load_yaml("wishlist.yml").get("items") or []
    projects = sorted(load_folder("projects", "projects"), key=lambda x: (x.get("order") or 99, x["title"]))
    news = sorted(load_folder("news", "news"), key=lambda x: x["date"] or dt.date.min, reverse=True)
    pages = []
    for p in sorted((CONTENT / "pages").glob("*.md")):
        meta, body = read_md(p)
        pages.append({**meta, "url": meta.get("path") or f"/{p.stem}/", "body": md(body)})

    env = Environment(loader=FileSystemLoader(ROOT / "src" / "templates"), autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["md"] = md
    env.filters["inline_md"] = inline_md
    env.filters["price"] = lambda v: (f"{v:g}" if isinstance(v, (int, float)) else str(v))
    env.filters["nice_date"] = lambda d: f"{d.day} {d:%B %Y}" if d else ""
    env.globals.update(img=img, site=site, year=dt.date.today().year, projects=projects, wishlist=wishlist)

    urls = []

    def render(template, url, **ctx):
        out = env.get_template(template).render(page_url=url, **ctx)
        dest = OUT / url.strip("/") / "index.html" if url != "/" else OUT / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        urls.append(url)

    render("home.html", "/", home=home, news=news[:3], title=None, description=site.get("description"))
    render("projects.html", "/projects/", title="Our projects", description="Six projects for the children and families of Kariyeri village in Kayonza, Rwanda.")
    for i, pr in enumerate(projects):
        render("project.html", pr["url"], page=pr, title=pr["title"], description=pr.get("teaser"),
               others=[x for x in projects if x is not pr][:3])
    render("news.html", "/news/", title="News", items=news, description="News from the Hirwa Children's Foundation.")
    for n in news:
        render("post.html", n["url"], page=n, title=n["title"], description=n.get("teaser"))
    for pg in pages:
        tpl = {"donate": "donate.html", "money": "money.html", "contact": "contact.html"}.get(pg.get("template"), "page.html")
        render(tpl, pg["url"], page=pg, title=pg["title"], description=pg.get("description"))

    (OUT / "404.html").write_text(env.get_template("404.html").render(page_url="/404", title="Page not found"), encoding="utf-8")

    # verkleinerte Bilder kopieren (nur die tatsächlich verwendeten)
    (OUT / "img").mkdir(exist_ok=True)
    for info in _image_cache.values():
        for _, name in (info or {}).get("variants", []):
            shutil.copy2(CACHE / Path(name).name, OUT / name.lstrip("/"))
    CACHE.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(_manifest, indent=0, sort_keys=True))

    shutil.copytree(ROOT / "src" / "static", OUT, dirs_exist_ok=True)
    for f in ("_redirects", "_headers"):
        if (ROOT / f).exists():
            shutil.copy(ROOT / f, OUT / f)

    base = (site.get("base_url") or "").rstrip("/")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {base}/sitemap.xml\n")
    print(f"Fertig: {len(urls)} Seiten, {len(projects)} Projekte, {len(news)} News, {len(_image_cache)} Bilder -> {OUT}")


if __name__ == "__main__":
    main()
