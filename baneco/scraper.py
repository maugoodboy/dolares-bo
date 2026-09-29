#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Económico (Baneco)."""

from datetime import datetime
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"

# Cambiado a la portada principal donde aparece la tabla de cotizaciones
URL_BANECO = "https://www.baneco.com.bo/"


def normalizar_decimal(texto):
  """Extrae el valor numérico y lo convierte en decimal."""
  limpio = re.search(r"(\d+[.,]\d+)", str(texto))
  if not limpio:
    raise ValueError(f"No se pudo extraer número de: {texto}")
  return float(limpio.group(1).replace(",", "."))


def consultar_baneco(session):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "es-ES,es;q=0.9",
  }
  response = session.get(URL_BANECO, headers=headers, timeout=20)
  response.raise_for_status()

  soup = BeautifulSoup(response.text, "html.parser")
  texto_completo = soup.get_text(" ", strip=True)

  # Busca específicamente la sección "Tipo de Cambio Banco Económico por Dólar: Compra: X - Venta: Y"
  patron = re.search(
      r"Banco\s+Econ[oó]mico\s+por\s+D[oó]lar.*?Compra\s*:\s*(\d+[.,]\d+).*?Venta\s*:\s*(\d+[.,]\d+)",
      texto_completo,
      re.IGNORECASE,
  )

  if not patron:
    raise RuntimeError(
        "No se encontraron las cotizaciones de Compra y Venta en la página del"
        " Banco Económico."
    )

  valor_compra = normalizar_decimal(patron.group(1))
  valor_venta = normalizar_decimal(patron.group(2))

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
    fecha, compra, venta = consultar_baneco(session)

  consolidar(COMPRA_FN, fecha, compra)
  consolidar(VENTA_FN, fecha, venta)
  print(
      "Banco Economico actualizado con exito para"
      f" {fecha}: Compra={compra}, Venta={venta}"
  )


if __name__ == "__main__":
  main()
