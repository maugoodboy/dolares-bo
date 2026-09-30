#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco FIE."""

import re
import unicodedata
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
URL_FIE = "https://www.bancofie.com.bo/"


def quitar_tildes(texto):
    """Elimina tildes y normaliza caracteres especiales a texto plano."""
    texto_norm = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto_norm if not unicodedata.combining(c))


def normalizar_decimal(texto):
    """Convierte texto como '11,52' a número decimal float (11.52)."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def extraer_valores(texto):
    """Extrae compra y venta de forma robusta e insensible a tildes o mayúsculas."""
    texto_plano = quitar_tildes(texto).lower()

    # Busca: 'compra' seguido opcionalmente de ':', espacios y el número decimal
    compra_match = re.search(r"compra\s*[:\-]?\s*(\d+[.,]\d+)", texto_plano)
    
    # Busca: 'venta' seguido opcionalmente de ':', espacios y el número decimal
    venta_match = re.search(r"venta\s*[:\-]?\s*(\d+[.,]\d+)", texto_plano)

    val_compra = normalizar_decimal(compra_match.group(1)) if compra_match else None
    val_venta = normalizar_decimal(venta_match.group(1)) if venta_match else None

    return val_compra, val_venta


def consultar_fie(session):
    """Descarga la página web y obtiene las cotizaciones de Banco FIE."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    response = session.get(URL_FIE, headers=headers, timeout=30)
    response.raise_for_status()

    # Ajuste automático de codificación para evitar caracteres rotos
    response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    # Unir todo el texto visible normalizando saltos y espacios
    texto_limpio = " ".join(soup.get_text().split())

    valor_compra, valor_venta = extraer_valores(texto_limpio)

    if valor_compra is None or valor_venta is None:
        raise ValueError("No se pudieron encontrar las cotizaciones de compra o venta en la página de Banco FIE.")

    fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    return fecha_hoy, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    """Guarda o actualiza el archivo CSV sin duplicar fechas."""
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
