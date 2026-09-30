#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Fortaleza."""

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
URL_FORTALEZA = "https://www.bancofortaleza.com.bo/"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato flotante."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def limpiar_texto(texto):
    """Elimina tildes y unifica espacios."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return " ".join(plano.split()).lower()


def extraer_datos(texto_o_html):
    """Busca compra y venta en el contenido."""
    t = limpiar_texto(texto_o_html)
    
    # 1. Intento por palabras clave 'compra' y 'venta'
    compra_m = re.search(r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)", t)
    venta_m = re.search(r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)", t)

    # 2. Intento por formato de barra de divisas: 'dolar ... compra ... venta'
    if not compra_m or not venta_m:
        patron_bloque = re.search(
            r"dolar.*?compra\s*(\d+[.,]\d+).*?venta\s*(\d+[.,]\d+)",
            t,
        )
        if patron_bloque:
            return normalizar_decimal(patron_bloque.group(1)), normalizar_decimal(patron_bloque.group(2))

    c = normalizar_decimal(compra_m.group(1)) if compra_m else None
    v = normalizar_decimal(venta_m.group(1)) if venta_m else None
    return c, v


def consultar_fortaleza():
    """Descarga la página emulando navegación interactiva para obtener las cotizaciones."""
    session = requests.Session()
    
    # Cabeceras completas de navegador para evitar contenido recortado
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    response = session.get(URL_FORTALEZA, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    compra, venta = extraer_datos(soup.get_text())

    # Si no lo halla en el texto visible, busca en el código HTML y scripts
    if compra is None or venta is None:
        compra, venta = extraer_datos(response.text)

    if compra is None or venta is None:
        raise ValueError(
            "No se pudieron encontrar las cifras de compra o venta en la respuesta del Banco Fortaleza."
        )

    # Fecha y hora exacta en Bolivia
    fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora, compra, venta


def consolidar(fn, fecha_hora, valor):
    """Guarda o actualiza el registro en el archivo CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    fecha_hora, compra, venta = consultar_fortaleza()

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(
        f"Banco Fortaleza actualizado con exito para {fecha_hora}: "
        f"Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
