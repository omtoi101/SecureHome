import face_recognition, cv2, os


#probably doesn't need to be a class lol

class FaceDet:
    def __init__(self, dir):
        self.dir = dir
    def findface(self, imgdir: str, name: str):
        image = cv2.imread(imgdir)

        face_locations = []

        base = image.copy()
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 1)


        if face_locations != []:
            cv2.imwrite(os.path.join(self.dir, fr"images\{name}.jpg"), base)
            cv2.imwrite(os.getenv("TEMP") + fr"\{name}_det.jpg", image)
            return True, os.path.join(self.dir, fr"images\{name}.jpg"), os.getenv("TEMP") + fr"\{name}_det.jpg"
        else:
            return False