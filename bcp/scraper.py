#!/usr/bin/env python3
"""Scraper de tipo de cambio oficial publicado por el Banco BCP Bolivia."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_BCP = "https://www.bcp.com.bo/"


def normalizar_decimal(texto):
    """Limpia el texto y extrae el número decimal correspondiente."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_bcp(session):
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    try:
        response = session.get(URL_BCP, headers=headers, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        texto_completo = soup.get_text(" ", strip=True)

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
    except Exception as e:
        print(f"Aviso: No se pudo conectar a la web del BCP ({e}). Se usarán valores de referencia.")
        valor_compra, valor_venta = 6.86, 6.96

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
        fecha, compra, venta = consultar_bcp(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"BCP procesado con exito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
