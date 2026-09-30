#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Económico (Baneco)."""

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
URL_BANECO = "https://www.baneco.com.bo/"


def normalizar_decimal(texto):
    """Extrae el número y lo convierte a formato decimal con punto."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_baneco(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }

    response = session.get(URL_BANECO, headers=headers, timeout=25)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Buscamos primero en el footer (pie de página)
    footer_element = soup.find("footer") or soup.find(class_=re.compile(r"footer", re.IGNORECASE))
    
    if footer_element:
        texto_busqueda = " ".join(footer_element.stripped_strings)
    else:
        texto_busqueda = " ".join(soup.stripped_strings)

    # 2. Buscamos el texto exacto del Banco Económico en el footer
    patron = re.search(
        r"Banco\s+Econ[oó]mico\s+por\s+D[oó]lar.*?Compra\s*:\s*(\d+[.,]\d+)\s*[-–—]\s*Venta\s*:\s*(\d+[.,]\d+)",
        texto_busqueda,
        re.IGNORECASE | re.DOTALL,
    )

    # 3. Si no encuentra con el título largo, busca directo cualquier 'Compra: X - Venta: Y'
    if not patron:
        patron = re.search(
            r"Compra\s*:\s*(\d+[.,]\d+)\s*[-–—]\s*Venta\s*:\s*(\d+[.,]\d+)",
            texto_busqueda,
            re.IGNORECASE,
        )

    if not patron:
        raise RuntimeError("No se encontró el bloque de cotizaciones dentro del footer.")

    valor_compra = normalizar_decimal(patron.group(1))
    valor_venta = normalizar_decimal(patron.group(2))

    fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    return fecha_hoy, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha, compra, venta = consultar_baneco(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(
        f"Banco Economico actualizado con exito para {fecha}: "
        f"Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
