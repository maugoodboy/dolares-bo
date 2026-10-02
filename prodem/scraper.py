#!/usr/bin/env python3

import argparse
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent
TIMEZONE = ZoneInfo("America/La_Paz")
REQUEST_TIMEOUT = (10, 30)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

URL_PRODEM = "https://www.prodem.bo/Inicio"


def solicitar(url, headers=None, max_retries=3):
    request_headers = {**REQUEST_HEADERS, **(headers or {})}
    for intento in range(max_retries + 1):
        try:
            with requests.Session() as session:
                response = session.get(
                    url,
                    headers=request_headers,
                    timeout=REQUEST_TIMEOUT,
                )
            response.raise_for_status()
            return response
        except requests.RequestException:
            if intento == max_retries:
                raise
            time.sleep(2**intento)


def descargar(url):
    return BeautifulSoup(solicitar(url).text, "html.parser")


def texto(elemento):
    return " ".join(elemento.get_text(" ", strip=True).split()) if elemento else ""


def sin_acentos(valor):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", valor)
        if unicodedata.category(c) != "Mn"
    ).lower()


def numero(valor):
    valor = valor.replace("\xa0", " ").strip()
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


def banco_prodem():
    # Intento 1: Proxy reader de Jina para evitar bloqueos de red en GitHub Actions
    try:
        url_reader = f"https://r.jina.ai/{URL_PRODEM}"
        contenido = solicitar(url_reader).text
        patron = re.search(
            r"Banco\s+Prodem.*?Compra\s*[:\-]?\s*(\d+[.,]\d+).*?Venta\s*[:\-]?\s*(\d+[.,]\d+)",
            contenido,
            re.IGNORECASE | re.DOTALL,
        )
        if patron:
            return {
                "compra": numero(patron.group(1)),
                "venta": numero(patron.group(2)),
            }
    except Exception:
        pass

    # Intento 2: Conexión directa al contenedor principal de la página
    sopa = descargar(URL_PRODEM)
    contenedor = sopa.select_one(
        "#MainContent_ListView1_PostWebUserControl_0_ListView1_0_Label1_0"
    )
    texto_fuente = texto(contenedor) if contenedor else texto(sopa)

    patron = re.search(
        r"Banco\s+Prodem.*?Compra\s*[:\-]?\s*(\d+[.,]\d+).*?Venta\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_fuente,
        re.IGNORECASE | re.DOTALL,
    )
    if patron:
        return {
            "compra": numero(patron.group(1)),
            "venta": numero(patron.group(2)),
        }

    # Intento 3: Búsqueda genérica de etiquetas compra y venta
    patron_alt = re.search(
        r"Compra\s*[:\-]?\s*(\d+[.,]\d+)\s+Venta\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_fuente,
        re.IGNORECASE,
    )
    if patron_alt:
        return {
            "compra": numero(patron_alt.group(1)),
            "venta": numero(patron_alt.group(2)),
        }

    raise ValueError("No se pudo obtener la cotización de Banco Prodem")


def actualizar_archivo(tipo_cotizacion, nuevos):
    ruta = DATA_DIR / f"{tipo_cotizacion}.csv"
    columnas = ["timestamp", "banco", "valor"]
    partes = []

    if ruta.exists() and ruta.stat().st_size:
        anterior = pd.read_csv(ruta, usecols=columnas)
        partes.append(anterior)

    actuales = nuevos.loc[nuevos["tipo_cotizacion"] == tipo_cotizacion, columnas]
    partes.append(actuales)
    datos = pd.concat(partes, ignore_index=True)
    datos["timestamp"] = datos["timestamp"].astype(str).str[:10]
    datos = (
        datos.drop_duplicates(subset=["timestamp", "banco"], keep="last")
        .sort_values(["timestamp", "banco"])
    )
    datos.to_csv(ruta, columns=columnas, index=False)


def main(dry_run=False):
    timestamp = datetime.now(TIMEZONE).date().isoformat()
    registros = []

    try:
        cotizaciones = banco_prodem()
        for tipo_cotizacion in ("compra", "venta"):
            registros.append(
                {
                    "tipo_cotizacion": tipo_cotizacion,
                    "timestamp": timestamp,
                    "banco": "banco_prodem",
                    "valor": cotizaciones[tipo_cotizacion],
                }
            )
        print(f"banco_prodem: {cotizaciones}")
    except Exception as error:
        mensaje = f"{type(error).__name__}: {error}".replace("\n", " ")
        print(f"::error title=Error en cotización::banco_prodem: {mensaje}")
        return 1

    nuevos = pd.DataFrame(
        registros,
        columns=["tipo_cotizacion", "timestamp", "banco", "valor"],
    )
    if not dry_run and not nuevos.empty:
        for tipo_cotizacion in ("compra", "venta"):
            actualizar_archivo(tipo_cotizacion, nuevos)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="consultar banco sin modificar los archivos CSV",
    )
    sys.exit(main(dry_run=parser.parse_args().dry_run))
