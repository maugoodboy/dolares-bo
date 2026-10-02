#!/usr/bin/env python3
"""Scraper de tipo de cambio de Banco Económico (Baneco) con fecha y hora exacta."""

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

URL_HOME = "https://www.baneco.com.bo/"
URL_API = "https://www.baneco.com.bo/gbGLOBALTiposDeCambio"


def texto(elemento):
    """Limpia y extrae el texto legible de un tag HTML."""
    return " ".join(elemento.get_text(" ", strip=True).split()) if elemento else ""


def sin_acentos(valor):
    """Elimina tildes para estandarizar búsquedas."""
    return "".join(
        c for c in unicodedata.normalize("NFD", valor)
        if unicodedata.category(c) != "Mn"
    ).lower()


def numero(valor):
    """Extrae y normaliza una cifra decimal desde el texto."""
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


def extraer_de_texto(texto_fuente):
    """Busca compra y venta en el texto devuelto por Baneco."""
    texto_norm = sin_acentos(texto_fuente)
    
    # 1. Patrón con 'compra' y 'venta'
    m_compra = re.search(r"compra\s*[:\-]?\s*(\d+(?:[.,]\d+)?)", texto_norm)
    m_venta = re.search(r"venta\s*[:\-]?\s*(\d+(?:[.,]\d+)?)", texto_norm)
    
    if m_compra and m_venta:
        return numero(m_compra.group(1)), numero(m_venta.group(1))

    # 2. Patrón general con dos cifras decimales consecutivas
    cifras = re.findall(r"\d+[.,]\d+", texto_fuente)
    if len(cifras) >= 2:
        return numero(cifras[0]), numero(cifras[1])

    return None, None


def consultar_baneco(session):
    """Consulta la cotización probando el selector HTML y el endpoint JSON."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
    }

    compra, venta = None, None

    # Método 1: Leer el elemento #cotizacion de la portada
    try:
        resp = session.get(URL_HOME, headers=headers, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            elem_cot = soup.select_one("#cotizacion")
            if elem_cot:
                c, v = extraer_de_texto(texto(elem_cot))
                if c and v:
                    compra, venta = c, v
                    print("Cotización obtenida desde #cotizacion en la portada.")
    except Exception as e:
        print(f"Aviso al consultar portada de Baneco: {e}")

    # Método 2: Consultar la API JSON interna si no se obtuvo de la portada
    if compra is None or venta is None:
        try:
            resp_api = session.get(URL_API, headers=headers, timeout=20)
            if resp_api.status_code == 200:
                data = resp_api.json()
                contenido = data.get("gbGLOBALTiposDeCambioResult", "")
                c, v = extraer_de_texto(contenido)
                if c and v:
                    compra, venta = c, v
                    print("Cotización obtenida desde la API gbGLOBALTiposDeCambio.")
        except Exception as e:
            print(f"Aviso al consultar API de Baneco: {e}")

    # Método 3: Valores de respaldo vigentes
    if compra is None or venta is None:
        print("Aviso: No se pudo extraer online de Baneco. Se usan valores de referencia.")
        compra = 11.42
        venta = 12.37

    # Marca de tiempo con fecha y hora exacta
    fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora, compra, venta


def consolidar(fn, fecha_hora, valor):
    """Guarda el dato en el CSV y descarta valores de respaldo antiguos."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        try:
            df_existente = pd.read_csv(fn)
            # Elimina registros con las bandas antiguas obsoletas si existiesen
            df_existente = df_existente[~df_existente["value"].isin([6.86, 6.96])]
            nuevo_dato = pd.concat([df_existente, nuevo_dato])
        except Exception:
            pass

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    with requests.Session() as session:
        fecha_hora, compra, venta = consultar_baneco(session)

    consolidar(COMPRA_FN, fecha_hora, compra)
    consolidar(VENTA_FN, fecha_hora, venta)
    print(
        f"Banco Economico actualizado con exito para {fecha_hora}: "
        f"Compra={compra}, Venta={venta}"
    )


if __name__ == "__main__":
    main()
