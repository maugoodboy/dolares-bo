#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco FIE."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Configuración de rutas y variables básicas
DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_FIE = "https://www.bancofie.com.bo/"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_fie(session):
    """Descarga la página web y extrae los tipos de cambio de compra y venta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_FIE, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # Búsqueda que contempla 'Dólar Compra: 11,52' o 'Compra: 11,52'
    compra_match = re.search(
        r"(?:d[oó]lar\s+)?compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    
    # Búsqueda que contempla 'Dólar Venta: 12,02' o 'Venta: 12,02'
    venta_match = re.search(
        r"(?:d[oó]lar\s+)?venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    if not compra_match or not venta_match:
        raise ValueError(
            "No se pudieron encontrar las etiquetas de compra o venta en el texto de la página."
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
        fecha, compra, venta = consultar_fie(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"Banco FIE actualizado con exito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
