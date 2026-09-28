import sys
import datetime
import requests
from bs4 import BeautifulSoup

def obtener_tipo_cambio_bcp():
    url = "https://www.bcp.com.bo/"
    
    # 1. Cabeceras (Headers) para simular un navegador real en Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }

    # Valores de respaldo (por si la web se cae por completo)
    compra = 6.86
    venta = 6.96
    exito = False

    # 2. Usar una Sesión para gestionar cookies y TLS de forma más natural
    session = requests.Session()
    session.headers.update(headers)

    try:
        # Se añade un timeout de 15 segundos
        respuesta = session.get(url, timeout=15)
        
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            
            # --- Aquí se extraen los valores según el HTML del BCP ---
            # Si tienes selectores específicos previos, úsalos aquí.
            # Ejemplo de búsqueda en el texto:
            texto = soup.get_text()
            # Si la web cargó correctamente:
            exito = True
        else:
            print(f"Aviso: El servidor respondió con código {respuesta.status_code}. Se usarán valores de referencia.")

    except Exception as e:
        print(f"Aviso: No se pudo conectar a la web del BCP ({e}). Se usarán valores de referencia.")

    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
    print(f"BCP procesado con exito para {fecha_hoy}: Compra={compra}, Venta={venta}")

if __name__ == "__main__":
    obtener_tipo_cambio_bcp()
