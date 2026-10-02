#!/usr/bin/env python3

import re
import sys
import time
import requests
from bs4 import BeautifulSoup

# Configuración básica de conexión
REQUEST_TIMEOUT = (10, 30)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# URL a través del reader proxy para saltar restricciones de datacenters
URL_PRODEM_PROXY = "https://r.jina.ai/https://www.prodem.bo/Inicio"
URL_PRODEM_DIRECTA = "https://www.prodem.bo/Inicio"


def solicitar(url, max_retries=3):
    """Envía la solicitud web con reintentos automáticos si falla."""
    for intento in range(max_retries + 1):
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            if intento == max_retries:
                raise error
            # Espera exponencial: 1s, 2s, 4s...
            time.sleep(2**intento)


def numero(valor):
    """Limpia el texto y extrae el número flotante de compra o venta."""
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


def obtener_cotizacion_prodem():
    # 1. Intento principal usando el proxy de lectura
    try:
        respuesta = solicitar(URL_PRODEM_PROXY)
        cuerpo = respuesta.text

        # Busca el patrón en texto plano generado por el reader:
        # Ejemplo: "Compra: 6.86" y "Venta: 6.96"
        patron_compra = re.search(r"compra\s*[:\-]?\s*(\d+[.,]\d+)", cuerpo, flags=re.IGNORECASE)
        patron_venta = re.search(r"venta\s*[:\-]?\s*(\d+[.,]\d+)", cuerpo, flags=re.IGNORECASE)

        if patron_compra and patron_venta:
            return {
                "compra": numero(patron_compra.group(1)),
                "venta": numero(patron_venta.group(1)),
            }
    except Exception:
        pass

    # 2. Intento de respaldo: conexión directa e inspección de selectores HTML
    sopa = BeautifulSoup(solicitar(URL_PRODEM_DIRECTA).text, "html.parser")
    compra = sopa.select_one("#prodem-compra")
    venta = sopa.select_one("#prodem-venta")

    if compra and venta and compra.text.strip() and venta.text.strip():
        return {
            "compra": numero(compra.text),
            "venta": numero(venta.text),
        }

    raise ValueError("No se pudieron extraer los valores de compra y venta de Prodem.")


if __name__ == "__main__":
    try:
        resultado = obtener_cotizacion_prodem()
        print("Cotización obtenida exitosamente:")
        print(f"  - Compra: {resultado['compra']}")
        print(f"  - Venta:  {resultado['venta']}")
    except Exception as err:
        print(f"Error al obtener los datos: {err}")
        sys.exit(1)
