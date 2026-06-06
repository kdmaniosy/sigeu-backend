from ultralytics import YOLO
import cv2
import requests
import time
import threading

API_URL = "http://localhost:8000"
ESPACIO_ID = "S6"
BUILDING_ID = "E1"

model = YOLO("yolov8n.pt")
model.overrides["verbose"] = False

num_personas = 0
ultimo_frame = None
lock = threading.Lock()
ultimo_envio = 0
INTERVALO_ENVIO = 5
INTERVALO_DETECCION = 3

def enviar_a_api(personas: int):
    try:
        requests.post(f"{API_URL}/aforo/", json={
            "space_id": ESPACIO_ID,
            "building_id": BUILDING_ID,
            "personas_detectadas": personas
        }, timeout=2)
    except Exception as e:
        print(f"Error enviando a API: {e}")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
cap.set(cv2.CAP_PROP_FPS, 15)

frame_count = 0
ultimo_annotated = None

print("✅ SIGEU - Detector de aforo iniciado")
print(f"   Espacio: {ESPACIO_ID} | Edificio: {BUILDING_ID}")
print("   Presiona 'q' para salir\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    if frame_count % INTERVALO_DETECCION == 0:
        frame_small = cv2.resize(frame, (320, 240))
        results = model(
            frame_small,
            classes=[0],
            conf=0.4,
            iou=0.45,
            imgsz=320,
            half=False,
            device="cpu",
            verbose=False
        )

        with lock:
            num_personas = len(results[0].boxes)

        ultimo_annotated = results[0].plot()

        ahora = time.time()
        if ahora - ultimo_envio >= INTERVALO_ENVIO:
            threading.Thread(
                target=enviar_a_api,
                args=(num_personas,),
                daemon=True
            ).start()
            ultimo_envio = ahora

    display_frame = ultimo_annotated if ultimo_annotated is not None else frame

    with lock:
        personas_mostrar = num_personas

    color = (0, 255, 0) if personas_mostrar < 10 else (0, 165, 255) if personas_mostrar < 20 else (0, 0, 255)

    cv2.putText(display_frame, f"Personas: {personas_mostrar}",
                (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    cv2.putText(display_frame, f"Espacio: {ESPACIO_ID}-{BUILDING_ID}",
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(display_frame, "SIGEU - Control de Aforo",
                (10, display_frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # Guardar frame para el streaming
    # Guardar frame y enviarlo al backend para streaming
    ret2, buffer = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if ret2:
        frame_bytes = buffer.tobytes()
        with lock:
            ultimo_frame = frame_bytes
        # Enviar frame al endpoint del backend
        try:
            requests.post(
                f"{API_URL}/aforo/frame",
                data=frame_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=0.5
            )
        except:
            pass

cap.release()
cv2.destroyAllWindows()
print("👋 Detector detenido.")