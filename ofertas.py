#!/usr/bin/env python3
"""Busca ofertas de vuelos reales (Travelpayouts) y escribe ofertas.json.
Lo ejecuta GitHub Actions cada 6 horas (.github/workflows/ofertas.yml)."""
import json, os, sys, datetime, urllib.request, urllib.parse
AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(AQUI, "conector-web")
MARKER = "809229"
SITIO = "85f3691a-23eb-4f62-9d45-1b712afb16aa"

# Ciudades de salida (las mismas del botón 🌐 de la página)
ORIGENES = {
    "BUE": "Buenos Aires", "COR": "Córdoba", "ROS": "Rosario", "MDZ": "Mendoza",
    "SAO": "São Paulo", "RIO": "Río de Janeiro", "SCL": "Santiago", "MVD": "Montevideo",
    "ASU": "Asunción", "LIM": "Lima", "BOG": "Bogotá", "MEX": "Ciudad de México",
    "MIA": "Miami", "NYC": "Nueva York", "MAD": "Madrid", "LON": "Londres",
}


def log(*a):
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), *a, flush=True)


def claves():
    c = {}
    with open(os.path.join(AQUI, "claves.txt")) as f:
        for linea in f:
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.strip().split("=", 1)
                c[k.strip()] = v.strip()
    return c


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "conector-ofertas"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def destinos_de_la_pagina():
    """Códigos de vuelo de los destinos que tienen foto y guía en la página."""
    html = open(os.path.join(AQUI, "index.html"), encoding="utf-8").read()
    import re
    m = re.search(r"const VUELO = (\{.*?\});", html)
    vuelo = json.loads(re.sub(r"([A-Z]{3}):", r'"\1":', m.group(1))) if m else {}
    return set(vuelo.values()) | set(vuelo.keys())


def nombres_ciudades():
    try:
        datos = get_json("https://api.travelpayouts.com/data/es/cities.json")
        return {c["code"]: ((c.get("name") or c.get("name_translations", {}).get("en") or c["code"]), c.get("country_code", "")) for c in datos}
    except Exception as e:
        log("sin nombres de ciudades:", e)
        return {}


def buscar(origen, token):
    q = urllib.parse.urlencode({
        "origin": origen, "currency": "usd", "one_way": "false", "unique": "true",
        "sorting": "price", "limit": 60, "page": 1, "market": "ar",
    })
    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + q
    return get_json(url, {"X-Access-Token": token, "User-Agent": "conector-ofertas"}).get("data", [])


def tasas():
    """Valor del dólar en cada moneda (se actualiza una vez por día en la fuente)."""
    try:
        r = get_json("https://open.er-api.com/v6/latest/USD")["rates"]
        return {k: r[k] for k in ["ARS", "BRL", "MXN", "CLP", "COP", "PEN", "UYU", "PYG", "BOB", "EUR", "GBP", "CAD"] if k in r}
    except Exception as e:
        log("sin tasas de cambio:", e)
        return {}


def armar(token):
    conocidos = destinos_de_la_pagina()
    ciudades = nombres_ciudades()
    salida = {"actualizado": datetime.datetime.now(datetime.timezone.utc).isoformat(), "moneda": "USD", "tasas": tasas(), "origenes": {}}
    hoy = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    for cod, nombre in ORIGENES.items():
        try:
            filas = buscar(cod, token)
        except Exception as e:
            log("error buscando", cod, e)
            continue
        ofertas = []
        for f in filas:
            d = f.get("destination")
            if not d or d == cod or not f.get("price") or (f.get("departure_at") or "")[:10] < hoy:
                continue
            link = "https://www.aviasales.com" + f.get("link", "")
            link += ("&" if "?" in link else "?") + "marker=" + MARKER
            ofertas.append({
                "d": d, "ciudad": ciudades.get(d, (d, ""))[0], "precio": int(round(f["price"])),
                "ida": f.get("departure_at", "")[:10], "vuelta": (f.get("return_at") or "")[:10],
                "escalas": f.get("transfers", 0), "aerolinea": f.get("airline", ""),
                "link": link, "conocido": d in conocidos,
                "afuera": ciudades.get(d, ("", "?"))[1] != ciudades.get(cod, ("", "!"))[1],
            })
        # mezcla: hasta 10 viajes al exterior y 6 dentro del país; primero los que tienen foto
        orden = lambda o: (not o["conocido"], o["precio"])
        afuera = sorted([o for o in ofertas if o["afuera"]], key=orden)[:10]
        adentro = sorted([o for o in ofertas if not o["afuera"]], key=orden)[:16 - len(afuera)]
        ofertas = sorted(afuera + adentro, key=lambda o: o["precio"])
        for o in ofertas:
            o.pop("conocido", None); o.pop("afuera", None)
        if ofertas:
            salida["origenes"][cod] = {"nombre": nombre, "ofertas": ofertas}
        log(cod, len(ofertas), "ofertas")
    return salida




if __name__ == "__main__":
    datos = armar(os.environ["TRAVELPAYOUTS_TOKEN"])
    if not datos["origenes"]:
        log("no llegaron ofertas; se deja el archivo anterior")
        sys.exit(0)
    with open(os.path.join(AQUI, "ofertas.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
    log("ofertas.json actualizado")
