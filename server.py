import threading, time, cv2, threading, logging, sys, traceback, os, json, colorama
from flask import Response, Flask, render_template

colorama.init()

logger = logging.getLogger('logger')
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs\w_server.log"))
logger.addHandler(fh)
def exc_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)))
sys.excepthook = exc_handler

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)

cam_n = config["camera"]["v_cam"]

outputFrame = None
lock = threading.Lock()

cap = cv2.VideoCapture(cam_n)
app = Flask(__name__)
time.sleep(2.0)

@app.route("/")
def index():
    return render_template( "index.html")

def getframe():
    global outputFrame, lock
    while True:
        _, img = cap.read()
        with lock:
            outputFrame = img
    

def generate():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':

    t = threading.Thread(target=getframe)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=8040, debug=True,
        threaded=True, use_reloader=False)
cv2.destroyAllWindows()