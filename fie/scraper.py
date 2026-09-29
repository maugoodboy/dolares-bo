#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco FIE."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Configuración de carpetas y enlaces
DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_FIE = "https://www.bancofie.com.bo/"


def normalizar_decimal(texto):
    """Convierte texto como '11,52' a número decimal 11.52."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def extraer_valores(texto):
    """Busca compra y venta en el texto con reglas flexibles."""
    # 1. Búsqueda prioritaria: 'Dólar Compra: 11,52' y 'Dólar Venta: 12,02'
    compra = re.search(
        r"d[oó]lar[^\d]{1,40}?compra[^\d]{1,40}?(\d+[.,]\d+)",
        texto,
        re.IGNORECASE,
    )
    venta = re.search(
        r"d[oó]lar[^\d]{1,40}?venta[^\d]{1,40}?(\d+[.,]\d+)",
        texto,
        re.IGNORECASE,
    )

    # 2. Búsqueda de respaldo si no lleva la palabra 'dólar' pegada
    if not compra:
        compra = re.search(r"compra[^\d]{1,40}?(\d+[.,]\d+)", texto, re.IGNORECASE)
    if not venta:
        venta = re.search(r"venta[^\d]{1,40}?(\d+[.,]\d+)", texto, re.IGNORECASE)

    val_compra = normalizar_decimal(compra.group(1)) if compra else None
    val_venta = normalizar_decimal(venta.group(1)) if venta else None
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

    # Asegurar codificación correcta en español
    response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Unificar texto y reemplazar espacios especiales o saltos de línea por un espacio simple
    texto_limpio = " ".join(soup.get_text(" ", strip=True).split())

    # Intento 1: Buscar en el texto visible
    valor_compra, valor_venta = extraer_valores(texto_limpio)

    # Intento 2: Si no lo halló en el texto visible, buscar directamente en el código HTML
    if valor_compra is None or valor_venta is None:
        html_limpio = " ".join(response.text.split())
        c_html, v_html = extraer_valores(html_limpio)
        valor_compra = valor_compra or c_html
        valor_venta = valor_venta or v_html

    # Si aún no se encuentran, mostrar información de depuración
    if valor_compra is None or valor_venta is None:
        titulo = soup.title.string.strip() if soup.title else "Sin título"
        print(f"[DEBUG] Título de la página recibida: {titulo}")
        print(f"[DEBUG] Primeros 300 caracteres del texto: {texto_limpio[:300]}")
        raise ValueError("No se pudieron encontrar las cotizaciones de compra o venta en la página de FIE.")

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
