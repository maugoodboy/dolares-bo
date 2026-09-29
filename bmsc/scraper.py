#!/usr/bin/env python3
"""Scraper de tipo de cambio del Dólar publicado por Banco Mercantil Santa Cruz (BMSC)."""

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
URL_BMSC = "https://www.bmsc.com.bo/"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_bmsc(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_BMSC, headers=headers, timeout=20)
    response.raise_for_status()

    # 1. Forzar decodificación en UTF-8 para evitar errores con tildes (Dólar vs DÃ³lar)
    contenido_html = response.content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(contenido_html, "html.parser")

    valor_compra = None
    valor_venta = None

    # 2. Estrategia principal: Buscar el bloque o tarjeta HTML que contenga "dólar" / "dolar"
    for etiqueta in soup.find_all(["div", "li", "span", "p", "tr"]):
        texto_etiqueta = etiqueta.get_text(" ", strip=True).lower()
        if ("dólar" in texto_etiqueta or "dolar" in texto_etiqueta) and "cmv" not in texto_etiqueta:
            m_compra = re.search(r"compra\s*:?\s*(\d+[.,]\d+)", texto_etiqueta)
            m_venta = re.search(r"venta\s*:?\s*(\d+[.,]\d+)", texto_etiqueta)
            if m_compra and m_venta:
                valor_compra = normalizar_decimal(m_compra.group(1))
                valor_venta = normalizar_decimal(m_venta.group(1))
                break

    # 3. Estrategia de respaldo: Búsqueda flexible en todo el texto plano
    if valor_compra is None or valor_venta is None:
        texto_completo = soup.get_text(" ", strip=True)
        patron = re.search(
            r"d[oó\w]{0,3}lar[\s\S]{1,150}?compra\s*:?\s*(\d+[.,]\d+)[\s\S]{1,150}?venta\s*:?\s*(\d+[.,]\d+)",
            texto_completo,
            re.IGNORECASE,
        )
        if patron:
            valor_compra = normalizar_decimal(patron.group(1))
            valor_venta = normalizar_decimal(patron.group(2))

    # Si todo falla, comprobación de seguridad
    if valor_compra is None or valor_venta is None:
        raise ValueError("No se pudo localizar el bloque del 'Dólar' en el sitio de BMSC.")

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
        fecha, compra, venta = consultar_bmsc(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"BMSC actualizado con éxito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
