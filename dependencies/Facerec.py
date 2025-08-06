import face_recognition
import cv2
import numpy as np
import os


class Facerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

    def load_encoding_images(self, users, images_path):
        """
        Load encoding images from a list of user objects.
        :param users: A list of User objects from the database.
        :param images_path: Path to the directory containing face images.
        """
        self.known_face_encodings = []
        self.known_face_names = []

        for user in users:
            image_path = os.path.join(images_path, f"{user.id}.jpg")
            if os.path.exists(image_path):
                try:
                    img = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        encoding = encodings[0]
                        self.known_face_encodings.append(encoding)
                        self.known_face_names.append(user.username)
                except Exception as e:
                    print(f"Error loading encoding for user {user.username}: {e}")

    def detect_known_faces(self, frame):
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # Convert from BGR to RGB
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find all the faces and face encodings in the current frame
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations
        )

        face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding
            )
            name = "Unknown"

            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, face_encoding
            )
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]

            face_names.append(name)

        # Scale back up face locations
        face_locations = np.array(face_locations)
        face_locations = face_locations * 4
        return face_locations.astype(int), face_names
