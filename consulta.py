import json
import requests

# URL de la API proporcionada
url = "https://intranet.premiumcollege.edu.pe/ajax/apiDocentes.php?control=all"

# Cabeceras estándar para simular una petición normal de navegador
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    # Realizamos la petición GET
    print("Consultando la API...")
    response = requests.get(url, headers=headers)
    
    # Forzar la codificación UTF-8 para arreglar textos rotos como "AÃ‘OS" o "VILLAORDUÃ‘A"
    response.encoding = "utf-8"
    
    # Validamos que la respuesta HTTP sea exitosa (Código 200)
    response.raise_for_status()
    
    # Convertimos la respuesta de texto a una lista de Python (JSON)
    lista_docentes = response.json()
    
    print(f"\n¡Conexión exitosa! Se encontraron {len(lista_docentes)} registros.\n")
    
    # Ejemplo 1: Mostrar una lista limpia en consola
    print(f"{'DNI':<10} | {'NOMBRE':<35} | {'CARGO':<25} | {'DETALLE'}")
    print("-" * 90)
    
    for docente in lista_docentes:
        # Usamos las llaves descriptivas que provee tu JSON
        dni = docente.get("dni", "")
        nombre = docente.get("datos", "")
        cargo = docente.get("descrCargo", "")
        detalle = docente.get("detalle", "")
        
        print(f"{dni:<10} | {nombre:<35} | {cargo:<25} | {detalle}")

    # Ejemplo 2: Guardar el resultado en un archivo local .json por si lo necesitas
    with open("docentes.json", "w", encoding="utf-8") as archivo:
        json.dump(lista_docentes, archivo, indent=4, ensure_ascii=False)
    print("\n[INFO] Los datos se han guardado exitosamente en 'docentes.json'")

except requests.exceptions.HTTPError as http_err:
    print(f"Error HTTP al consultar la API: {http_err}")
except ValueError:
    print("El servidor no devolvió un formato JSON válido.")
except Exception as err:
    print(f"Ocurrió un error inesperado: {err}")