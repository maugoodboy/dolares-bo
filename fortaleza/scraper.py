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
    """Extrae el valor numérico y lo convierte a formato decimal estándar."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_fortaleza(session):
    """Descarga la página web y extrae los valores de compra y venta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }
    
    # 1. Petición web
    response = session.get(URL_FORTALEZA, headers=headers, timeout=25)
    response.raise_for_status()

    # 2. Parseo y limpieza del texto
    soup = BeautifulSoup(response.text, "html.parser")
    # Limpiamos caracteres invisibles (\xa0) y normalizamos espacios
    texto_completo = " ".join(soup.get_text().split())

    # 3. Buscar 'COMPRA' seguido inmediatamente del número decimal
    compra_match = re.search(
        r"compra\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    
    # 4. Buscar 'VENTA' seguido inmediatamente del número decimal
    venta_match = re.search(
        r"venta\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    if not compra_match or not venta_match:
        raise ValueError(
            f"No se encontraron los valores en el texto obtenido:\n{texto_completo[:500]}"
        )

    valor_compra = normalizar_decimal(compra_match.group(1))
    valor_venta = normalizar_decimal(venta_match.group(1))

    fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    return fecha_hoy, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    """Guarda o actualiza el registro en el archivo CSV correspondiente."""
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
    print(f"Banco Fortaleza actualizado con éxito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
