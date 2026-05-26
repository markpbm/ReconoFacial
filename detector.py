# ============================================================
# SISTEMA DE RECONOCIMIENTO FACIAL OPTIMIZADO
# PREMIUM COLLEGE
# ============================================================

# ------------------------------------------------------------
# LIBRERÍAS NECESARIAS
# ------------------------------------------------------------

import cv2                      # Procesamiento de imágenes y video
import os                       # Manejo de archivos y carpetas
import time                     # Control de tiempo
import pickle                   # Cargar archivos .pkl
import numpy as np              # Operaciones matemáticas
import face_recognition         # Reconocimiento facial
import threading                # Hilos para mejorar rendimiento
from datetime import datetime   # Fecha y hora actual
import requests

# ============================================================
# CONFIGURACIÓN GENERAL DEL SISTEMA
# ============================================================

# Archivo donde están guardados los rostros entrenados
ARCHIVO_ENCODINGS = "encodings_rostros.pkl"

# URL RTSP de la cámara EZVIZ
RTSP_URL = "rtsp://admin:FLMUDZ@192.168.0.118:554/h264/ch1/sub/av_stream"

# Procesar solo cada 8 frames para ahorrar CPU
PROCESAR_CADA_N_FRAMES = 5

# Reducir tamaño de imagen para acelerar detección
# 0.35 = 35% del tamaño original
ESCALA = 0.35

# 0 = más rápido
# 1 o 2 = detecta rostros más pequeños pero más lento
UPSAMPLE = 1

# Tolerancia de reconocimiento
# Menor valor = más estricto
TOLERANCIA = 0.48

# Tiempo en segundos para reutilizar reconocimiento
TIEMPO_CACHE_RECONOCIMIENTO = 2

# Máximo de errores antes de reconectar cámara
MAX_FALLOS_CAMARA = 10

# Mostrar FPS en pantalla
MOSTRAR_FPS = True

# ============================================================
# CARGAR ROSTROS ENTRENADOS
# ============================================================

# Verificar si existe el archivo .pkl
if not os.path.exists(ARCHIVO_ENCODINGS):
    print("No existe encodings_rostros.pkl")
    exit()

# Abrir archivo
with open(ARCHIVO_ENCODINGS, "rb") as archivo:
    datos = pickle.load(archivo)

# Extraer rostros codificados
rostros_codificados = np.array(datos["rostros_codificados"])

# Datos de personas
datos_personas = datos["datos_personas"]

print(f"Rostros cargados: {len(rostros_codificados)}")

# Validar si existen rostros
if len(rostros_codificados) == 0:
    print("No existen rostros entrenados.")
    exit()


# ============================================================
# VARIABLES GLOBALES
# ============================================================

# Frame capturado actualmente
frame_actual = None

# Frame procesado y dibujado
frame_procesado = None

# Lock para evitar conflictos entre hilos
lock_frame = threading.Lock()

# Control para no enviar muchas marcas seguidas del mismo docente
ultimo_marcado = {}

# Tiempo mínimo entre llamadas a la API por docente
TIEMPO_ENTRE_MARCAS = 60

# Última persona reconocida
ultima_persona_reconocida = None

# Tiempo del último reconocimiento
ultimo_tiempo_reconocido = 0

# Contador de frames
contador_frames = 0

# FPS del sistema
fps = 0


# ============================================================
# FUNCIÓN PARA MARCAR ASISTENCIA
# ============================================================

def marcar_asistencia_api(iddocente):
    url = "https://tudominio.com/registrar_asistencia.php"

    datos = {
        "token": "MI_TOKEN_SECRETO_123",
        "iddocente": iddocente
    }

    try:
        respuesta = requests.post(url, data=datos, timeout=10)

        if respuesta.status_code != 200:
            print("Error HTTP:", respuesta.status_code)
            print(respuesta.text)
            return None

        resultado = respuesta.json()

        print(resultado.get("mensaje", "Respuesta recibida"))
        return resultado

    except Exception as e:
        print("Error llamando API:", e)
        return None


# ============================================================
# FUNCIÓN PARA CONECTAR CÁMARA
# ============================================================

def conectar_camara():

    # Abrir stream RTSP
    cam = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

    # Reducir buffer para menos delay
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Limitar FPS
    cam.set(cv2.CAP_PROP_FPS, 15)

    # Reducir resolución
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    return cam


# ============================================================
# HILO DE CAPTURA DE VIDEO
# ============================================================

def hilo_captura():

    global frame_actual

    # Conectar cámara
    camara = conectar_camara()

    if not camara.isOpened():
        print("No se pudo abrir la cámara.")
        return

    print("Cámara conectada.")

    fallos = 0

    while True:

        # Leer frame
        ret, frame = camara.read()

        # Si falla lectura
        if not ret or frame is None:

            fallos += 1

            print(f"Error leyendo cámara... {fallos}")

            time.sleep(0.2)

            # Reconectar si hay muchos errores
            if fallos >= MAX_FALLOS_CAMARA:

                print("Reconectando cámara...")

                camara.release()

                time.sleep(2)

                camara = conectar_camara()

                fallos = 0

            continue

        fallos = 0

        # Guardar frame actual
        with lock_frame:
            frame_actual = frame.copy()


# ============================================================
# HILO DE RECONOCIMIENTO FACIAL
# ============================================================

def hilo_reconocimiento():

    global frame_actual
    global frame_procesado
    global contador_frames
    global ultima_persona_reconocida
    global ultimo_tiempo_reconocido

    while True:

        # Esperar si no hay frame
        if frame_actual is None:
            time.sleep(0.01)
            continue

        # Copiar frame actual
        with lock_frame:
            frame = frame_actual.copy()

        contador_frames += 1

        # Saltar frames para mejorar velocidad
        if contador_frames % PROCESAR_CADA_N_FRAMES != 0:

            frame_procesado = frame
            continue

        # ====================================================
        # REDUCIR TAMAÑO DE IMAGEN
        # ====================================================

        frame_pequeno = cv2.resize(
            frame,
            (0, 0),
            fx=ESCALA,
            fy=ESCALA
        )

        # Convertir BGR -> RGB
        rgb = cv2.cvtColor(
            frame_pequeno,
            cv2.COLOR_BGR2RGB
        )

        # ====================================================
        # DETECTAR ROSTROS
        # ====================================================

        ubicaciones = face_recognition.face_locations(
            rgb,
            number_of_times_to_upsample=UPSAMPLE,
            model="hog"
        )

        # Obtener encodings faciales
        codificaciones = face_recognition.face_encodings(
            rgb,
            ubicaciones
        )

        # ====================================================
        # RECORRER CADA ROSTRO
        # ====================================================

        for codificacion, ubicacion in zip(codificaciones, ubicaciones):

            nombre_mostrar = "Desconocido"
            color = (0, 0, 255)

            # ====================================================
            # COMPARAR CON BASE DE DATOS
            # ====================================================

            coincidencias = face_recognition.compare_faces(
                rostros_codificados,
                codificacion,
                tolerance=TOLERANCIA
            )

            # Si encontró coincidencia
            if True in coincidencias:

                # Calcular distancias
                distancias = face_recognition.face_distance(
                    rostros_codificados,
                    codificacion
                )

                # Obtener mejor coincidencia
                indice_mejor = np.argmin(distancias)

                persona = datos_personas[indice_mejor]

                iddocente = persona["iddocente"]
                nombre = persona["nombre"]
                codigo = persona["dni"]

                # ====================================================
                # TEXTO A MOSTRAR
                # ====================================================

                nombre_mostrar = f"{nombre} | {codigo}"

                # Color verde
                color = (0, 255, 0)

                # Guardar último reconocido
                ultima_persona_reconocida = nombre
                ultimo_tiempo_reconocido = time.time()

                # ====================================================
                # MARCAR ASISTENCIA
                # ====================================================

                ahora = time.time()

                if iddocente not in ultimo_marcado:
                    threading.Thread(
                        target=marcar_asistencia_api,
                        args=(iddocente,),
                        daemon=True
                    ).start()

                    ultimo_marcado[iddocente] = ahora

                else:
                    segundos = ahora - ultimo_marcado[iddocente]

                    if segundos >= TIEMPO_ENTRE_MARCAS:
                        threading.Thread(
                            target=marcar_asistencia_api,
                            args=(iddocente,),
                            daemon=True
                        ).start()

                        ultimo_marcado[iddocente] = ahora
            # ====================================================
            # ESCALAR COORDENADAS AL TAMAÑO ORIGINAL
            # ====================================================

            top, right, bottom, left = ubicacion

            top = int(top / ESCALA)
            right = int(right / ESCALA)
            bottom = int(bottom / ESCALA)
            left = int(left / ESCALA)

            # ====================================================
            # DIBUJAR RECTÁNGULO DEL ROSTRO
            # ====================================================

            cv2.rectangle(
                frame,
                (left, top),
                (right, bottom),
                color,
                2
            )

            # ====================================================
            # FONDO DEL NOMBRE
            # ====================================================

            cv2.rectangle(
                frame,
                (left, bottom + 5),
                (right, bottom + 35),
                color,
                cv2.FILLED
            )

            # ====================================================
            # ESCRIBIR NOMBRE DE LA PERSONA
            # ====================================================

            cv2.putText(
                frame,
                nombre_mostrar,
                (left + 5, bottom + 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        # Guardar frame procesado
        frame_procesado = frame


# ============================================================
# INICIAR HILOS
# ============================================================

# Hilo de captura de video
threading.Thread(
    target=hilo_captura,
    daemon=True
).start()

# Hilo de reconocimiento facial
threading.Thread(
    target=hilo_reconocimiento,
    daemon=True
).start()


# ============================================================
# LOOP PRINCIPAL
# ============================================================

print("Sistema iniciado.")
print("Presiona ESC para salir.")

# Variables FPS
fps_inicio = time.time()
fps_contador = 0

while True:

    # Esperar si aún no hay frame
    if frame_procesado is None:
        continue

    frame = frame_procesado.copy()

    # ========================================================
    # CALCULAR FPS
    # ========================================================

    fps_contador += 1

    tiempo_actual = time.time()

    if tiempo_actual - fps_inicio >= 1:

        fps = fps_contador

        fps_contador = 0
        fps_inicio = tiempo_actual

    # ========================================================
    # MOSTRAR FPS EN PANTALLA
    # ========================================================

    if MOSTRAR_FPS:

        cv2.putText(
            frame,
            f"FPS: {fps}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

    # ========================================================
    # MOSTRAR VIDEO
    # ========================================================

    cv2.imshow(
        "Reconocimiento Facial Premium College",
        frame
    )

    # ========================================================
    # SALIR CON ESC
    # ========================================================

    tecla = cv2.waitKey(1)

    if tecla == 27:
        break


# ============================================================
# CERRAR SISTEMA
# ============================================================

cv2.destroyAllWindows()

print("Sistema finalizado.")