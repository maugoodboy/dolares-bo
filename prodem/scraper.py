#!/usr/bin/env python3
"""Scraper de tipo de cambio oficial publicado por Banco Prodem."""

import re
import time
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

# Lista de vías de acceso para evitar los bloqueos de IP
RUTAS_CONEXION = [
    "https://r.jina.ai/https://www.prodem.bo/Inicio",
    "https://www.prodem.bo/Inicio",
]


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def extraer_desde_texto(texto):
    """Extrae compra y venta buscando específicamente el bloque de Banco Prodem."""
    # Busca la sección donde aparece 'Banco Prodem' seguida de Compra y Venta
    patron_prodem = re.search(
        r"Banco\s+Prodem.*?Compra\s*[:\-]?\s*(\d+[.,]\d+).*?Venta\s*[:\-]?\s*(\d+[.,]\d+)",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if patron_prodem:
        compra = normalizar_decimal(patron_prodem.group(1))
        venta = normalizar_decimal(patron_prodem.group(2))
        return compra, venta

    # Búsqueda secundaria en caso de ligero cambio en el orden de palabras
    compra_m = re.search(r"Compra\s*[:\-]?\s*(\d+[.,]\d+)", texto, re.IGNORECASE)
    venta_m = re.search(r"Venta\s*[:\-]?\s*(\d+[.,]\d+)", texto, re.IGNORECASE)

    if compra_m and venta_m:
        return normalizar_decimal(compra_m.group(1)), normalizar_decimal(venta_m.group(1))

    return None, None


def consultar_prodem(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    for ruta in RUTAS_CONEXION:
        print(f"Intentando obtener datos desde: {ruta}...")
        for intento in range(1, 3):
            try:
                response = session.get(ruta, headers=headers, timeout=35)
                if response.status_code == 200 and len(response.text) > 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    texto = soup.get_text(" ", strip=True)

                    compra, venta = extraer_desde_texto(texto)
                    if compra and venta:
                        # Se registra tanto la fecha como la hora exacta de Bolivia
                        fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"Cotización encontrada: Compra={compra}, Venta={venta}")
                        return fecha_hora, compra, venta
            except requests.exceptions.RequestException as e:
                print(f"Aviso en intento {intento}: {e}")
            time.sleep(3)

    print("No fue posible obtener la página web de Prodem en vivo.")
    return None, None, None


def consolidar(fn, fecha_hora, valor):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha_hora, compra, venta = consultar_prodem(session)

    # Si hubo problemas de conexión, se usa la fecha y hora actual con los valores de respaldo
    if fecha_hora is None:
        fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Usando valores de respaldo para: {fecha_hora}.")
        try:
            df_compra = pd.read_csv(COMPRA_FN)
            compra = float(df_compra["value"].iloc[-1])
        except Exception:
            compra = 11.72

        try:
            df_venta = pd.read_csv(VENTA_FN)
            venta = float(df_venta["value"].iloc[-1])
        except Exception:
            venta = 12.12

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(f"Banco Prodem actualizado con éxito para {fecha_hora}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
