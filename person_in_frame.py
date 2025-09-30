import cv2
from ultralytics import YOLO
import torch
import numpy as np
from matplotlib import pyplot as plt

def person_in_frame(frame):

    model = YOLO("yolov5n.pt")

    # model을 통해 객체 인식
    results = model(frame) # 객체 여러 개 감지될 수 있음

    # 감지된 결과를 하나씩 처리
    x_shape = frame.shape[1]
    y_shape = frame.shape[0]

    for result in results:
        boxes = result.boxes # 해당 필드에는 x1, y1, x2, y2, conf, cls
        print(f"Detected boxes count: {len(boxes)}")  # 박스 개수 출력
        
        # 가장 큰 box 찾기(게임에 참가하는 사람 1명)
        max_area = 0
        target_box = None
        
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2-x1) * (y2-y1)
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            
            print(f"Box: ({x1}, {y1}, {x2}, {y2}), class: {class_name}, area: {area}")

            if area > max_area and class_name == "person":
                max_area = area
                target_box = (x1, y1, x2, y2)

    if target_box is not None:
        print(f"Selected box for crop: {target_box}")
        result = frame[target_box[1]:target_box[3], target_box[0]:target_box[2], :]   # 인식한 객체 박스 크롭
    else:
        result = None

    return result
        