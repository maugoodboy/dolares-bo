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


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_fortaleza(session):
    """Descarga la página de Banco Fortaleza y extrae compra y venta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }
    
    # Realizar petición web
    response = session.get(URL_FORTALEZA, headers=headers, timeout=25)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # 1. Intentar patrón flexible para 'Compra'
    compra_match = re.search(
        r"compra\s*[:\-]?\s*(?:bs\.?|bob|\$)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    # 2. Intentar patrón flexible para 'Venta'
    venta_match = re.search(
        r"venta\s*[:\-]?\s*(?:bs\.?|bob|\$)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    # 3. Plan de respaldo si están en orden inverso o separados
    if not compra_match:
        compra_match = re.search(
            r"(\d+[.,]\d+)\s*(?:bs\.?|bob)?\s*compra",
            texto_completo,
            re.IGNORECASE,
        )

    if not venta_match:
        venta_match = re.search(
            r"(\d+[.,]\d+)\s*(?:bs\.?|bob)?\s*venta",
            texto_completo,
            re.IGNORECASE,
        )

    if not compra_match or not venta_match:
        raise ValueError("No se encontraron los valores de compra/venta en la página.")

    valor_compra = normalizar_decimal(compra_match.group(1))
    valor_venta = normalizar_decimal(venta_match.group(1))

    fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    return fecha_hoy, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    """Guarda o actualiza el registro en el archivo CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha, compra, venta = consultar_fortaleza(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"Banco Fortaleza actualizado con exito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
