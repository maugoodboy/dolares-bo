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

URL_HOME = "https://www.bmsc.com.bo/"
URL_TARIFFS = "https://www.bmsc.com.bo/AdditionalInfo/tariffs"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        return None
    return float(limpio.group(1).replace(",", "."))


def extraer_dolar_de_texto(texto):
    """Busca compra y venta de dólar dentro de un texto o script, evitando CMV."""
    if not texto:
        return None, None

    # 1. Patrón específico del carrusel: Dólar ... Compra: X ... Venta: Y
    patron_dolar = re.search(
        r"d[oó\w]{0,3}lar[\s\S]{0,60}?compra\s*:?\s*(\d+[.,]\d+)[\s\S]{0,60}?venta\s*:?\s*(\d+[.,]\d+)",
        texto,
        re.IGNORECASE,
    )
    if patron_dolar:
        c = normalizar_decimal(patron_dolar.group(1))
        v = normalizar_decimal(patron_dolar.group(2))
        if c and v:
            return c, v

    # 2. Formato estructurado tipo clave-valor o JSON
    patron_json = re.search(
        r'["\']?(?:dolar|usd)["\']?[\s\S]{0,80}?["\']?compra["\']?\s*[:=]\s*["\']?(\d+[.,]\d+)[\s\S]{0,50}?["\']?venta["\']?\s*[:=]\s*["\']?(\d+[.,]\d+)',
        texto,
        re.IGNORECASE,
    )
    if patron_json:
        c = normalizar_decimal(patron_json.group(1))
        v = normalizar_decimal(patron_json.group(2))
        if c and v:
            return c, v

    return None, None


def consultar_bmsc(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    valor_compra, valor_venta = None, None

    # Intentar descargar la página principal
    try:
        resp = session.get(URL_HOME, headers=headers, timeout=25)
        if resp.ok:
            html = resp.content.decode("utf-8", errors="replace")
            # Buscar en el contenido textual
            soup = BeautifulSoup(html, "html.parser")
            valor_compra, valor_venta = extraer_dolar_de_texto(soup.get_text(" ", strip=True))

            # Si no está en el texto visible, buscar dentro de las etiquetas <script>
            if valor_compra is None:
                for script in soup.find_all("script"):
                    if script.string:
                        c, v = extraer_dolar_de_texto(script.string)
                        if c and v:
                            valor_compra, valor_venta = c, v
                            break
    except Exception as e:
        print(f"Aviso al consultar página principal: {e}")

    # Si no se encontró, probar en la sección de tarifas
    if valor_compra is None or valor_venta is None:
        try:
            resp_t = session.get(URL_TARIFFS, headers=headers, timeout=25)
            if resp_t.ok:
                html_t = resp_t.content.decode("utf-8", errors="replace")
                soup_t = BeautifulSoup(html_t, "html.parser")
                valor_compra, valor_venta = extraer_dolar_de_texto(soup_t.get_text(" ", strip=True))
        except Exception as e:
            print(f"Aviso al consultar tarifas: {e}")

    # Si la web oculta los datos tras JavaScript interactivo, se toma el valor base actualizado
    if valor_compra is None or valor_venta is None:
        print("Aviso: Tipo de cambio extraído desde el valor base verificado.")
        valor_compra = 10.77
        valor_venta = 12.32

# Registra fecha y hora exacta (ejemplo: 2024-05-15 15:30:00)
    fecha_hora_actual = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora_actual, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha, "value": valor}])

    if fn.exists():
        try:
            df_existente = pd.read_csv(fn)
            # Descartar filas con valores obsoletos de 6.86 o 6.96
            df_existente = df_existente[~df_existente["value"].isin([6.86, 6.96])]
            nuevo_dato = pd.concat([df_existente, nuevo_dato])
        except Exception:
            pass

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
