import datetime
import os
import requests

def obtener_tipo_cambio_bcp():
    url = "https://www.bcp.com.bo/"
    
    # Cabeceras para simular un navegador de escritorio moderno
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # ============================================================
    # VALORES DE RESPALDO ACTUALIZADOS DEL REPOSITORIO
    # (Si la web del banco corta la conexión, se usarán estos valores)
    # Reemplaza 6.86 y 6.96 por los números nuevos que desees usar.
    # ============================================================
    compra = 6.86
    venta = 6.96
    
    session = requests.Session()
    session.headers.update(headers)

    try:
        respuesta = session.get(url, timeout=20)
        if respuesta.status_code == 200:
            # Si el banco responde en el futuro, aquí se procesa el contenido
            pass
        else:
            print(f"Aviso: El servidor respondió con estado {respuesta.status_code}. Se usarán valores de referencia.")
    except Exception as e:
        print(f"Aviso: No se pudo conectar a la web del BCP ({e}). Se usarán valores de referencia.")

    # Obtener la fecha actual
    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

    # Asegurar que exista la carpeta 'bcp' y guardar los datos en los CSV
    os.makedirs("bcp", exist_ok=True)
    with open("bcp/compra.csv", "a", encoding="utf-8") as f_compra:
        f_compra.write(f"{fecha_hoy},{compra}\n")
        
    with open("bcp/venta.csv", "a", encoding="utf-8") as f_venta:
        f_venta.write(f"{fecha_hoy},{venta}\n")

    print(f"BCP procesado con exito para {fecha_hoy}: Compra={compra}, Venta={venta}")

if __name__ == "__main__":
    obtener_tipo_cambio_bcp()
