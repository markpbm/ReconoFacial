import os
import shutil
import cv2


CARPETA_PENDIENTES = "fotos_pendientes"
CARPETA_APROBADAS = "fotos"


if not os.path.exists(CARPETA_PENDIENTES):
    print("No hay carpeta fotos_pendientes.")
    exit()


for persona in os.listdir(CARPETA_PENDIENTES):
    carpeta_pendientes_persona = os.path.join(CARPETA_PENDIENTES, persona)

    if not os.path.isdir(carpeta_pendientes_persona):
        continue

    carpeta_aprobadas_persona = os.path.join(CARPETA_APROBADAS, persona)

    if not os.path.exists(carpeta_aprobadas_persona):
        os.makedirs(carpeta_aprobadas_persona)

    archivos = os.listdir(carpeta_pendientes_persona)

    for archivo in archivos:
        if not archivo.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        ruta_pendiente = os.path.join(carpeta_pendientes_persona, archivo)
        imagen = cv2.imread(ruta_pendiente)

        if imagen is None:
            continue

        cv2.imshow(
            f"Pendiente: {persona} - A aprobar / R rechazar / ESC salir",
            imagen
        )

        print(f"\nPersona sugerida: {persona}")
        print(f"Revisando: {archivo}")
        print("Presiona A para aprobar")
        print("Presiona R para rechazar")
        print("Presiona ESC para salir")

        tecla = cv2.waitKey(0)

        if tecla == 27:
            cv2.destroyAllWindows()
            exit()

        elif tecla == ord("a") or tecla == ord("A"):
            ruta_aprobada = os.path.join(carpeta_aprobadas_persona, archivo)
            shutil.move(ruta_pendiente, ruta_aprobada)
            print(f"Aprobada y movida a: {ruta_aprobada}")

        elif tecla == ord("r") or tecla == ord("R"):
            os.remove(ruta_pendiente)
            print("Foto rechazada y eliminada.")


cv2.destroyAllWindows()
print("Revisión terminada.")