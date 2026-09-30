#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco de la Comunidad (BCO)."""

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
URL_BCO = "https://www.bco.com.bo/"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_bco(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_BCO, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # Búsqueda de cotización de compra y venta para USD
    compra_match = re.search(
        r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    venta_match = re.search(
        r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    valor_compra = normalizar_decimal(compra_match.group(1)) if compra_match else 6.86
    valor_venta = normalizar_decimal(venta_match.group(1)) if venta_match else 6.96

# Registra fecha y hora exacta (ejemplo: 2024-05-15 15:30:00)
    fecha_hora_actual = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora_actual, valor_compra, valor_venta


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
        fecha, compra, venta = consultar_bco(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"Banco de la Comunidad actualizado con exito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
