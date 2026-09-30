#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco FIE con registro de hora exacta."""

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


def extraer_de_texto(texto):
    """Busca los valores específicamente con el prefijo dolar."""
    texto_plano = quitar_tildes(texto).lower()

    # Prioridad 1: Buscar 'dolar compra: XX,XX' y 'dolar venta: XX,XX'
    match_compra = re.search(
        r"dolar\s*compra\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_plano,
    )
    match_venta = re.search(
        r"dolar\s*venta\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_plano,
    )

    # Prioridad 2: Buscar en frases como 'compra: 11,52'
    if not match_compra:
        match_compra = re.search(
            r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
            texto_plano,
        )
    if not match_venta:
        match_venta = re.search(
            r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
            texto_plano,
        )

    val_compra = normalizar_decimal(match_compra.group(1)) if match_compra else None
    val_venta = normalizar_decimal(match_venta.group(1)) if match_venta else None
    return val_compra, val_venta


def consultar_fie(session):
    """Descarga la página web y obtiene las cotizaciones de Banco FIE con fecha y hora."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    response = session.get(URL_FIE, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    # Extraer texto eliminando elementos que distorsionan la lectura
    for elemento in soup(["script", "style", "noscript"]):
        elemento.decompose()

    texto_limpio = " ".join(soup.get_text(" ", strip=True).split())

    # Intento 1: Buscar en el texto renderizado
    compra, venta = extraer_de_texto(texto_limpio)

    # Intento 2: Buscar en el código fuente HTML original
    if compra is None or venta is None:
        compra_html, venta_html = extraer_de_texto(response.text)
        compra = compra or compra_html
        venta = venta or venta_html

    if compra is None or venta is None:
        print("[DEBUG] No se encontró el patrón de compra/venta.")
        print(f"[DEBUG] Longitud de texto descargado: {len(texto_limpio)}")
        print(f"[DEBUG] Muestra del texto (primeros 500 caracteres): {texto_limpio[:500]}")
        raise ValueError(
            "No se pudieron encontrar las cotizaciones de compra o venta en la página de Banco FIE."
        )

    # Registro de fecha Y hora exacta (Ejemplo: 2026-09-30 11:08:52)
    timestamp_ahora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return timestamp_ahora, compra, venta


def consolidar(fn, fecha_hora, valor):
    """Guarda o actualiza el archivo CSV con fecha y hora sin duplicados."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha_hora, compra, venta = consultar_fie(session)

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(f"Banco FIE actualizado con exito para {fecha_hora}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
