import cv2
from ultralytics import YOLO
import torch
import numpy as np
from matplotlib import pyplot as plt
import pathlib

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

# model = YOLO("yolov5nu.pt")
model = torch.hub.load("ultralytics/yolov5", "custom", "best.pt").cpu().eval()

def person_in_frame(frame):
    # model을 통해 객체 인식
    results = model(frame, size=160) # 객체 여러 개 감지될 수 있음

    # 감지된 결과를 하나씩 처리
    x_shape = frame.shape[1]
    y_shape = frame.shape[0]
    
    max_area = 0
    target_box = None
    boxes = results.xyxyn[0].numpy() # 해당 필드에는 x1, y1, x2, y2, conf, cls
    for box in boxes:
        x1, y1, x2, y2, conf, cls = box
        x1, x2 = map(int, [x1 * x_shape, x2 * x_shape])
        y1, y2 = map(int, [y1 * x_shape, y2 * x_shape])
        area = (x2-x1) * (y2-y1)

        if area > max_area:
            max_area = area
            target_box = (x1, y1, x2, y2)

    if target_box is not None:
        x1, y1, x2, y2 = target_box
        x1 = max(0, x1 - 15)
        y1 = max(0, y1 - 15)
        x2 = min(x2 + 15, x_shape)
        y2 = min(y2 + 15, y_shape)
        result = frame[y1:y2, x1:x2, :]   # 인식한 객체 박스 크롭
    else:
        return None

    return result