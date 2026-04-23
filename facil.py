import cv2
import face_recognition
import csv
import os
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================
NOMBRE_VENTANA = "Reconocimiento Facial"
RUTA_IMAGEN = "fotos/mark.jpg"
NOMBRE_PERSONA = "Mark"
ARCHIVO_SALIDA = "asistencia.csv"

# =========================
# CARGAR IMAGEN CONOCIDA
# =========================
imagen_mark = face_recognition.load_image_file(RUTA_IMAGEN)
encodings_mark = face_recognition.face_encodings(imagen_mark)

if len(encodings_mark) == 0:
    print(f"No se detectó ningún rostro en la imagen: {RUTA_IMAGEN}")
    exit()

encoding_mark = encodings_mark[0]

# Base simple local
encodings_conocidos = [encoding_mark]
nombres = [NOMBRE_PERSONA]

# Datos adicionales locales
datos_personas = {
    "Mark": {
        "codigo": "001",
        "cargo": "Usuario",
        "area": "Local"
    }
}

# =========================
# PREPARAR REGISTRO
# =========================
registrados = set()
registros_sesion = []

# Crear archivo CSV con cabecera si no existe
if not os.path.exists(ARCHIVO_SALIDA):
    with open(ARCHIVO_SALIDA, mode="w", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["nombre", "codigo", "cargo", "area", "fecha", "hora"])

# =========================
# INICIAR CÁMARA
# =========================
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: no se pudo abrir la cámara.")
    exit()

print("Cámara iniciada.")
print("Presiona ESC o cierra la ventana con la X para terminar.")

# =========================
# BUCLE PRINCIPAL
# =========================
while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo leer la cámara.")
        break

    # Convertir a RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detectar caras y obtener encodings
    caras = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, caras)

    for (top, right, bottom, left), encoding in zip(caras, encodings):
        nombre = "Desconocido"
        color = (0, 0, 255)  # rojo por defecto

        resultados = face_recognition.compare_faces(encodings_conocidos, encoding, tolerance=0.5)
        distancias = face_recognition.face_distance(encodings_conocidos, encoding)

        if len(distancias) > 0:
            mejor_indice = distancias.argmin()

            if resultados[mejor_indice]:
                nombre = nombres[mejor_indice]
                color = (0, 255, 0)  # verde si reconocido

                # Registrar una sola vez por sesión
                if nombre not in registrados:
                    ahora = datetime.now()
                    fecha = ahora.strftime("%Y-%m-%d")
                    hora = ahora.strftime("%H:%M:%S")

                    info = datos_personas.get(nombre, {})
                    codigo = info.get("codigo", "")
                    cargo = info.get("cargo", "")
                    area = info.get("area", "")

                    registros_sesion.append([nombre, codigo, cargo, area, fecha, hora])
                    registrados.add(nombre)

                    print(f"Registrado: {nombre} - {fecha} {hora}")

        # Dibujar rectángulo
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        # Texto principal
        cv2.putText(
            frame,
            nombre,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        # Mostrar datos extra si es conocido
        if nombre != "Desconocido":
            info = datos_personas.get(nombre, {})
            texto_extra = f"Cod: {info.get('codigo', '')} | {info.get('cargo', '')}"
            cv2.putText(
                frame,
                texto_extra,
                (left, bottom + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

    # Mostrar ventana
    cv2.imshow(NOMBRE_VENTANA, frame)

    # Cerrar con X
    if cv2.getWindowProperty(NOMBRE_VENTANA, cv2.WND_PROP_VISIBLE) < 1:
        break

    # Cerrar con ESC
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break

# =========================
# GUARDAR CSV AL FINAL
# =========================
cap.release()
cv2.destroyAllWindows()

if len(registros_sesion) > 0:
    with open(ARCHIVO_SALIDA, mode="a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerows(registros_sesion)

    print(f"\nSe exportó el archivo: {ARCHIVO_SALIDA}")
    print("Registros guardados:")
    for fila in registros_sesion:
        print(fila)
else:
    print("\nNo hubo registros nuevos. No se agregó nada al CSV.")