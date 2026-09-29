#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Ganadero."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_GANADERO = "https://www.bg.com.bo/personas/"


def normalizar_decimal(texto):
    """Extrae el número y lo convierte a decimal estándar de Python."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_ganadero(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_GANADERO, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # 1. Búsqueda de Compra (T. Cambio Oficial)
    # Busca 'T. Cambio Oficial' seguido de un número decimal
    compra_match = re.search(
        r"T\.?\s*Cambio\s*Oficial\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    # Alternativa por si en el HTML dice simplemente 'compra'
    if not compra_match:
        compra_match = re.search(
            r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
            texto_completo,
            re.IGNORECASE,
        )

    # 2. Búsqueda de Venta (Valor Ref. Venta USD)
    # Busca 'Valor Ref. Venta' seguido opcionalmente de 'USD' y del número
    venta_match = re.search(
        r"Valor\s*Ref\.?\s*Venta(?:\s*USD)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    # Alternativa por si en el HTML dice directamente 'venta'
    if not venta_match:
        venta_match = re.search(
            r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
            texto_completo,
            re.IGNORECASE,
        )

    # Validamos que se hayan encontrado ambos valores en la web
    if not compra_match or not venta_match:
        raise ValueError(
            "No se pudieron encontrar las etiquetas de cotización en la página."
        )

    valor_compra = normalizar_decimal(compra_match.group(1))
    valor_venta = normalizar_decimal(venta_match.group(1))

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
        fecha, compra, venta = consultar_ganadero(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(
        f"Banco Ganadero actualizado con éxito para {fecha}: Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
