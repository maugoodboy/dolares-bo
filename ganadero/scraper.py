#!/usr/bin/env python3
"""Scraper de cotización de venta publicado por Banco Ganadero."""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd
import requests

# 1. Definición de rutas y archivos
DATA_DIR = Path(__file__).resolve().parent
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_GANADERO = "https://www.bg.com.bo/personas/"


def normalizar_decimal(texto):
    """Limpia el texto y extrae el número con formato decimal (ej: '12,32' -> 12.32)."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    # Convierte coma decimal a punto para que Python lo reconozca
    return float(limpio.group(1).replace(",", "."))


def consultar_ganadero(session):
    """Descarga la página web y extrae el valor de venta."""
    # Simula un navegador para que la página permita la conexión
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_GANADERO, headers=headers, timeout=20)
    response.raise_for_status()

    # Leemos el texto de la página
    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # Buscamos la frase 'Valor Ref. Venta' seguida de 'USD' y del número (ej: 12,32)
    venta_match = re.search(
        r"Valor\s*Ref\.?\s*Venta(?:\s*USD)?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    # Búsqueda alternativa por si la página cambia levemente el texto a 'Venta'
    if not venta_match:
        venta_match = re.search(
            r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
            texto_completo,
            re.IGNORECASE,
        )

    if not venta_match:
        raise ValueError(
            "No se encontró el 'Valor Ref. Venta USD' en la página."
        )

    valor_venta = normalizar_decimal(venta_match.group(1))

    # Obtenemos la fecha de hoy con la hora de Bolivia
    fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    return fecha_hoy, valor_venta


def consolidar(fn, fecha, valor):
    """Guarda el valor en el archivo CSV sin duplicar la fecha."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha, "value": valor}])

    # Si el archivo ya existía, añadimos la nueva fila conservando los datos anteriores
    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    # Si se ejecuta varias veces el mismo día, conserva el último registro
    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha, venta = consultar_ganadero(session)

    # Guarda únicamente en venta.csv
    consolidar(VENTA_FN, fecha, venta)
    print(
        f"Banco Ganadero actualizado con éxito para {fecha}: Venta={venta}"
    )


if __name__ == "__main__":
    main()
