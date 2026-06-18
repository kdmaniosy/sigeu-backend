from ultralytics import YOLO
import cv2
import requests
import time
import threading

# Variables de configuración
API_URL = "http://localhost:8000"
ESPACIO_ID = "S6"
BUILDING_ID = "E1"


# Cargar modelo YOLOv8 preentrenado (versión pequeña)
model = YOLO("yolov8n.pt")
model.overrides["verbose"] = False

# Variables compartidas
num_personas = 0
ultimo_frame = None
lock = threading.Lock()
ultimo_envio_api = 0
ultimo_envio_frame = 0
INTERVALO_ENVIO_DATOS = 5    # datos de aforo cada 5s
INTERVALO_ENVIO_FRAME = 0.1  # frames cada 100ms (10 FPS en stream)
INTERVALO_DETECCION = 5      # detectar 1 de cada 5 frames


# Funciones para enviar datos al backend
def enviar_datos(personas: int):
    try:
        requests.post(f"{API_URL}/aforo/", json={
            "space_id": ESPACIO_ID,
            "building_id": BUILDING_ID,
            "personas_detectadas": personas
        }, timeout=2)
    except:
        pass

# Función para enviar frames al backend
def enviar_frame(frame_bytes: bytes):
    try:
        requests.post(
            f"{API_URL}/aforo/frame",
            data=frame_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=0.3
        )
    except:
        pass


# Configurar captura de video (ajustar resolución y FPS para mejor rendimiento)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 426)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)
cap.set(cv2.CAP_PROP_FPS, 15)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # buffer mínimo = menos lag

frame_count = 0
ultimo_annotated = None


# Mensaje de inicio
print("✅ SIGEU - Detector de aforo iniciado")
print(f"   Espacio: {ESPACIO_ID} | Edificio: {BUILDING_ID}")
print("   Presiona 'q' para salir\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    ahora = time.time()

    # ─── Detección YOLO (cada N frames) ────────────────
    if frame_count % INTERVALO_DETECCION == 0:
        frame_small = cv2.resize(frame, (320, 240))
        results = model(
            frame_small,
            classes=[0],
            conf=0.45,
            iou=0.45,
            imgsz=320,
            half=False,
            device="cpu",
            verbose=False
        )
        with lock:
            num_personas = len(results[0].boxes)
        ultimo_annotated = cv2.resize(results[0].plot(), (426, 320))

        # Enviar datos de aforo (en hilo separado)
        if ahora - ultimo_envio_api >= INTERVALO_ENVIO_DATOS:
            threading.Thread(
                target=enviar_datos,
                args=(num_personas,),
                daemon=True
            ).start()
            ultimo_envio_api = ahora

    # ─── Frame a mostrar ───────────────────────────────
    display_frame = ultimo_annotated if ultimo_annotated is not None else frame

    with lock:
        personas_mostrar = num_personas

    color = (0, 200, 0) if personas_mostrar < 10 else (0, 165, 255) if personas_mostrar < 20 else (0, 0, 255)
    cv2.putText(display_frame, f"Personas: {personas_mostrar}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    cv2.putText(display_frame, f"{ESPACIO_ID}-{BUILDING_ID}",
                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # ─── Enviar frame al stream (cada 100ms en hilo separado) ──
    if ahora - ultimo_envio_frame >= INTERVALO_ENVIO_FRAME:
        ret2, buffer = cv2.imencode(".jpg", display_frame,
                                    [cv2.IMWRITE_JPEG_QUALITY, 60])
        if ret2:
            threading.Thread(
                target=enviar_frame,
                args=(buffer.tobytes(),),
                daemon=True
            ).start()
        ultimo_envio_frame = ahora

    cv2.imshow("SIGEU - Control de Aforo", display_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("👋 Detector detenido.")