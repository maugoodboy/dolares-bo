#!/usr/bin/env python3
"""Scraper de tipo de cambio de Banco FIE con fecha y hora exacta de consulta."""

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

# URLs de consulta: página principal y página directa de tasas
URLS_FIE = [
    "https://www.bancofie.com.bo/",
    "https://www.bancofie.com.bo/tasas-y-cotizaciones",
]


def quitar_tildes(texto):
    """Elimina tildes y acentos para facilitar la búsqueda."""
    texto_norm = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto_norm if not unicodedata.combining(c))


def normalizar_decimal(texto):
    """Convierte texto como '11,52' a número decimal float (11.52)."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def extraer_de_texto(texto):
    """Busca compra y venta con patrones flexibles."""
    texto_plano = quitar_tildes(texto).lower()

    # Patrón 1: 'dolar compra: 11,52' y 'dolar venta: 12,02'
    match_compra = re.search(r"dolar\s*compra\s*[:\-]?\s*(\d+[.,]\d+)", texto_plano)
    match_venta = re.search(r"dolar\s*venta\s*[:\-]?\s*(\d+[.,]\d+)", texto_plano)

    # Patrón 2: 'compra: 11,52' y 'venta: 12,02'
    if not match_compra:
        match_compra = re.search(
            r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)", texto_plano
        )
    if not match_venta:
        match_venta = re.search(
            r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)", texto_plano
        )

    # Patrón 3: Captura directa desde la franja 'TIPOS DE CAMBIO'
    if not match_compra or not match_venta:
        bloque = re.search(
            r"tipos?\s+de\s+cambio.*?dolar[^\d]+(\d+[.,]\d+)[^\d]+(\d+[.,]\d+)",
            texto_plano,
        )
        if bloque:
            val_compra = normalizar_decimal(bloque.group(1))
            val_venta = normalizar_decimal(bloque.group(2))
            return val_compra, val_venta

    val_compra = normalizar_decimal(match_compra.group(1)) if match_compra else None
    val_venta = normalizar_decimal(match_venta.group(1)) if match_venta else None
    return val_compra, val_venta


def consultar_fie(session):
    """Prueba las fuentes disponibles y extrae compra, venta y hora de consulta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }

    compra, venta = None, None

    for url in URLS_FIE:
        try:
            response = session.get(url, headers=headers, timeout=25)
            if response.status_code != 200:
                continue

            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            texto_limpio = " ".join(soup.get_text(" ", strip=True).split())
            compra, venta = extraer_de_texto(texto_limpio)

            if compra is not None and venta is not None:
                break

            # Búsqueda en el HTML crudo si no estuvo en el texto
            compra_html, venta_html = extraer_de_texto(response.text)
            if compra_html and venta_html:
                compra, venta = compra_html, venta_html
                break
        except Exception:
            continue

    if compra is None or venta is None:
        raise ValueError(
            "No se pudieron encontrar las cotizaciones de compra o venta en Banco FIE."
        )

    # Recupera fecha y hora de la consulta (ejemplo: 2026-09-30 11:30:00)
    hora_consulta = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return hora_consulta, compra, venta


def consolidar(fn, timestamp, valor):
    """Guarda el valor en el CSV con su fecha y hora exacta."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": timestamp, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        hora_consulta, compra, venta = consultar_fie(session)

    consolidar(COMPRA_FN, hora_consulta, compra)
    consolidar(VENTA_FN, hora_consulta, venta)
    print(
        f"Banco FIE actualizado con exito para {hora_consulta}: Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
