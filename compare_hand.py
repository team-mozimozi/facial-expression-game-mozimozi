import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2
import cv2
import numpy as np
import os, re
import pandas as pd
from person_in_frame import person_in_frame

mp_drawing = mp.solutions.drawing_utils

def detect_landmark(img):

    # img = cv2.imread("./test_yr/peace_person.jpg")
    # cv2.imshow(img)

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
    detector = vision.HandLandmarker.create_from_options(options)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

    detection_result = detector.detect(mp_image)

    annotated_image = img_rgb.copy()

    for hand_landmarks in detection_result.hand_landmarks:
        landmark_list = landmark_pb2.NormalizedLandmarkList()
        for lm in hand_landmarks:
            landmark = landmark_list.landmark.add()
            landmark.x = lm.x
            landmark.y = lm.y
            landmark.z = lm.z
        mp_drawing.draw_landmarks(
            annotated_image,
            landmark_list,
            mp.solutions.hands.HAND_CONNECTIONS
        )

    annotated_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

    # 손 랜드마크 인식 시
    if annotated_bgr is not None:
        return annotated_bgr
    else:
        # 손 랜드마크를 인식할 수 없으면 None 반환
        return None
    

