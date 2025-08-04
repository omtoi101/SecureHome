import os
import cv2
import pyttsx3
import pyvirtualcam
import multiprocessing
import logging
import sys
import traceback
import json
import colorama
from cvzone.PoseModule import PoseDetector
from pyvirtualcam import PixelFormat
from datetime import datetime
from dependencies.Webhook import WebhookBuilder
from dependencies.Facerec import Facerec

colorama.init()

# Setup logging
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
logger = logging.getLogger('logger')
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "s_cam.log"))
logger.addHandler(fh)

def exc_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)))

sys.excepthook = exc_handler

class SecurityCamera:
    def __init__(self, config):
        self.config = config
        self.settings = config['settings']
        self.camera_config = config['camera']

        # Initialize core components
        self.face_recognizer = Facerec()
        self.pose_detector = PoseDetector(detectionCon=0.5, trackCon=0.5)
        self.webhook_builder = WebhookBuilder(config.get("discord", {}).get("webhook_url", ""), os.path.dirname(__file__))
        self.tts_engine = pyttsx3.init()

        # Load face encodings
        self.images_dir = os.path.join(os.path.dirname(__file__), "images")
        self.face_recognizer.load_encoding_images(self.images_dir)
        self.face_list = os.listdir(self.images_dir)

        # Video capture setup
        self.cap = cv2.VideoCapture(self.camera_config["main"])
        self.cap.set(3, 1280)
        self.cap.set(4, 720)
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps > 0 else self.camera_config["fallback_fps"]
        self.size = (self.frame_width, self.frame_height)

        # State variables
        self.reset_state()

        self.check_frame_index = 0
        self.video_writer = None

    def reset_state(self):
        print("Camera reset.")
        self.motion_c = 0
        self.face_det = []
        self.face_c = 0
        self.body_c = 0
        self.prev_detection = False
        self.f_reset = False
        self.intruder = True
        self.detected_person = False
        self.undetected_c = 0
        self.just_ran = []
        self.v_path = None
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

    def speak(self, text):
        print(text)
        if self.settings['speech']:
            multiprocessing.Process(target=self._tts_say, args=(text,), daemon=True).start()

    def _tts_say(self, text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def _reload_faces_if_changed(self):
        self.check_frame_index += 1
        if self.check_frame_index == 50:
            self.check_frame_index = 0
            current_face_list = os.listdir(self.images_dir)
            if self.face_list != current_face_list:
                self.face_list = current_face_list
                self.face_recognizer.load_encoding_images(self.images_dir)
                print("Reloaded faces")

    def _c_face(self, facelist: list):
        if not facelist:
            return None
        faces = {}
        for face in facelist:
            faces[face] = faces.get(face, 0) + 1
        return max(faces, key=faces.get)

    def run(self):
        multiprocessing.freeze_support()
        with pyvirtualcam.Camera(self.frame_width, self.frame_height, self.fps, fmt=PixelFormat.BGR) as cam:
            while True:
                self._reload_faces_if_changed()

                ret1, frame = self.cap.read()
                ret2, frame2 = self.cap.read()

                if not ret1 or not ret2:
                    print("Error: Could not read frames from camera.")
                    continue

                motion_detected, contours = self._detect_motion(frame, frame2)
                face_detected, face_locations, face_names = self._detect_faces(frame)
                body_detected, body_bbox = self._detect_bodies(frame)

                self._update_counters(motion_detected, face_detected, body_detected, face_names)
                self._draw_overlays(frame, contours, face_locations, face_names)

                self._handle_recorder(frame, body_detected, face_detected)
                self._handle_notifications(frame, face_names)

                if not any([body_detected, face_detected, motion_detected]) and self.prev_detection:
                    self.undetected_c += 1

                if self.undetected_c >= self.camera_config["undetected_time"]:
                    if self.intruder and (self.body_c > 5 or self.face_c > 5) and self.settings['discord_notifications']:
                        self.webhook_builder.thread("recording", self.v_path)
                    self.reset_state()

                if self.settings['webserver']:
                    # The frame sent to virtual cam should be the one with overlays
                    resized_frame = cv2.resize(frame, (640, 480))
                    cam.send(resized_frame)
                    cam.sleep_until_next_frame()

        self.cap.release()
        cv2.destroyAllWindows()

    def _detect_motion(self, frame1, frame2):
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        valid_contours = [c for c in contours if cv2.contourArea(c) >= 5000]
        return len(valid_contours) > 0, valid_contours

    def _detect_faces(self, frame):
        face_locations, face_names = self.face_recognizer.detect_known_faces(frame)
        return len(face_locations) > 0, face_locations, face_names

    def _detect_bodies(self, frame):
        img = self.pose_detector.findPose(frame, draw=False)
        _, bboxInfo = self.pose_detector.findPosition(img, bboxWithHands=False)
        return bboxInfo != {}, bboxInfo

    def _update_counters(self, motion, face, body, face_names):
        if motion: self.motion_c += 1
        if face:
            self.face_c += 1
            self.face_det.extend(face_names)
        if body: self.body_c += 1

        if body or face:
            self.prev_detection = True
        else:
            self.prev_detection = False

    def _draw_overlays(self, frame, contours, face_locations, face_names):
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 225, 225), 1)
            cv2.putText(frame, "Status: Movement", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 225, 225), 2)

        for face_loc, name in zip(face_locations, face_names):
            color = (0, 0, 225) if name == "Unknown" else (0, 225, 0)
            y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]
            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, color, 1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

    def _handle_recorder(self, frame, body_detected, face_detected):
        now = datetime.now()
        path_t = now.strftime("%d-%m-%Y_%H")
        self.clips_dir = os.path.join(os.path.dirname(__file__), "clipped", path_t)
        os.makedirs(self.clips_dir, exist_ok=True)

        is_recording_trigger = (self.body_c == 1) or (self.face_c == 1 and not self.f_reset)

        if is_recording_trigger and "recorder" not in self.just_ran:
            file_t = now.strftime("%d-%m-%Y_%H-%M-%S")
            self.v_path = os.path.join(self.clips_dir, f"recording_{file_t}.avi")
            self.video_writer = cv2.VideoWriter(
                self.v_path,
                cv2.VideoWriter_fourcc(*'MJPG'),
                10, self.size
            )
            self.just_ran.append("recorder")

        if self.video_writer and (self.body_c > 5 or self.face_c > 5):
            self.video_writer.write(frame)

    def _save_image(self, frame, event_name):
        now = datetime.now()
        file_t = now.strftime("%d-%m-%Y_%H-%M-%S")
        image_path = os.path.join(self.clips_dir, f"{event_name}_{file_t}.jpg")
        cv2.imwrite(image_path, frame)
        return image_path

    def _handle_notifications(self, frame, face_names):
        cam_conf = self.camera_config

        # Motion
        if self.settings['motion_detection'] and self.motion_c == cam_conf['motion_inc'] and "motion" not in self.just_ran:
            if not self.f_reset: self.speak("Motion detected")
            self.just_ran.append("motion")

        # Body
        if self.body_c == cam_conf['body_inc'] and self.face_c == 0 and "body_1" not in self.just_ran:
            if not self.f_reset: self.speak("Person detected, initiate face detection")
            self._save_image(frame, "body")
            self.just_ran.append("body_1")
        elif self.body_c == cam_conf['body_inc'] * 2 and self.face_c == 0 and "body_2" not in self.just_ran:
            if not self.f_reset: self.speak("Initiate face detection now, you are already on camera")
            self._save_image(frame, "body_1")
            self.just_ran.append("body_2")
        elif self.body_c == cam_conf['body_inc'] * 3 and self.face_c == 0 and "body_3" not in self.just_ran:
            if not self.f_reset: self.speak("Face not detected")
            self._save_image(frame, "body_nf")
            self.just_ran.append("body_3")
        elif self.body_c == cam_conf['body_inc'] * 4 and self.face_c == 0 and "body_4" not in self.just_ran:
            if not self.f_reset:
                self.speak("Intruder detected")
                if self.settings['discord_notifications']:
                    img_path = self._save_image(frame, "body_nf2")
                    self.webhook_builder.thread("intruder", img_path)
            self.just_ran.append("body_4")

        # Face
        name = face_names[0] if face_names else ""
        if self.face_c == 1 and "face_1" not in self.just_ran:
            if not self.f_reset: self.speak("Face detected, look into the camera for recognition")
            if name == "Unknown": self._save_image(frame, "unknown_face")
            self.just_ran.append("face_1")
        elif self.face_c == cam_conf['face_inc']:
            d_face = self._c_face(self.face_det)
            if d_face == "Unknown":
                if not self.f_reset:
                    self.speak("Unknown face detected")
                    if self.settings['discord_notifications']:
                        img_path = self._save_image(frame, f"verification_{d_face}_face")
                        self.webhook_builder.thread("unknown", img_path)
                self.f_reset = True
            elif not self.detected_person:
                if not self.f_reset or self.intruder:
                    self.speak(f"Welcome, {d_face}")
                    if self.settings['discord_notifications']:
                        img_path = self._save_image(frame, f"verification_{d_face}_face")
                        self.webhook_builder.thread("login", d_face, img_path)
                self.detected_person = True
                self.intruder = False
                self.f_reset = True
            self.face_c = 0 # Reset face counter after check


if __name__ == '__main__':
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
        config_data = json.load(conf_file)

    camera_system = SecurityCamera(config_data)
    camera_system.run()
