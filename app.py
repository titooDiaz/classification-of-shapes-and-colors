from flask import Flask, render_template, Response
from flask_sock import Sock
import cv2
import numpy as np
import threading
import time

app = Flask(__name__)
sock = Sock(app)

latest_frame = None
frame_lock = threading.Lock()
frame_event = threading.Event()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame_event.wait(timeout=2)
            with frame_lock:
                frame = None if latest_frame is None else latest_frame.copy()

            if frame is None:
                # Imagen negra de espera mientras se conecta el teléfono
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Esperando camara del celular...", (35, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n")
            time.sleep(0.03)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@sock.route("/ws")
def receive_camera(ws):
    global latest_frame
    while True:
        try:
            message = ws.receive()
            if message is None:
                break
            if isinstance(message, str):
                continue
            data = np.frombuffer(message, dtype=np.uint8)
            frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if frame is not None:
                with frame_lock:
                    latest_frame = frame
                frame_event.set()
        except Exception as exc:
            print("Conexión de cámara cerrada:", exc)
            break

if __name__ == "__main__":
    # Certificado local para permitir getUserMedia en el navegador del celular.
    # Genera cert.pem y key.pem con el comando indicado en README.md.
    app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"),
            threaded=True, debug=False)
