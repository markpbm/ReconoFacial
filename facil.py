import cv2
import os
import time
import pickle
import numpy as np
import face_recognition
import mysql.connector
from datetime import datetime


# =========================
# CONEXIÓN MYSQL
# =========================

conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="@Otita2345",
    database="reconocimiento_facial"
)

cursor = conexion.cursor(dictionary=True)


# =========================
# CARGAR ROSTROS ENTRENADOS
# =========================

ARCHIVO_ENCODINGS = "encodings_rostros.pkl"

if not os.path.exists(ARCHIVO_ENCODINGS):
    print("No existe encodings_rostros.pkl.")
    print("Primero ejecuta: python entrenar_rostro.py")
    cursor.close()
    conexion.close()
    exit()

with open(ARCHIVO_ENCODINGS, "rb") as archivo:
    datos = pickle.load(archivo)

rostros_codificados = datos["rostros_codificados"]
datos_personas = datos["datos_personas"]

print("Rostros cargados desde entrenamiento:", len(rostros_codificados))

if len(rostros_codificados) == 0:
    print("No hay rostros entrenados.")
    print("Revisa tus fotos y vuelve a ejecutar: python entrenar_rostro.py")
    cursor.close()
    conexion.close()
    exit()


# =========================
# MARCAR ASISTENCIA
# =========================

def marcar_asistencia(id_persona):
    ahora = datetime.now()
    fecha = ahora.date()
    hora = ahora.time()

    try:
        sql = """
        INSERT INTO asistencia (id_persona, fecha, hora, estado)
        VALUES (%s, %s, %s, %s)
        """

        valores = (id_persona, fecha, hora, "Presente")

        cursor.execute(sql, valores)
        conexion.commit()

        print("Asistencia marcada correctamente.")

    except mysql.connector.errors.IntegrityError:
        print("Esta persona ya marcó asistencia hoy.")


# =========================
# GUARDAR FOTO PENDIENTE
# =========================

def guardar_foto_pendiente(nombre_persona, frame):
    carpeta = os.path.join("fotos_pendientes", nombre_persona)

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"captura_{fecha_hora}.jpg"
    ruta_guardado = os.path.join(carpeta, nombre_archivo)

    cv2.imwrite(ruta_guardado, frame)

    print(f"Foto pendiente guardada: {ruta_guardado}")


# =========================
# CONECTAR CÁMARA EZVIZ
# =========================

def conectar_camara():
    # Stream liviano recomendado para mejor velocidad
    url = "rtsp://admin:FLMUDZ@192.168.0.118:554/h264/ch1/sub/av_stream"

    # Si quieres probar mejor calidad, usa este, pero puede ir más lento:
    # url = "rtsp://admin:FLMUDZ@192.168.0.118:554/h264/ch1/main/av_stream"

    cam = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cam, url


# =========================
# INICIAR CÁMARA
# =========================

camara, url_rtsp = conectar_camara()

if not camara.isOpened():
    print("Error: no se pudo abrir la cámara EZVIZ.")
    print("Verifica que VLC esté cerrado y que la cámara esté conectada.")
    cursor.close()
    conexion.close()
    exit()

print("Cámara iniciada. Presiona ESC para salir.")


# =========================
# VARIABLES DE CONTROL
# =========================

marcados_en_sesion = set()

fallos = 0
contador_frames = 0

ultima_persona_reconocida = None
ultimo_tiempo_reconocido = 0
ultimo_guardado_pendiente = 0


# =========================
# CONFIGURACIÓN DE RENDIMIENTO
# =========================

# Procesa reconocimiento cada 5 frames para que no se ponga lento
PROCESAR_CADA_N_FRAMES = 3

# Escala 0.35 es balance entre velocidad y detección
ESCALA = 0.5

# 1 es más rápido. 2 detecta rostros más pequeños pero es más lento
UPSAMPLE = 2

# Distancia máxima para aceptar una persona
# 0.45 = estricto
# 0.50 = normal
# 0.55 = más flexible
TOLERANCIA = 0.50


# =========================
# BUCLE PRINCIPAL
# =========================

while True:
    ret, frame = camara.read()

    if not ret or frame is None:
        fallos += 1
        print(f"No se pudo leer frame. Reintentando... intento {fallos}")

        time.sleep(0.5)

        if fallos >= 10:
            print("Reconectando cámara RTSP...")

            camara.release()
            time.sleep(2)

            camara, url_rtsp = conectar_camara()
            fallos = 0

        continue

    fallos = 0
    contador_frames += 1

    procesar_reconocimiento = contador_frames % PROCESAR_CADA_N_FRAMES == 0

    if procesar_reconocimiento:
        frame_pequeno = cv2.resize(frame, (0, 0), fx=ESCALA, fy=ESCALA)
        frame_rgb = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2RGB)

        ubicaciones = face_recognition.face_locations(
            frame_rgb,
            number_of_times_to_upsample=UPSAMPLE,
            model="hog"
        )

        codificaciones = face_recognition.face_encodings(
            frame_rgb,
            ubicaciones
        )

        print("Rostros detectados:", len(ubicaciones))

        for codificacion, ubicacion in zip(codificaciones, ubicaciones):
            nombre_mostrar = "Desconocido"

            distancias = face_recognition.face_distance(
                rostros_codificados,
                codificacion
            )

            if len(distancias) > 0:
                indice_mejor = np.argmin(distancias)
                mejor_distancia = distancias[indice_mejor]

                print("Mejor distancia:", mejor_distancia)

                if mejor_distancia <= TOLERANCIA:
                    persona_detectada = datos_personas[indice_mejor]

                    id_persona = persona_detectada["id_persona"]
                    nombre = persona_detectada["nombre"]
                    codigo = persona_detectada["codigo"]

                    nombre_mostrar = f"{nombre} - {codigo}"

                    ultima_persona_reconocida = nombre
                    ultimo_tiempo_reconocido = time.time()

                    if id_persona not in marcados_en_sesion:
                        marcar_asistencia(id_persona)
                        marcados_en_sesion.add(id_persona)

                else:
                    nombre_mostrar = "Desconocido"

                    # Si antes reconoció a alguien y luego duda,
                    # guarda foto pendiente para revisión.
                    if ultima_persona_reconocida is not None:
                        segundos_pasados = time.time() - ultimo_tiempo_reconocido
                        segundos_desde_ultimo_guardado = time.time() - ultimo_guardado_pendiente

                        if segundos_pasados <= 5 and segundos_desde_ultimo_guardado >= 3:
                            guardar_foto_pendiente(ultima_persona_reconocida, frame)
                            ultimo_guardado_pendiente = time.time()
                            nombre_mostrar = f"Pendiente: {ultima_persona_reconocida}"

            top, right, bottom, left = ubicacion

            top = int(top / ESCALA)
            right = int(right / ESCALA)
            bottom = int(bottom / ESCALA)
            left = int(left / ESCALA)

            if nombre_mostrar == "Desconocido":
                color = (0, 0, 255)
            elif "Pendiente" in nombre_mostrar:
                color = (0, 255, 255)
            else:
                color = (0, 255, 0)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            cv2.putText(
                frame,
                nombre_mostrar,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )

    cv2.imshow("Reconocimiento Facial EZVIZ", frame)

    tecla = cv2.waitKey(1)

    if tecla == 27:
        break


# =========================
# CERRAR TODO
# =========================

camara.release()
cv2.destroyAllWindows()
cursor.close()
conexion.close()