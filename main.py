import os, cv2, pyttsx3, pyvirtualcam, multiprocessing, logging, sys, traceback, json, colorama
from cvzone.PoseModule import PoseDetector
from pyvirtualcam import PixelFormat
from datetime import datetime

from dependencies.Webhook import WebhookBuilder
from dependencies.Facerec import Facerec

colorama.init()

os.makedirs(os.path.join(os.path.dirname(__file__), "logs\\"), exist_ok=True)
logger = logging.getLogger('logger')
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), r"logs\s_cam.log"))
logger.addHandler(fh)
def exc_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)))
sys.excepthook = exc_handler

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)


## SETTINGS:
body_inc = config["camera"]["body_inc"]
face_inc = config["camera"]["face_inc"]
motion_inc = config["camera"]["motion_inc"]
undetected_time = config["camera"]["undetected_time"]
motion_detection = config["settings"]["motion_detection"]
speech = config["settings"]["speech"]
webserver = config["settings"]["webserver"]
notifications = config["settings"]["discord_notifications"]
# url = environ["URL"]  # REMOVE THIS LINE

# Get Discord webhook URL from config.json
url = config.get("discord", {}).get("webhook_url", "")

cam_n = config["camera"]["main"]
fallback_fps = config["camera"]["fallback_fps"]







# text to speech
engine = pyttsx3.init()
def speak(text):
	print(text)
	if speech:
		engine.say(text)
		engine.runAndWait()
	

# mainloop
if __name__ == '__main__':
	multiprocessing.freeze_support()
	cap = cv2.VideoCapture(cam_n)
	cap.set(3, 1280)
	cap.set(4, 720)
	detector = PoseDetector(detectionCon=0.5, trackCon=0.5)
	
	
	webhook = WebhookBuilder(url, os.path.dirname(__file__))
	fr = Facerec()
	fr.load_encoding_images(os.path.join(os.path.dirname(__file__), r".\images"))


	frame_width = int( cap.get(cv2.CAP_PROP_FRAME_WIDTH))
	frame_height =int( cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
	fps = cap.get(cv2.CAP_PROP_FPS)
	if fps == 0.0:
		fps = fallback_fps
	size = (frame_width, frame_height)

	# initializing variables
	motion_c = 0
	face_det = []
	face_c = 0
	body_c = 0
	prev = False
	f_reset = False
	intruder = True
	detected = False
	img_thread = None
	undetected_c = 0
	just_ran = []
	v_path = None
	check_frame_index = 0
	face_list = os.listdir(os.path.join(os.path.dirname(__file__), "images\\"))

	def c_face(facelist: list):
		faces = {}
		for face in facelist:
			try:
				faces[face]+=1
			except KeyError:
				faces[face] = 0
		highest = 0
		highest_n = None
		for val in faces:
			if faces[val] > highest:
				highest = faces[val]
				highest_n = val
			
		return highest_n





	with pyvirtualcam.Camera(frame_width, frame_height, fps, fmt=PixelFormat.BGR) as cam:
		while True:
			check_frame_index+=1
			if check_frame_index == 50:
				check_frame_index = 0
				if face_list != os.listdir(os.path.join(os.path.dirname(__file__), "images\\")):
					face_list = os.listdir(os.path.join(os.path.dirname(__file__), "images\\"))
					fr.load_encoding_images
					fr.load_encoding_images(os.path.join(os.path.dirname(__file__), r".\images"))
					print("Reloaded faces")

			ret1, frame = cap.read()
			ret2, frame2 = cap.read()
			if not ret1 or not ret2:
				print("Error: Could not read frames from camera.")
			else:
				diff = cv2.absdiff(frame, frame2)
				gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
			blur = cv2.GaussianBlur(gray, (5,5), 0)
			_, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
			dilated = cv2.dilate(thresh, None, iterations=3)
			contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
			for contour in contours:
				(x, y, w, h) = cv2.boundingRect(contour)

				if cv2.contourArea(contour) < 5000:
					continue
				cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 225, 225), 1)
				cv2.putText(frame, "Status: {}".format('Movement'), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 225, 225), 2)

			frame = cv2.resize(frame, (1280, 720))
			_, frame2 = cap.read()
			if contours != ():
				motion_c+=1
				motion = True
			else:
				motion = False

			

			## face
			face_locations, face_names = fr.detect_known_faces(frame)
			for face_loc, name in zip(face_locations, face_names):
				if name == "Unknown":
					color = (0, 0, 225)
				else:
					color = (0, 225, 0)
				y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

				cv2.putText(frame, name,(x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, color, 1)
				cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
			if face_locations.size > 0:
				face_c+=1
				face = True
				face_det.append(name)
			else:
				face = False
			
		
			
			## body
			img = detector.findPose(frame, draw=False)
			_, bboxInfo = detector.findPosition(img, bboxWithHands=False)
			if bboxInfo != {}:
				body = True
				body_c+=1
			else:
				body = False
				




			## recorder
			now = datetime.now()
			file_t = now.strftime("%d-%m-%Y_%H-%M-%S")
			path_t = now.strftime("%d-%m-%Y_%H")
			path = os.path.join(os.path.dirname(__file__), fr".\clipped\{path_t}")
			if body or face:
				prev = True
			if body_c == 1 or (face_c == 1 and not f_reset) and "recorder" not in just_ran:
				result = cv2.VideoWriter(fr"{path}\recording_{file_t}.avi",  
							cv2.VideoWriter_fourcc(*'MJPG'),  
							10, size)
				v_path = fr"{path}\recording_{file_t}.avi"
				just_ran.append("recorder")
			if body_c > 5 or face_c > 5:
				result.write(frame)


			## reset
			if not body and not face and not motion and prev:
				undetected_c+=1
			

			if undetected_c == undetected_time:
				if intruder and (body_c > 5 or face_c > 5) and notifications:
					webhook.thread("recording", v_path)
				print("Camera reset.")
				undetected_c = 0
				f_reset = False
				detected = False
				intruder = True
				face_c = 0
				face_det = []
				prev = False
				body_c = 0
				motion_c = 0
				just_ran = []
			
			
			## files
			if not os.path.exists(path):
				os.makedirs(path)
			
			
			## notification
			if motion_detection and motion_c == motion_inc and "motion" not in just_ran:
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Motion detected"], daemon=True).start()
				just_ran.append("motion")
			
			
			if body_c == body_inc and face_c == 0 and "body_1" not in just_ran:
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Person detected initiate face detection"], daemon=True).start()
				cv2.imwrite(rf"{path}\body_{file_t}.jpg", frame)
				just_ran.append("body_1")
			
			
			elif body_c == body_inc*2 and face_c == 0 and "body_2" not in just_ran:
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Initiate face detection now you are already on camera"], daemon=True).start()
				cv2.imwrite(rf"{path}\body_1_{file_t}.jpg", frame)
				just_ran.append("body_2")
			
			
			elif body_c == body_inc*3 and face_c == 0 and "body_3" not in just_ran:
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Face not detected"], daemon=True).start()
				cv2.imwrite(rf"{path}\body_nf_{file_t}.jpg", frame)
				just_ran.append("body_3")
			
			
			elif body_c == body_inc*4 and face_c == 0 and "body_4" not in just_ran:
				cv2.imwrite(rf"{path}\body_nf2_{file_t}.jpg", frame)
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Intruder detected"], daemon=True).start()
					if notifications:
						webhook.thread("intruder", rf"{path}\body_nf2_{file_t}.jpg")
				
				just_ran.append("body_4")
			
			
			elif face_c == 1 and "face_1" not in just_ran:
				if not f_reset:
					multiprocessing.Process(target=speak, args=["Face detected look into the camera for reconition"], daemon=True).start()
				if name == "Unknown":
					cv2.imwrite(rf"{path}\unknown_face_{file_t}.jpg", frame)
				just_ran.append("face_1")
			

			elif face_c == face_inc:
				d_face = c_face(face_det)
				if d_face == "Unknown":
					cv2.imwrite(rf"{path}\verification_{name}_face_{file_t}.jpg", frame)
					if not f_reset:
						multiprocessing.Process(target=speak, args=["Unknown face detected"], daemon=True).start()
						if notifications:
							webhook.thread("unknown", rf"{path}\verification_{name}_face_{file_t}.jpg")
					face_c = 0
					f_reset = True


				elif not detected:
					cv2.imwrite(rf"{path}\verification_{name}_face_{file_t}.jpg", frame)
					if not f_reset or intruder:
						multiprocessing.Process(target=speak, args=[f"Welcome, {name}"], daemon=True).start()
						if notifications:
							webhook.thread("login", name, rf"{path}\verification_{name}_face_{file_t}.jpg")
					face_c = 0
					detected = True
					intruder = False
					f_reset = True
			
			
			if webserver:
				img = cv2.resize(img, (640, 480))
				cam.send(img)
				cam.sleep_until_next_frame()

	cap.release()
	cv2.destroyAllWindows()


