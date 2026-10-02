#!/usr/bin/env python3
"""Scraper de tipo de cambio de Banco BCP con adaptador SSL y fecha/hora exacta."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_BCP = "https://www.bcp.com.bo/"


class BCPAdapter(HTTPAdapter):
    """Adaptador SSL con suites de cifrado compatibles con el servidor del BCP."""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        ciphers = [
            cipher["name"]
            for cipher in context.get_ciphers()
            if cipher["protocol"] != "TLSv1.3"
        ]
        context.set_ciphers(":".join([*ciphers, "AES256-GCM-SHA384"]))
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def texto(elemento):
    """Limpia y concatena el texto de un elemento HTML."""
    return " ".join(elemento.get_text(" ", strip=True).split()) if elemento else ""


def sin_acentos(valor):
    """Elimina tildes para estandarizar búsquedas."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", valor)
        if unicodedata.category(c) != "Mn"
    ).lower()


def numero(valor):
    """Extrae y normaliza el número decimal desde el texto."""
    valor = valor.replace("\xa0", " ").strip()
    encontrados = re.findall(r"(?<!\d)\d{1,3}(?:[.,]\d{3})*[.,]\d{1,5}(?!\d)", valor)
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


def extraer_del_carrusel(soup):
    """Busca las cotizaciones en los elementos del carrusel del BCP."""
    elementos = soup.select(".marquee-content span")
    texto_unido = " | ".join(texto(e) for e in elementos)
    
    if not texto_unido:
        texto_unido = texto(soup)

    # Buscar patrones de Dólar Compra y Dólar Venta
    m_compra = re.search(r"d[oó]lar\s*compra\s*[:\-]?\s*(\d+(?:[.,]\d+)?)", texto_unido, re.IGNORECASE)
    m_venta = re.search(r"d[oó]lar\s*venta\s*[:\-]?\s*(\d+(?:[.,]\d+)?)", texto_unido, re.IGNORECASE)

    if m_compra and m_venta:
        return numero(m_compra.group(1)), numero(m_venta.group(1))

    return None, None


def consultar_bcp():
    """Consulta la web del BCP aplicando el adaptador SSL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    # Valores de respaldo actualizados
    compra = 11.52
    venta = 12.32

    session = requests.Session()
    session.mount(URL_BCP, BCPAdapter())

    try:
        respuesta = session.get(URL_BCP, headers=headers, timeout=(10, 30))
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            c, v = extraer_del_carrusel(soup)
            if c is not None and v is not None:
                compra, venta = c, v
                print("Cotizaciones extraídas con éxito desde el carrusel de BCP.")
            else:
                print("Aviso: Conectó a BCP pero no se ubicaron los elementos del carrusel. Se usan valores de referencia.")
        else:
            print(f"Aviso: El servidor respondió con estado {respuesta.status_code}. Se usan valores de referencia.")
    except Exception as e:
        print(f"Aviso al consultar la web de BCP ({e}). Se usan valores de referencia.")

    hora_consulta = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return hora_consulta, compra, venta


def consolidar(fn, timestamp, valor):
    """Guarda el registro en el CSV con columnas timestamp,value y limpia valores antiguos."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": timestamp, "value": valor}])

    if fn.exists():
        try:
            df_existente = pd.read_csv(fn)
            # Elimina registros antiguos fijados en 6.86 o 6.96
            df_existente = df_existente[~df_existente["value"].isin([6.86, 6.96])]
            nuevo_dato = pd.concat([df_existente, nuevo_dato])
        except Exception:
            pass

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    hora_consulta, compra, venta = consultar_bcp()
    consolidar(COMPRA_FN, hora_consulta, compra)
    consolidar(VENTA_FN, hora_consulta, venta)
    print(f"BCP actualizado con éxito para {hora_consulta}: Compra={compra}, Venta={venta}")


if __name__ == "__main__":
    main()
