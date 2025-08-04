import threading, time, cv2, logging, sys, traceback, os, json, colorama, subprocess
from flask import Response, Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime

colorama.init()

os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
logger = logging.getLogger('logger')
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "w_server.log"))
logger.addHandler(fh)
def exc_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)))
sys.excepthook = exc_handler

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)



outputFrame = None
lock = threading.Lock()
system_status = {
    'security': False,
    'discord_bot': False,
    'webserver': True
}

cap = cv2.VideoCapture(config["camera"]["v_cam"])
app = Flask(__name__)
app.config['SECRET_KEY'] = 'security_system_key'
socketio = SocketIO(app, cors_allowed_origins="*")

time.sleep(2.0)

# Global process references
security_process = None
bot_process = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def get_status():
    global security_process, bot_process
    
    # Update status based on actual process states
    system_status['security'] = security_process is not None and security_process.poll() is None
    system_status['discord_bot'] = bot_process is not None and bot_process.poll() is None
    
    return jsonify(system_status)

@app.route("/api/screenshot", methods=['POST'])
def take_screenshot():
    global outputFrame, lock
    try:
        with lock:
            if outputFrame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = f"screenshot_{timestamp}.jpg"
                filepath = os.path.join(screenshot_dir, filename)
                cv2.imwrite(filepath, outputFrame)
                return jsonify({"success": True, "filename": filename, "path": filepath})
            else:
                return jsonify({"success": False, "error": "No frame available"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/api/get_config", methods=['GET'])
def get_config():
    try:
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
            config_data = json.load(conf_file)
        return jsonify({"success": True, "config": config_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/save_config", methods=['POST'])
def save_config():
    try:
        new_config = request.get_json()
        
        # Validate config structure
        required_keys = ['settings', 'camera']
        for key in required_keys:
            if key not in new_config:
                return jsonify({"success": False, "error": f"Missing required key: {key}"})
        
        # Backup current config
        backup_path = os.path.join(os.path.dirname(__file__), "config_backup.json")
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
            current_config = json.load(conf_file)
        with open(backup_path, "w") as backup_file:
            json.dump(current_config, backup_file, indent=4)
        
        # Save new config
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "w") as conf_file:
            json.dump(new_config, conf_file, indent=4)
        
        return jsonify({"success": True, "message": "Configuration saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/reload_camera", methods=['POST'])
def reload_camera():
    global cap, outputFrame, lock
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
        config = json.load(conf_file)
    try:
        with lock:
            # Release current camera
            if cap:
                cap.release()
            
            # Small delay to ensure camera is released
            time.sleep(1)
            
            # Reinitialize camera
            cap = cv2.VideoCapture(config["camera"]["v_cam"])
            cap.set(3, 1280)  # Width
            cap.set(4, 720)   # Height
            
            # Clear current frame
            outputFrame = None
            
            # Test if camera is working
            ret, test_frame = cap.read()
            if ret:
                return jsonify({"success": True, "message": "Camera reloaded successfully"})
            else:
                return jsonify({"success": False, "error": "Failed to initialize camera"})
                
    except Exception as e:
        return jsonify({"success": False, "error": f"Camera reload failed: {str(e)}"})

@app.route("/api/control/<action>", methods=['POST'])
def system_control(action):
    global security_process, bot_process, system_status
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
        config = json.load(conf_file)
    try:
        if action == "start":
            # Start security system
            if not security_process or security_process.poll() is not None:
                security_process = subprocess.Popen([
                    'python', os.path.join(os.path.dirname(__file__), 'main.py')
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                universal_newlines=True, bufsize=1)
                system_status['security'] = True
                
                # Start log monitoring
                threading.Thread(target=monitor_process_output, 
                               args=(security_process, 'SECURITY SYSTEM'), daemon=True).start()
            
            # Start Discord bot if enabled
            if config["settings"]["discord_bot"]:
                if not bot_process or bot_process.poll() is not None:
                    bot_process = subprocess.Popen([
                        'python', os.path.join(os.path.dirname(__file__), 'bot.py')
                    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    universal_newlines=True, bufsize=1)
                    system_status['discord_bot'] = True
                    
                    threading.Thread(target=monitor_process_output, 
                                   args=(bot_process, 'DISCORD BOT'), daemon=True).start()
            
            return jsonify({"success": True, "message": "System started"})
            
        elif action == "stop":
            # Stop security system
            if security_process and security_process.poll() is None:
                security_process.terminate()
                try:
                    security_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    security_process.kill()
                system_status['security'] = False
            
            # Stop Discord bot
            if bot_process and bot_process.poll() is None:
                bot_process.terminate()
                try:
                    bot_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    bot_process.kill()
                system_status['discord_bot'] = False
            
            return jsonify({"success": True, "message": "System stopped"})
            
        elif action == "restart":
            # Stop first
            system_control("stop")
            time.sleep(2)
            # Then start
            return system_control("start")
            
        else:
            return jsonify({"success": False, "error": "Invalid action"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/get_env", methods=['GET'])
def get_env():
    try:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if not os.path.exists(env_path):
            return jsonify({"success": False, "error": ".env file not found"})
        with open(env_path, "r") as env_file:
            env_content = env_file.read()
        return jsonify({"success": True, "env": env_content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/save_env", methods=['POST'])
def save_env():
    try:
        data = request.get_json()
        env_content = data.get("env")
        if env_content is None:
            return jsonify({"success": False, "error": "Missing 'env' content"})
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_path, "w") as env_file:
            env_file.write(env_content)
        return jsonify({"success": True, "message": ".env file saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/add_user")
def add_user():
    return render_template("add_user.html")

@app.route("/api/add_user", methods=['POST'])
def api_add_user():
    try:
        data = request.get_json()
        name = data.get("name")
        img_data = data.get("image")
        if not name or not img_data:
            return jsonify({"success": False, "error": "Missing name or image"})
        # Decode base64 image
        import base64
        from PIL import Image
        from io import BytesIO
        img_bytes = base64.b64decode(img_data.split(',')[1])
        img = Image.open(BytesIO(img_bytes))
        # Save image
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        os.makedirs(images_dir, exist_ok=True)
        img.save(os.path.join(images_dir, f"{name}.jpg"))
        return jsonify({"success": True, "message": "User added successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/list_users", methods=['GET'])
def list_users():
    try:
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        if not os.path.exists(images_dir):
            return jsonify({"success": True, "users": []})
        users = []
        for filename in os.listdir(images_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                user = os.path.splitext(filename)[0]
                if user:
                    users.append({"name": user})
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/user_image/<username>")
def user_image(username):
    images_dir = os.path.join(os.path.dirname(__file__), "images")
    # Try jpg, jpeg, png in order
    for ext in ["jpg", "jpeg", "png"]:
        filename = f"{username}.{ext}"
        filepath = os.path.join(images_dir, filename)
        if os.path.exists(filepath):
            return send_from_directory(images_dir, filename)
    # If not found, return 404
    return '', 404

@app.route("/api/delete_user", methods=['POST'])
def delete_user():
    try:
        data = request.get_json()
        name = data.get("name")
        if not name:
            return jsonify({"success": False, "error": "Missing user name"})
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        deleted = False
        for ext in ["jpg", "jpeg", "png"]:
            filename = f"{name}.{ext}"
            filepath = os.path.join(images_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted = True
        if deleted:
            return jsonify({"success": True, "message": f"User '{name}' deleted"})
        else:
            return jsonify({"success": False, "error": "User image not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/speak", methods=['POST'])
def api_speak():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"success": False, "error": "No message provided"})
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(message)
        engine.runAndWait()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def monitor_process_output(process, service_name):
    """Monitor process output and send to frontend"""
    try:
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] [{service_name}] {line.strip()}"
                socketio.emit('log', {'data': log_entry})
    except Exception as e:
        error_msg = f"Error monitoring {service_name}: {str(e)}"
        socketio.emit('log', {'data': error_msg})

def getframe():
    global outputFrame, lock
    while True:
        try:
            ret, img = cap.read()
            if ret and img is not None:
                with lock:
                    outputFrame = img
        except Exception as e:
            print(f"Frame capture error: {e}")
        time.sleep(0.033)  # ~30 FPS

def generate():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None:
                continue
            try:
                (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
                if not flag:
                    continue
            except Exception as e:
                print(f"Encoding error: {e}")
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame")

@socketio.on('connect')
def handle_connect():
    emit('log', {'data': '[SYSTEM] Connected to SecureHome Dashboard'})

if __name__ == '__main__':
    # Start frame capture thread
    t = threading.Thread(target=getframe)
    t.daemon = True
    t.start()
    
    # Start the Flask-SocketIO server
    socketio.run(app, host="0.0.0.0", port=8040, debug=False)

cv2.destroyAllWindows()