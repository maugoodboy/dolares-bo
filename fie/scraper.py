#!/usr/bin/env python3
"""Scraper de tipo de cambio de Banco FIE con fecha y hora exacta de consulta."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"

URL_BASE = "https://www.bancofie.com.bo/"
URL_API = "https://www.bancofie.com.bo/api/tcl"


def sin_acentos(texto):
    """Elimina tildes y normaliza a minúsculas."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    ).lower()


def numero(valor):
    """Extrae un número decimal limpio de una cadena de texto."""
    valor = str(valor).replace("\xa0", " ").strip()
    encontrados = re.findall(
        r"(?<!\d)\d{1,3}(?:[.,]\d{3})*[.,]\d{1,5}(?!\d)", valor
    )
    if not encontrados:
        encontrados = re.findall(r"(?<!\d)\d+(?:[.,]\d+)?(?!\d)", valor)
    if not encontrados:
        raise ValueError(f"No se encontró un número en: {valor!r}")

    token = encontrados[-1]
    if "," in token and "." in token:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        miles = "." if decimal == "," else ","
        token = token.replace(miles, "").replace(decimal, ".")
    elif "," in token:
        token = token.replace(",", ".")
    return float(token)


def valor_etiquetado(texto_fuente, etiqueta):
    """Busca una etiqueta y extrae el número que le sigue."""
    patron = rf"{etiqueta}\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"
    encontrado = re.search(patron, texto_fuente, flags=re.IGNORECASE)
    if not encontrado:
        raise ValueError(f"No se encontró {etiqueta!r} en el documento recibido")
    return numero(encontrado.group(1))


def consultar_fie(session):
    """Consulta la API oficial de Banco FIE y extrae compra, venta y hora exacta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": URL_BASE,
        "Origin": "https://www.bancofie.com.bo",
    }

    # Llamada directa al endpoint JSON de Banco FIE
    response = session.post(URL_API, json={}, headers=headers, timeout=25)
    response.raise_for_status()

    datos = response.json()
    documento = datos.get("resultado", {}).get("documento", "")

    if not documento:
        raise ValueError("La API de Banco FIE no devolvió el documento de cotización.")

    doc_plano = sin_acentos(documento)

    # Extracción de valores
    val_compra = valor_etiquetado(doc_plano, r"dolar\s+compra")
    val_venta = valor_etiquetado(doc_plano, r"dolar\s+venta")

    # Registro de la fecha y hora exacta de consulta (Ejemplo: 2026-10-01 09:15:00)
    hora_consulta = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    return hora_consulta, val_compra, val_venta


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
        hora_consulta, compra, venta = consultar_fie(session)

    consolidar(COMPRA_FN, hora_consulta, compra)
    consolidar(VENTA_FN, hora_consulta, venta)
    print(
        f"Banco FIE actualizado con exito para {hora_consulta}: Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
