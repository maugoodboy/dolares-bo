#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Económico (Baneco)."""

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
URL_BANECO = "https://www.baneco.com.bo/"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_baneco(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }

    response = session.get(URL_BANECO, headers=headers, timeout=25)
    response.raise_for_status()

    # Limpiamos el texto completo de la página unificando espacios
    soup = BeautifulSoup(response.text, "html.parser")
    texto = " ".join(soup.stripped_strings)

    # 1. Búsqueda principal: texto entre "Banco Económico por Dólar" hasta "Unidad de Fomento" o "Compra... Venta..."
    patron_especifico = re.search(
        r"Banco\s+Econ[oó]mico\s+por\s+D[oó]lar.*?Compra\s*:\s*(\d+[.,]\d+).*?Venta\s*:\s*(\d+[.,]\d+)",
        texto,
        re.IGNORECASE | re.DOTALL,
    )

    if patron_especifico:
        valor_compra = normalizar_decimal(patron_especifico.group(1))
        valor_venta = normalizar_decimal(patron_especifico.group(2))
    else:
        # 2. Búsqueda secundaria flexible: busca cualquier 'Compra: XX - Venta: YY'
        patron_bloque = re.search(
            r"Compra\s*:\s*(\d+[.,]\d+)\s*[-–—]\s*Venta\s*:\s*(\d+[.,]\d+)",
            texto,
            re.IGNORECASE,
        )
        if patron_bloque:
            valor_compra = normalizar_decimal(patron_bloque.group(1))
            valor_venta = normalizar_decimal(patron_bloque.group(2))
        else:
            raise RuntimeError(
                f"No se encontraron las cotizaciones en el texto procesado. Inicio del texto: {texto[:300]}"
            )

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
        fecha, compra, venta = consultar_baneco(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(
        f"Banco Economico actualizado con exito para {fecha}: "
        f"Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
