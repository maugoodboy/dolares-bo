#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Fortaleza."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"

URL_FORTALEZA = "https://www.bancofortaleza.com.bo/"
URL_PROXY = "https://www.bancofortaleza.com.bo/proxy-exchange.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
}


def normalizar_numero(valor):
    """Extrae el número decimal de cadenas como '11.72 Bs.' o '11,72'."""
    limpio = re.search(r"(\d+[.,]\d+)", str(valor))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {valor}")
    return float(limpio.group(1).replace(",", "."))


def consultar_fortaleza(session):
    """Obtiene los valores de compra y venta mediante HTML o el proxy JSON."""
    compra = None
    venta = None

    # Método 1: Intentar leer selectores específicos en el HTML
    try:
        resp = session.get(URL_FORTALEZA, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            nodo_compra = soup.select_one('span[data-exchange="buyExchange"]')
            nodo_venta = soup.select_one('span[data-exchange="saleExchange"]')

            texto_c = nodo_compra.get_text(strip=True) if nodo_compra else ""
            texto_v = nodo_venta.get_text(strip=True) if nodo_venta else ""

            if re.search(r"\d", texto_c) and re.search(r"\d", texto_v):
                compra = normalizar_numero(texto_c)
                venta = normalizar_numero(texto_v)
    except Exception:
        pass

    # Método 2: Consultar la API proxy directa que alimenta la barra
    if compra is None or venta is None:
        headers_proxy = {
            **HEADERS,
            "Accept": "application/json, text/plain, */*",
            "Referer": URL_FORTALEZA,
        }
        resp_json = session.get(URL_PROXY, headers=headers_proxy, timeout=20)
        resp_json.raise_for_status()
        datos = resp_json.json().get("response", {})
        compra = float(datos["buyExchange"])
        venta = float(datos["saleExchange"])

    fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora, compra, venta


def consolidar(fn, fecha_hora, valor):
    """Actualiza o guarda el registro en el CSV correspondiente."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha_hora, compra, venta = consultar_fortaleza(session)

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(
        f"Banco Fortaleza actualizado con exito para {fecha_hora}: "
        f"Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
