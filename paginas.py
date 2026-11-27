#!/usr/bin/env python3
"""Arma una página por ciudad de salida ("Vuelos baratos desde X") con las ofertas reales
de ofertas/<CIUDAD>.json, y actualiza sitemap.xml. Lo corre GitHub Actions después de ofertas.py,
así Google encuentra páginas con precios del día."""
import json, os, re, html, datetime, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
SITIO = "https://conectorviajes.com"
NOMBRE = {"MAD": "Madrid"}  # nombres más cortos que los de la API
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def slug(t):
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def fecha(v):
    if not v:
        return ""
    a, m, d = v.split("-")
    return f"{int(d)} {MESES[int(m) - 1]}"


def ddmm(v):
    return v[8:10] + v[5:7] if v else ""


CSS = """
:root{--bg:#fff;--soft:#F5F7F8;--ink:#14232B;--muted:#5E6E76;--line:#E6EBEE;--accent:#0E8C86;--sun:#FF7A1A}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line)}header .wrap{display:flex;align-items:center;justify-content:space-between;height:60px}
.brand{display:flex;gap:8px;align-items:center;font-weight:800;font-size:20px;color:var(--ink);text-decoration:none}
h1{font-size:clamp(26px,5vw,38px);line-height:1.15;margin:28px 0 8px}
.sub{color:var(--muted);margin:0 0 22px}
.lista{display:grid;gap:10px;padding:0;margin:0 0 28px;list-style:none}
.of{display:flex;align-items:center;gap:12px;justify-content:space-between;border:1px solid var(--line);border-radius:14px;padding:14px 16px;background:#fff}
.of b{font-size:18px}.of small{display:block;color:var(--muted)}
.precio{text-align:right;white-space:nowrap}.precio b{color:var(--sun);font-size:22px}
.btn{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;border-radius:999px;padding:8px 14px;font-weight:700;font-size:14px;margin-top:4px}
.cta{background:var(--soft);border-radius:16px;padding:18px;margin:0 0 28px}
h2{font-size:20px;margin:28px 0 10px}.otras{columns:2 180px;padding:0;list-style:none;margin:0 0 40px}.otras li{margin:3px 0}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:20px 0 40px}
"""

LOGO = ('<svg width="34" height="20" viewBox="0 0 40 24" aria-hidden="true"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#0E8C86"/><stop offset="1" stop-color="#FF7A1A"/></linearGradient></defs>'
        '<path d="M20 12C16.5 6.5 13 4.5 9.5 4.5A7.5 7.5 0 0 0 9.5 19.5C13 19.5 16.5 17.5 20 12C23.5 6.5 27 4.5 30.5 4.5A7.5 7.5 0 0 1 30.5 19.5C27 19.5 23.5 17.5 20 12Z" '
        'fill="none" stroke="url(#g)" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def pagina(cod, nombre, ofertas, todas, actualizado):
    e = html.escape
    titulo = f"Vuelos baratos desde {nombre}: ofertas de hoy | Conector"
    minimo = min(o["precio"] for o in ofertas)
    desc = (f"Ofertas reales de vuelos desde {nombre}, actualizadas cada 6 horas. Ida y vuelta desde USD {minimo}: "
            + ", ".join(o["ciudad"] for o in ofertas[:5]) + " y más.")
    url = f"{SITIO}/vuelos/{slug(nombre)}/"
    filas = []
    for o in ofertas:
        esc = "Sin escalas" if not o.get("escalas") else f'{o["escalas"]} escala' + ("s" if o["escalas"] > 1 else "")
        ver = f'/?flightSearch={cod}{ddmm(o["ida"])}{o["d"]}{ddmm(o["vuelta"])}1#vuelos'
        filas.append(
            f'<li class="of"><div><b>{e(o["ciudad"])}</b><small>{fecha(o["ida"])} → {fecha(o["vuelta"])} · {esc}</small></div>'
            f'<div class="precio"><small>ida y vuelta desde</small><b>USD {o["precio"]}</b><br>'
            f'<a class="btn" href="{e(ver)}" rel="nofollow">Ver pasajes</a></div></li>')
    otras = "".join(f'<li><a href="/vuelos/{slug(n)}/">Vuelos desde {e(n)}</a></li>' for c, n in todas if c != cod)
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Vuelos baratos desde {nombre}",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f'{nombre} a {o["ciudad"]} desde USD {o["precio"]}'}
                              for i, o in enumerate(ofertas)]}
    act = actualizado[:10]
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{SITIO}/compartir.png"><meta property="og:type" content="website">
<link rel="icon" href="/logo.svg"><link rel="apple-touch-icon" href="/icono.png"><meta name="theme-color" content="#FFFFFF">
<style>{CSS}</style><script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body><header><div class="wrap"><a class="brand" href="/">{LOGO}Conector</a><a href="/#vuelos">Buscar vuelos</a></div></header>
<main class="wrap"><h1>Vuelos baratos desde {e(nombre)}</h1>
<p class="sub">Ofertas reales de ida y vuelta, actualizadas el {act}. Los precios cambian todo el tiempo: tocá "Ver pasajes" para ver el precio de hoy en tu moneda.</p>
<ul class="lista">{"".join(filas)}</ul>
<div class="cta"><b>¿No ves tu destino?</b> Buscá cualquier vuelo desde {e(nombre)} y compará todas las aerolíneas en un solo lugar.<br>
<a class="btn" href="/#vuelos">Buscar vuelos</a></div>
<h2>Vuelos baratos desde otras ciudades</h2><ul class="otras">{otras}</ul></main>
<footer><div class="wrap">© 2026 Conector · Precios en dólares estadounidenses, aproximados, para ida y vuelta por persona. Cuando reservás a través de nuestros enlaces, la plataforma de reservas puede pagarnos una comisión, sin costo extra para vos.</div></footer>
</body></html>
"""


def main():
    carpeta = os.path.join(AQUI, "ofertas")
    indice = json.load(open(os.path.join(carpeta, "index.json"), encoding="utf-8"))
    todas = sorted(((c, NOMBRE.get(c, n)) for c, n in indice["origenes"].items()), key=lambda x: x[1])
    urls = [(SITIO + "/", "daily")]
    for cod, nombre in todas:
        ruta = os.path.join(carpeta, cod + ".json")
        if not os.path.exists(ruta):
            continue
        ofertas = json.load(open(ruta, encoding="utf-8")).get("ofertas", [])
        if not ofertas:
            continue
        dest = os.path.join(AQUI, "vuelos", slug(nombre))
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina(cod, nombre, ofertas, todas, indice["actualizado"]))
        urls.append((f"{SITIO}/vuelos/{slug(nombre)}/", "daily"))
    hoy = datetime.date.today().isoformat()
    with open(os.path.join(AQUI, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u, freq in urls:
            f.write(f"  <url><loc>{u}</loc><lastmod>{hoy}</lastmod><changefreq>{freq}</changefreq></url>\n")
        f.write("</urlset>\n")
    print(len(urls) - 1, "páginas de vuelos")


if __name__ == "__main__":
    main()
