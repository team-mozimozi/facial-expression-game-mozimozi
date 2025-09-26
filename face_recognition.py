import cv2
from ultralytics import YOLO
import torch
import numpy as np
from matplotlib import pyplot as plt

def face_in_frame(frame):

    model = YOLO("yolov5s.pt")

    cap = cv2.VideoCapture(0)

    # model을 통해 객체 인식
    results = model(frame) # 객체 여러 개 감지될 수 있음

    # 감지된 결과를 하나씩 처리
    x_shape = frame.shape[1]
    y_shape = frame.shape[0]

    for result in results:
        boxes = result.boxes # 해당 필드에는 x1, y1, x2, y2, conf, cls

        # 가장 큰 box 찾기(게임에 참가하는 사람 1명)
        max_area = 0
        target_box = None
        target_class = None
        
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2-x1) * (y2-y1)
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            
            if area > max_area and class_name == "person":
                max_area = area
                target_box = (x1, y1, x2, y2)
                target_class = model.names[int(box.cls[0])]

        if target_box is not None:
            x1, y1, x2, y2 = target_box
            # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # 인식한 사람 객체의 얼굴 부분만 잘라내기 
    result = person_to_face(frame)
    if result is False:
        return None
    else:
        frame = result
        # 테스트 코드
        # cv2.imshow("Detected Face", frame)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        return frame
        

def person_to_face(img):
    img_h, img_w = img.shape[:2]

    face_cascade = cv2.CascadeClassifier('./haarcascade_frontalface_default.xml')

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray)

    buffer = 0.1  # 10% 확장   
    height, width = img.shape[:2]
    
    if len(faces)> 0:
        # faces: (x, y, w, h)
        largest = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest
        
        # 확장 계산(경계 내로)
        dw = int(w * buffer / 2)
        dh = int(h * buffer / 2)
        crop_x1 = max(0, x - dw)
        crop_y1 = max(0, y - dh)
        crop_x2 = min(width, x + w + dw)
        crop_y2 = min(height, y + h + dh)

        cropped_img = img[crop_y1:crop_y2, crop_x1:crop_x2, :]
        cv2.resize(cropped_img, dst=cropped_img, fx=img_w/(crop_x2 - crop_x1), fy=img_w/(crop_x2 - crop_x1))
        
        
        return cropped_img
    
    # 얼굴이 없는 경우 원본 이미지 반환
    return False
