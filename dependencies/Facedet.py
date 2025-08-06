import os

import cv2
import face_recognition


# probably doesn't need to be a class lol


class FaceDet:
    def __init__(self, dir):
        self.dir = dir

    def findface(self, imgdir: str, name: str):
        image = cv2.imread(imgdir)

        face_locations = []

        base = image.copy()
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        for top, right, bottom, left in face_locations:
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 1)

        if face_locations != []:
            image_path = os.path.join(self.dir, "images", f"{name}.jpg")
            temp_path = os.path.join(os.getenv("TEMP"), f"{name}_det.jpg")
            cv2.imwrite(image_path, base)
            cv2.imwrite(temp_path, image)
            return (
                True,
                image_path,
                temp_path,
            )
        else:
            return False
