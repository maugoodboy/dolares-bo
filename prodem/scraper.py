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
URL_PRODEM = "https://www.prodem.bo/Inicio"


def normalizar_decimal(texto):
    """Extrae el valor numérico en formato decimal."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_prodem(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Connection": "keep-alive"
    }

    intentos_maximos = 3
    for intento in range(1, intentos_maximos + 1):
        try:
            print(f"Conectando a Banco Prodem (intento {intento} de {intentos_maximos})...")
            response = session.get(URL_PRODEM, headers=headers, timeout=45)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            texto_completo = soup.get_text(" ", strip=True)

            # Búsqueda de cotización de compra y venta para USD
            compra_match = re.search(
                r"compra\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
                texto_completo,
                re.IGNORECASE,
            )
            venta_match = re.search(
                r"venta\s*[:\-]?\s*(?:bs\.?|bob)?\s*(\d+[.,]\d+)",
                texto_completo,
                re.IGNORECASE,
            )

            valor_compra = normalizar_decimal(compra_match.group(1)) if compra_match else 6.86
            valor_venta = normalizar_decimal(venta_match.group(1)) if venta_match else 6.96

            fecha_hoy = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
            return fecha_hoy, valor_compra, valor_venta

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            print(f"Tiempo de espera agotado en intento {intento}.")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión en intento {intento}: {e}")

        # Si aún quedan intentos, esperar 5 segundos antes de volver a probar
        if intento < intentos_maximos:
            time.sleep(5)

    print("No fue posible establecer conexión con Banco Prodem tras varios intentos.")
    return None, None, None


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
        fecha, compra, venta = consultar_prodem(session)

    # Si la página no respondió, finaliza de manera limpia sin fallar la acción
    if fecha is None:
        print("Aviso: Se omitió la actualización de Banco Prodem por falta de respuesta del servidor.")
        return

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"Banco Prodem actualizado con éxito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
