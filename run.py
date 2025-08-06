import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from queue import Empty

import colorama
import cv2
from flask import (
    Response,
    Flask,
    render_template,
    jsonify,
    request,
    send_from_directory,
    redirect,
    url_for,
    flash,
)
from flask_socketio import SocketIO, emit
from datetime import datetime
from database import db, User
from auth import (
    get_user_by_username,
    get_user_by_id,
    get_all_users,
    create_user,
    update_user_profile,
    delete_user,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_limiter import Limiter
from functools import wraps
from flask_limiter.util import get_remote_address

colorama.init()

os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
logger = logging.getLogger("logger")
log_path = os.path.join(os.path.dirname(__file__), "logs", "w_server.log")
fh = logging.FileHandler(log_path)
logger.addHandler(fh)


def exc_handler(exctype, value, tb):
    logger.exception("".join(traceback.format_exception(exctype, value, tb)))


sys.excepthook = exc_handler

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)

outputFrame = None
lock = threading.Lock()
system_status = {"security": False, "discord_bot": False, "webserver": True}

app = Flask(__name__)
app.config["SECRET_KEY"] = "a_very_secret_key"  # Changed for security
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --- Auth Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])


@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return User.query.get(int(user_id))


# --- End Auth Setup ---

cap = cv2.VideoCapture(config["camera"]["v_cam"])
socketio = SocketIO(app, cors_allowed_origins="*")

time.sleep(2.0)

# Global process references
security_process = None
bot_process = None
camera_p = None
frame_queue = None


def initialize_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            from auth import create_user

            try:
                create_user("admin", "admin", is_admin=True)
                print("Admin user created.")
            except ValueError as e:
                print(e)


@app.before_request
def create_tables():
    initialize_database()


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        user = get_user_by_username(request.form["username"])
        if user and user.check_password(request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/status")
@login_required
def get_status():
    global security_process, bot_process

    # Update status based on actual process states
    system_status["security"] = security_process is not None and security_process.poll() is None
    system_status["discord_bot"] = bot_process is not None and bot_process.poll() is None

    return jsonify(system_status)


@app.route("/api/screenshot", methods=["POST"])
@login_required
def take_screenshot():
    global outputFrame, lock
    try:
        with lock:
            if outputFrame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_dir = os.path.join(
                    os.path.dirname(__file__), "screenshots"
                )
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
@login_required
def settings():
    return render_template("settings.html")


@app.route("/api/get_config", methods=["GET"])
@login_required
def get_config():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as conf_file:
            config_data = json.load(conf_file)
        return jsonify({"success": True, "config": config_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/save_config", methods=["POST"])
@login_required
def save_config():
    try:
        new_config = request.get_json()

        # Validate config structure
        required_keys = ["settings", "camera"]
        for key in required_keys:
            if key not in new_config:
                return jsonify({"success": False, "error": f"Missing required key: {key}"})

        # Backup current config
        backup_path = os.path.join(os.path.dirname(__file__), "config_backup.json")
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as conf_file:
            current_config = json.load(conf_file)
        with open(backup_path, "w") as backup_file:
            json.dump(current_config, backup_file, indent=4)

        # Save new config
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "w") as conf_file:
            json.dump(new_config, conf_file, indent=4)

        return jsonify(
            {"success": True, "message": "Configuration saved successfully"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def start_camera_process(queue):
    """Starts the camera process."""
    proc = Process(target=camera_process, args=(queue,))
    proc.daemon = True
    proc.start()
    return proc


@app.route("/api/reload_camera", methods=["POST"])
@login_required
def reload_camera():
    """Terminates the existing camera process and starts a new one."""
    global camera_p, frame_queue
    try:
        if camera_p and camera_p.is_alive():
            camera_p.terminate()
            camera_p.join(timeout=2) # Wait for the process to terminate

        # Clear the queue of any old frames
        while not frame_queue.empty():
            try:
                frame_queue.get_nowait()
            except Empty:
                pass

        # Start a new camera process
        camera_p = start_camera_process(frame_queue)

        # Give the camera a moment to initialize
        time.sleep(2)

        if camera_p.is_alive():
             return jsonify({"success": True, "message": "Camera reloaded successfully"})
        else:
             return jsonify({"success": False, "error": "Failed to restart camera process"})

    except Exception as e:
        return jsonify({"success": False, "error": f"Camera reload failed: {str(e)}"})


@app.route("/api/control/<action>", methods=["POST"])
@login_required
def system_control(action):
    global security_process, bot_process, system_status
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
        config = json.load(conf_file)
    try:
        if action == "start":
            # Start security system
            if not security_process or security_process.poll() is not None:
                security_process = subprocess.Popen(
                    ["python", os.path.join(os.path.dirname(__file__), "main.py")],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )
                system_status["security"] = True

                # Start log monitoring
                threading.Thread(
                    target=monitor_process_output,
                    args=(security_process, "SECURITY SYSTEM"),
                    daemon=True,
                ).start()

            # Start Discord bot if enabled
            if config["settings"]["discord_bot"]:
                if not bot_process or bot_process.poll() is not None:
                    bot_process = subprocess.Popen(
                        ["python", os.path.join(os.path.dirname(__file__), "bot.py")],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                    )
                    system_status["discord_bot"] = True

                    threading.Thread(
                        target=monitor_process_output,
                        args=(bot_process, "DISCORD BOT"),
                        daemon=True,
                    ).start()

            return jsonify({"success": True, "message": "System started"})

        elif action == "stop":
            # Stop security system
            if security_process and security_process.poll() is None:
                security_process.terminate()
                try:
                    security_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    security_process.kill()
                system_status["security"] = False

            # Stop Discord bot
            if bot_process and bot_process.poll() is None:
                bot_process.terminate()
                try:
                    bot_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    bot_process.kill()
                system_status["discord_bot"] = False

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


@app.route("/api/get_env", methods=["GET"])
@login_required
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


@app.route("/api/save_env", methods=["POST"])
@login_required
def save_env():
    try:
        data = request.get_json()
        env_content = data.get("env")
        if env_content is None:
            return jsonify({"success": False, "error": "Missing 'env' content"})
        env_path = os.path.join(os.path.dirname(__file__), "bob.txt")
        with open(env_path, "w") as env_file:
            env_file.write(env_content)
        return jsonify({"success": True, "message": ".env file saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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

        img_bytes = base64.b64decode(img_data.split(",")[1])
        img = Image.open(BytesIO(img_bytes))
        # Save image
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        os.makedirs(images_dir, exist_ok=True)
        img.save(os.path.join(images_dir, f"{name}.jpg"))
        return jsonify({"success": True, "message": "User added successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/list_users", methods=["GET"])
@login_required
def list_users():
    try:
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        if not os.path.exists(images_dir):
            return jsonify({"success": True, "users": []})
        users = []
        for filename in os.listdir(images_dir):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                user = os.path.splitext(filename)[0]
                if user:
                    users.append({"name": user})
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/user_image/<username>")
@login_required
def user_image(username):
    images_dir = os.path.join(os.path.dirname(__file__), "images")
    # Try jpg, jpeg, png in order
    for ext in ["jpg", "jpeg", "png"]:
        filename = f"{username}.{ext}"
        filepath = os.path.join(images_dir, filename)
        if os.path.exists(filepath):
            return send_from_directory(images_dir, filename)
    # If not found, return 404
    return "", 404


@app.route("/api/delete_user", methods=["POST"])
@login_required
def api_delete_user():
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


@app.route("/api/speak", methods=["POST"])
@login_required
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


def send_crash_notification(service_name, exit_code):
    """Sends a crash notification to Discord."""
    if config["settings"].get("crash_notifications"):
        from dependencies.Webhook import WebhookBuilder
        webhook_url = config.get("discord", {}).get("webhook_url", "")
        if webhook_url:
            webhook = WebhookBuilder(webhook_url, os.path.dirname(__file__))
            webhook.embed.set_title(f"🚨 {service_name} CRASHED 🚨")
            webhook.embed.set_description(f"The {service_name} process has crashed with exit code: `{exit_code}`")
            webhook.embed.set_color("FF0000")
            webhook.webhook.add_embed(webhook.embed)
            webhook.webhook.execute()

def monitor_process_output(process, service_name):
    """Monitor process output and send to frontend"""
    try:
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] [{service_name}] {line.strip()}"
                socketio.emit("log", {"data": log_entry})
        # Process has finished, check exit code
        exit_code = process.poll()
        if exit_code != 0:
            send_crash_notification(service_name, exit_code)
    except Exception as e:
        error_msg = f"Error monitoring {service_name}: {str(e)}"
        socketio.emit("log", {"data": error_msg})


def camera_process(frame_queue):
    """
    This function runs in a separate process to read frames from the camera.
    This is done to prevent the blocking `read()` call from freezing the web server.
    """
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
        config = json.load(conf_file)

    cap = None
    retry_count = 0
    max_retries = 3

    while True:
        if cap is None or not cap.isOpened():
            if retry_count < max_retries:
                print(f"Attempting to open camera (attempt {retry_count + 1}/{max_retries})...")
                cap = cv2.VideoCapture(config["camera"]["v_cam"])
                if not cap.isOpened():
                    retry_count += 1
                    time.sleep(2)  # Wait before retrying
                    continue
                else:
                    print("Camera opened successfully.")
                    retry_count = 0 # Reset on success
            else:
                print(f"Failed to open camera after {max_retries} attempts. Going into dormant state.")
                time.sleep(60) # Dormant state
                retry_count = 0 # Reset to allow new attempts after dormancy
                continue

        ret, frame = cap.read()
        if ret:
            if frame_queue.full():
                frame_queue.get_nowait()
            frame_queue.put(frame)
            retry_count = 0 # Reset on successful read
        else:
            print("Failed to read frame from camera. Retrying...")
            retry_count += 1
            cap.release()
            cap = None # Force re-initialization

        time.sleep(0.033) # ~30 FPS


def getframe(frame_queue):
    """
    This function runs in a thread to get frames from the queue and update the global outputFrame.
    """
    global outputFrame, lock
    while True:
        try:
            # Use a timeout to prevent blocking indefinitely
            frame = frame_queue.get(timeout=1.0)
            with lock:
                outputFrame = frame
        except Empty:
            # If the queue is empty, just continue. This is expected if the camera process is slow.
            continue
        except Exception as e:
            print(f"Frame queue error: {e}")
        time.sleep(0.01) # Small sleep to prevent busy-waiting


def generate():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None:
                time.sleep(0.1) # Wait for a frame to be available
                continue
            try:
                (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
                if not flag:
                    continue
            except Exception as e:
                print(f"Encoding error: {e}")
                continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + bytearray(encodedImage) + b"\r\n"
        )
        # Yield control to other greenlets
        time.sleep(0.01)


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


# --- Admin Routes ---


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html")


@app.route("/admin/users")
@login_required
@admin_required
def list_admin_users():
    users = get_all_users()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_admin_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        is_admin = "is_admin" in request.form
        try:
            create_user(username, password, is_admin)
            flash(f"User '{username}' created successfully.", "success")
            return redirect(url_for("list_admin_users"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template(
        "admin/edit_user.html", user=None
    )  # Re-use edit template for adding


@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_admin_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("list_admin_users"))

    if request.method == "POST":
        new_username = request.form["username"]
        new_password = request.form.get("password")
        is_admin = "is_admin" in request.form

        try:
            update_user_profile(
                user_id, new_username, new_password if new_password else None, is_admin
            )
            flash(f"User '{new_username}' updated successfully.", "success")
            return redirect(url_for("list_admin_users"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template("admin/edit_user.html", user=user)


@app.route("/admin/users/edit_face/<int:user_id>")
@login_required
@admin_required
def edit_face(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("list_admin_users"))
    return render_template("admin/edit_face.html", user=user)


@app.route("/api/admin/users/edit_face/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def api_edit_face(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"})

    try:
        data = request.form
        img_data = data.get("image_data")
        if not img_data:
            return jsonify({"success": False, "error": "Missing image data"})

        import base64
        from PIL import Image
        from io import BytesIO

        img_bytes = base64.b64decode(img_data.split(",")[1])
        img = Image.open(BytesIO(img_bytes))

        images_dir = os.path.join(os.path.dirname(__file__), "images")
        os.makedirs(images_dir, exist_ok=True)

        # Save the image with the user's ID as the filename
        img.save(os.path.join(images_dir, f"{user.id}.jpg"))

        return jsonify({"success": True, "message": "Face updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/users/delete/<int:user_id>")
@login_required
@admin_required
def delete_admin_user(user_id):
    # Prevent admin from deleting themselves
    if current_user.id == user_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("list_admin_users"))

    if delete_user(user_id):
        flash("User deleted successfully.", "success")
    else:
        flash("User not found.", "danger")
    return redirect(url_for("list_admin_users"))


@socketio.on("connect")
def handle_connect():
    emit("log", {"data": "[SYSTEM] Connected to SecureHome Dashboard"})


if __name__ == "__main__":
    from multiprocessing import Process, Queue
    import atexit

    # Create a queue for communication between processes
    frame_queue = Queue(maxsize=2)

    # Start the camera process using the helper function
    camera_p = start_camera_process(frame_queue)

    # Register a function to terminate the camera process upon exit
    atexit.register(lambda: camera_p.terminate())

    # Start frame capture thread to get frames from the queue
    t = threading.Thread(target=getframe, args=(frame_queue,))
    t.daemon = True
    t.start()

    # Start the Flask-SocketIO server
    socketio.run(app, host="0.0.0.0", port=8040, debug=False)

cv2.destroyAllWindows()
