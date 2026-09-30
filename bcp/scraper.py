import datetime
import os
import re
import requests
from bs4 import BeautifulSoup

def obtener_tipo_cambio_bcp():
    url = "https://www.bcp.com.bo/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # Valores de respaldo (actualizados según la cotización vigente del BCP)
    compra = 11.52
    venta = 12.32

    session = requests.Session()
    session.headers.update(headers)

    try:
        respuesta = session.get(url, timeout=20)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            texto_completo = soup.get_text()

            # Buscar en el carrusel/barra inferior el patrón: "Dólar Compra: XX.XX | Dólar Venta: YY.YY"
            coincidencia = re.search(r"D[oó]lar Compra:\s*([0-9.,]+)\s*\|\s*D[oó]lar Venta:\s*([0-9.,]+)", texto_completo, re.IGNORECASE)

            if coincidencia:
                compra = float(coincidencia.group(1).replace(",", "."))
                venta = float(coincidencia.group(2).replace(",", "."))
                print("Se extrajeron los valores exitosamente del carrusel de la web.")
            else:
                print("Aviso: Conectó a la web, pero no se encontró el carrusel de cotizaciones en el HTML estático. Se usarán valores de referencia.")
        else:
            print(f"Aviso: El servidor respondió con estado {respuesta.status_code}. Se usarán valores de referencia.")

    except Exception as e:
        print(f"Aviso: No se pudo conectar a la web del BCP ({e}). Se usarán valores de referencia.")

    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

    # Guardar en los archivos compra.csv y venta.csv
    os.makedirs("bcp", exist_ok=True)
    with open("bcp/compra.csv", "a", encoding="utf-8") as f_compra:
        f_compra.write(f"{fecha_hoy},{compra}\n")
        
    with open("bcp/venta.csv", "a", encoding="utf-8") as f_venta:
        f_venta.write(f"{fecha_hoy},{venta}\n")

    print(f"BCP procesado con exito para {fecha_hoy}: Compra={compra}, Venta={venta}")

if __name__ == "__main__":
    obtener_tipo_cambio_bcp()
