#!/usr/bin/env python3
"""Scraper de tipo de cambio publicado por Banco Fortaleza usando navegador automatizado."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from playwright.sync_api import sync_playwright

DATA_DIR = Path(__file__).resolve().parent
COMPRA_FN = DATA_DIR / "compra.csv"
VENTA_FN = DATA_DIR / "venta.csv"
TIMEZONE = "America/La_Paz"
URL_FORTALEZA = "https://bancofortaleza.com.bo"


def normalizar_decimal(texto):
    """Extrae el valor numérico y lo convierte a formato decimal flotante."""
    limpio = re.search(r"(\d+[.,]\d+)", str(texto))
    if not limpio:
        raise ValueError(f"No se pudo extraer número de: {texto}")
    return float(limpio.group(1).replace(",", "."))


def limpiar_texto(texto):
    """Elimina tildes y normaliza espacios."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return " ".join(plano.split()).lower()


def consultar_fortaleza():
    """Abre la página con un navegador real, extrae los datos mediante selectores estables."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = context.new_page()

        # Abre la página principal esperando hasta que termine la carga de red
        page.goto(URL_FORTALEZA, wait_until="networkidle", timeout=60000)

        # Espera un momento prudencial para la ejecución de las APIs de tipo de cambio
        page.wait_for_timeout(3000)

        # 1. Validar que la API del banco no haya fallado
        texto_cuerpo = page.inner_text("body")
        if "no se pudieron cargar los datos" in limpiar_texto(texto_cuerpo):
            browser.close()
            raise RuntimeError("El portal del banco experimenta problemas y no cargó las tasas.")

        # 2. Extracción precisa por selectores de la estructura de la tabla de tipo de cambio
        # Buscamos el contenedor principal de Tipo de Cambio para no confundir datos con el pie de página
        contenedor_tasas = page.locator("text=Tipo de Cambio / >> xpath=../..")
        
        if contenedor_tasas.count() == 0:
            # Selector de respaldo si la estructura visual cambia ligeramente
            contenedor_tasas = page.locator("h2:has-text('Tipo de Cambio') + div, div:has-text('DÓLAR')")

        # Extraemos el bloque de texto específico de la sección de monedas
        texto_bloque = contenedor_tasas.first.inner_text()
        browser.close()

    texto_limpio = limpiar_texto(texto_bloque)

    # Buscamos de forma secuencial y limpia los valores numéricos dentro del bloque aislado
    # Al estar aislados en el bloque de tasas, los primeros decimales corresponden a Compra y Venta
    valores = re.findall(r"\d+[.,]\d+", texto_limpio)

    if len(valores) < 2:
        raise ValueError(
            f"No se pudieron segmentar los valores de compra/venta en el bloque:\n{texto_limpio}"
        )

    # El primer valor numérico tras las etiquetas suele ser Compra y el segundo Venta
    valor_compra = normalizar_decimal(valores[0])
    valor_venta = normalizar_decimal(valores[1])

    # Fecha y hora exacta en Bolivia
    fecha_hora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return fecha_hora, valor_compra, valor_venta


def consolidar(fn, fecha_hora, valor):
    """Guarda o actualiza el registro en el archivo CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    nuevo_dato = pd.DataFrame([{"timestamp": fecha_hora, "value": valor}])

    if fn.exists():
        df_existente = pd.read_csv(fn)
        nuevo_dato = pd.concat([df_existente, nuevo_dato])

    nuevo_dato = nuevo_dato.drop_duplicates(subset=["timestamp"], keep="last")
    nuevo_dato.sort_values("timestamp").to_csv(fn, index=False)


def main():
    try:
        fecha_hora, compra, venta = consultar_fortaleza()
        consolidar(COMPRA_FN, fecha_hora, compra)
        consolidar(VENTA_FN, fecha_hora, venta)
        print(
            f"✅ Banco Fortaleza actualizado con éxito para {fecha_hora}: "
            f"Compra={compra} Bs, Venta={venta} Bs"
        )
    except Exception as e:
        print(f"❌ Error al ejecutar el scraper: {e}")


if __name__ == "__main__":
    main()
