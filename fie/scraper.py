#!/usr/bin/env python3
"""Scraper de tipo de cambio de Banco Fortaleza con registro de fecha y hora exacta."""

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

URL_BASE = "https://www.bancofortaleza.com.bo/"
URL_PROXY = "https://www.bancofortaleza.com.bo/proxy-exchange.php"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_fortaleza(session):
    """Consulta las cotizaciones de Banco Fortaleza usando su endpoint directo o HTML."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": URL_BASE,
    }

    compra, venta = None, None

    # Método 1: Endpoint JSON interno (la forma más confiable que usa la web)
    try:
        res_json = session.get(URL_PROXY, headers=headers, timeout=25)
        if res_json.status_code == 200:
            datos = res_json.json().get("response", {})
            if "buyExchange" in datos and "saleExchange" in datos:
                compra = float(datos["buyExchange"])
                venta = float(datos["saleExchange"])
    except Exception as e:
        print(f"[DEBUG] Falló intento de JSON proxy: {e}")

    # Método 2: Respaldo HTML con selectores de etiquetas
    if compra is None or venta is None:
        res_html = session.get(URL_BASE, headers=headers, timeout=25)
        res_html.raise_for_status()
        soup = BeautifulSoup(res_html.text, "html.parser")

        el_compra = soup.select_one('span[data-exchange="buyExchange"]')
        el_venta = soup.select_one('span[data-exchange="saleExchange"]')

        texto_compra = el_compra.get_text(strip=True) if el_compra else ""
        texto_venta = el_venta.get_text(strip=True) if el_venta else ""

        if re.search(r"\d", texto_compra) and re.search(r"\d", texto_venta):
            compra = normalizar_decimal(texto_compra)
            venta = normalizar_decimal(texto_venta)

    # Si ambos métodos fallan
    if compra is None or venta is None:
        raise ValueError("No se encontraron los valores de compra/venta en Banco Fortaleza.")

    # Registro con fecha y hora exacta
    hora_consulta = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return hora_consulta, compra, venta


def consolidar(fn, timestamp, valor):
    """Guarda o actualiza el archivo CSV sin duplicar registros."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": timestamp, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        hora_consulta, compra, venta = consultar_fortaleza(session)

    consolidar(COMPRA_FN, hora_consulta, compra)
    consolidar(VENTA_FN, hora_consulta, venta)
    print(
        f"Banco Fortaleza actualizado con exito para {hora_consulta}: Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
