from ultralytics import YOLO
import cv2
import requests
import time

API_URL = "http://localhost:8000"
ESPACIO_ID = "S6"
BUILDING_ID = "E1"

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

ultimo_envio = 0
INTERVALO_ENVIO = 5  # segundos entre cada envío a la API

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (640, 480))
    results = model(frame, classes=[0])
    annotated_frame = results[0].plot()
    num_personas = len(results[0].boxes)

    cv2.putText(annotated_frame, f'Personas: {num_personas}',
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    ahora = time.time()
    if ahora - ultimo_envio >= INTERVALO_ENVIO:
        try:
            requests.post(f"{API_URL}/aforo/", json={
                "space_id": ESPACIO_ID,
                "building_id": BUILDING_ID,
                "personas_detectadas": num_personas
            }, timeout=2)
            ultimo_envio = ahora
        except Exception as e:
            print(f"Error enviando a API: {e}")

    cv2.imshow("SIGEU - Control de Aforo", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()