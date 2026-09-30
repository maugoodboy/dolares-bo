#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Fortaleza."""

import json
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
    """Extrae el valor numérico y lo convierte a formato flotante."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def limpiar_texto(texto):
    """Quita tildes, caracteres especiales y normaliza espacios."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize("NFKD", texto)
    texto_plano = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return " ".join(texto_plano.split()).lower()


def extraer_desde_scripts(html_text):
    """Busca variables de cotización dentro de etiquetas <script> o JSON embebido."""
    # Busca patrones tipo: "compra": 11.72 o "compra": "11.72"
    patron_compra = re.search(r'["\']?compra["\']?\s*[:=]\s*["\']?(\d+[.,]\d+)["\']?', html_text, re.IGNORECASE)
    patron_venta = re.search(r'["\']?venta["\']?\s*[:=]\s*["\']?(\d+[.,]\d+)["\']?', html_text, re.IGNORECASE)

    if patron_compra and patron_venta:
        return normalizar_decimal(patron_compra.group(1)), normalizar_decimal(patron_venta.group(1))
    return None, None


def consultar_fortaleza(session):
    """Descarga la página web y extrae fecha/hora, compra y venta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
    }

    response = session.get(URL_FORTALEZA, headers=headers, timeout=25)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    html_raw = response.text
    valor_compra, valor_venta = extraer_desde_scripts(html_raw)

    # Si no estaba en los scripts, buscar en el contenido procesado por BeautifulSoup
    if valor_compra is None or valor_venta is None:
        soup = BeautifulSoup(html_raw, "html.parser")
        texto_limpio = limpiar_texto(soup.get_text())

        compra_match = re.search(r"compra\s*[:\-]?\s*(\d+[.,]\d+)", texto_limpio)
        venta_match = re.search(r"venta\s*[:\-]?\s*(\d+[.,]\d+)", texto_limpio)

        if compra_match and venta_match:
            valor_compra = normalizar_decimal(compra_match.group(1))
            valor_venta = normalizar_decimal(venta_match.group(1))

    if valor_compra is None or valor_venta is None:
        raise ValueError(
            "No se pudieron encontrar las cifras de compra o venta en la respuesta del Banco Fortaleza."
        )

    # Timestamp con fecha y hora completa en zona horaria La Paz
    ahora = datetime.now(ZoneInfo(TIMEZONE))
    fecha_hora = ahora.strftime("%Y-%m-%d %H:%M:%S")

    return fecha_hora, valor_compra, valor_venta


def consolidar(fn, fecha_hora, valor):
    """Guarda o actualiza el registro en el archivo CSV correspondiente."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    # Se mantiene la última consulta sin duplicar si coincide exactamente el minuto/segundo
    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha_hora, compra, venta = consultar_fortaleza(session)

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(f"Banco Fortaleza actualizado con éxito para {fecha_hora}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
