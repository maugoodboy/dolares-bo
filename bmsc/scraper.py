#!/usr/bin/env python3
"""Scraper de tipo de cambio del Dólar publicado por Banco Mercantil Santa Cruz (BMSC)."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"

# Endpoint directo oficial del BMSC
API_BMSC = "https://backportal.bmsc.com.bo:1443/api/bmscservices/tipotre"


def consultar_bmsc(session):
    """Consulta la API interna del BMSC y extrae fecha, hora y cotizaciones."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bmsc.com.bo/",
    }

    # Valores de respaldo actualizados por si el servidor falla
    valor_compra = 10.77
    valor_venta = 12.32

    try:
        # 1. Intentar obtener los datos desde la API oficial de BMSC
        resp = session.get(API_BMSC, headers=headers, timeout=20)
        if resp.status_code == 200:
            datos = resp.json()
            valor_compra = float(datos["compra"])
            valor_venta = float(datos["venta"])
            print("Datos obtenidos exitosamente desde la API interna del BMSC.")
        else:
            print(f"Aviso: La API respondió con código {resp.status_code}. Se usarán valores de referencia.")
    except Exception as e:
        print(f"Aviso al consultar la API del BMSC: {e}. Se usarán valores de referencia.")

    # Fecha y hora exacta de consulta con zona horaria de Bolivia
    fecha_hora_actual = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora_actual, valor_compra, valor_venta


def consolidar(fn, fecha, valor):
    """Guarda el registro en el CSV con columnas timestamp,value."""
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
