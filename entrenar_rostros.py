import os
import pickle
import face_recognition
import requests

# Configuración del archivo de salida
ARCHIVO_ENCODINGS = "encodings_rostros.pkl"

# URL de la API de la intranet
URL_API = "https://intranet.premiumcollege.edu.pe/ajax/apiDocentes.php?control=all"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    print("Consultando el listado de docentes desde la API...")
    response = requests.get(URL_API, headers=headers)
    response.encoding = "utf-8" # Corregir caracteres como eñes y tildes
    response.raise_for_status()
    
    # La API nos devuelve directamente la lista de personas
    personas = response.json()
    print(f"API consultada con éxito. Se procesarán {len(personas)} registros.\n")

except Exception as e:
    print(f"Error crítico al conectar con la API: {e}")
    exit()

rostros_codificados = []
datos_personas = []

# Procesamiento de imágenes (Tu lógica original)
for persona in personas:
    # Validamos que existan los datos mínimos en el JSON de la API
    dni = persona.get("dni")
    nombre = persona.get("datos") # En la API el campo se llama 'datos', no 'nomb'
    
    if not dni or not nombre:
        continue

    ruta = f"./src/docentes/{dni}"

    if not os.path.exists(ruta):
        print(f"No existe la ruta local: {ruta}")
        continue

    print(f"\nProcesando localmente a: {nombre} (DNI: {dni})")

    for archivo in os.listdir(ruta):
        if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
            ruta_imagen = os.path.join(ruta, archivo)

            try:
                imagen = face_recognition.load_image_file(ruta_imagen)

                ubicaciones = face_recognition.face_locations(
                    imagen,
                    number_of_times_to_upsample=2,
                    model="hog"
                )

                codificaciones = face_recognition.face_encodings(
                    imagen,
                    ubicaciones
                )

                if len(codificaciones) > 0:
                    rostros_codificados.append(codificaciones[0])

                    # Mapeo de los datos ajustado a los nombres de las llaves de la API
                    datos_personas.append({
                        "idDocente": persona.get("idDocente"),
                        "dni": dni,
                        "nombre": nombre,
                        "cargo": persona.get("descrCargo"),
                        "area": persona.get("detalle"),
                        "ruta_imagen": ruta_imagen
                    })

                    print(f"OK: {ruta_imagen}")
                else:
                    print(f"NO SIRVE (No se detectó rostro): {ruta_imagen}")
            
            except Exception as e:
                print(f"ERROR al procesar la imagen {ruta_imagen}: {e}")

# Guardar los encodings generados en el archivo pickle
datos = {
    "rostros_codificados": rostros_codificados,
    "datos_personas": datos_personas
}

with open(ARCHIVO_ENCODINGS, "wb") as archivo:
    pickle.dump(datos, archivo)

print("\n--- Entrenamiento terminado ---")
print(f"Archivo creado: {ARCHIVO_ENCODINGS}")
print(f"Rostros codificados guardados: {len(rostros_codificados)}")