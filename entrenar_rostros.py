import os
import pickle
import face_recognition
import mysql.connector


ARCHIVO_ENCODINGS = "encodings_rostros.pkl"


conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="@Otita2345",
    database="reconocimiento_facial"
)

cursor = conexion.cursor(dictionary=True)

cursor.execute("SELECT * FROM persona")
personas = cursor.fetchall()


rostros_codificados = []
datos_personas = []


for persona in personas:
    ruta = persona["ruta_foto"]

    if not os.path.exists(ruta):
        print(f"No existe la ruta: {ruta}")
        continue

    print(f"\nProcesando: {persona['nombre']}")

    for archivo in os.listdir(ruta):
        if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
            ruta_imagen = os.path.join(ruta, archivo)

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

                datos_personas.append({
                    "id_persona": persona["id_persona"],
                    "nombre": persona["nombre"],
                    "codigo": persona["codigo"],
                    "cargo": persona["cargo"],
                    "area": persona["area"],
                    "ruta_imagen": ruta_imagen
                })

                print(f"OK: {ruta_imagen}")
            else:
                print(f"NO SIRVE: {ruta_imagen}")


datos = {
    "rostros_codificados": rostros_codificados,
    "datos_personas": datos_personas
}


with open(ARCHIVO_ENCODINGS, "wb") as archivo:
    pickle.dump(datos, archivo)


print("\nEntrenamiento terminado.")
print(f"Archivo creado: {ARCHIVO_ENCODINGS}")
print(f"Rostros guardados: {len(rostros_codificados)}")

cursor.close()
conexion.close()