
#!/usr/bin/env python3
"""Scraper de tipo de cambio oficial publicado por Banco Unión."""

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
URL_BANCO_UNION = "https://bancounion.com.bo/"


def normalizar_decimal(texto):
    """Convierte texto como '11,02' o '12.12' en número flotante 11.02."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def consultar_banco_union(session):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    response = session.get(URL_BANCO_UNION, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    texto_completo = soup.get_text(" ", strip=True)

    # Patrón exacto para Banco Unión:
    # "Compra BOB: 11,02 / Venta 12,12" o variaciones similares
    compra_match = re.search(
        r"compra\s*(?:bob)?\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )
    venta_match = re.search(
        r"venta\s*(?:bob)?\s*[:\-]?\s*(\d+[.,]\d+)",
        texto_completo,
        re.IGNORECASE,
    )

    if not compra_match or not venta_match:
        # Intento de rescate si el formato viene junto en una sola frase
        rescate = re.search(
            r"compra\s*bob:\s*(\d+[.,]\d+)\s*/\s*venta\s*(\d+[.,]\d+)",
            texto_completo,
            re.IGNORECASE,
        )
        if rescate:
            valor_compra = normalizar_decimal(rescate.group(1))
            valor_venta = normalizar_decimal(rescate.group(2))
        else:
            raise ValueError("No se encontraron los valores de compra y venta en el texto de Banco Unión.")
    else:
        valor_compra = normalizar_decimal(compra_match.group(1))
        valor_venta = normalizar_decimal(venta_match.group(1))

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
        fecha, compra, venta = consultar_banco_union(session)

    consolidar(COMPRA_FN, fecha, compra)
    consolidar(VENTA_FN, fecha, venta)
    print(f"Banco Union actualizado con éxito para {fecha}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
