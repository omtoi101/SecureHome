import face_recognition
import cv2, os, json


with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)

cam = config["camera"]["main"]

name = input("enter the name of the person your taking a photo of: ")
video_capture = cv2.VideoCapture(cam)

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
img_num=0
while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()
    base = frame.copy()
    # Only process every other frame of video to save time
    if process_this_frame:
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        #rgb_small_frame = small_frame[:, :, ::-1]
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        #print(face_locations)
        face_names = []

    process_this_frame = not process_this_frame


    # Display the results
    for (top, right, bottom, left) in face_locations:
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 1)


    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord(' '):
        if face_locations != []:
            img_num += 1
            cv2.imwrite(os.path.join(os.path.dirname(__file__), f"images\{name}_photo{img_num}.jpg"), base)
            print("img saved.")
        else:
            print("no face detected")
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()