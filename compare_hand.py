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

base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

def detect_landmark(img):

    # img = cv2.imread("./test_yr/peace_person.jpg")
    # cv2.imshow(img)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

    detection_result = detector.detect(mp_image)

    annotated_image = img_rgb.copy()

    all_hand_landmarks = []

    for hand_landmarks in detection_result.hand_landmarks:
        landmarks = []
        landmark_list = landmark_pb2.NormalizedLandmarkList()
        for lm in hand_landmarks:
            landmarks.append([lm.x, lm.y, lm.z])
            landmark = landmark_list.landmark.add()
            landmark.x = lm.x
            landmark.y = lm.y
            landmark.z = lm.z
        all_hand_landmarks.append(np.array(landmarks))

        mp_drawing.draw_landmarks(
            annotated_image,
            landmark_list,
            mp.solutions.hands.HAND_CONNECTIONS
        )

    annotated_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

    # 손 랜드마크 인식 시
    if len(all_hand_landmarks) > 0:
        return all_hand_landmarks, annotated_bgr
    else:
        # 손 랜드마크를 인식할 수 없으면 None 반환
        return None, annotated_bgr
    
def normalize_landmarks(landmarks):
    landmarks = np.array(landmarks)

    # 손목 좌표를 원점으로 이동
    origin = landmarks[0]
    landmarks -= origin
    
    # 손 크기 측정 (손목 ~ 가운데 손가락 끝 거리)
    scale = np.linalg.norm(landmarks[12] - landmarks[0])
    landmarks /= scale
    return landmarks

def mirror_landmarks(landmarks):
    mirrored = landmarks.copy()
    mirrored[:, 0] *= -1 # x 좌표 좌우 반전
    return mirrored

def calculate_similarity(landmarks1, landmarks2):
    # 랜드마크 좌표를 1차원 벡터로 변환 후 유클리드 거리 계산
    diff = landmarks1 - landmarks2
    distance = np.linalg.norm(diff)
    return distance

def match_hand_pose(user_landmarks, emoji_landmarks, threshold=1.0):
    user_norm = normalize_landmarks(user_landmarks)
    emoji_norm = normalize_landmarks(emoji_landmarks)

    emoji_mirror = mirror_landmarks(emoji_norm)

    dist_normal = calculate_similarity(user_norm, emoji_norm)
    dist_mirror = calculate_similarity(user_norm, emoji_mirror)

    dist_min = min(dist_normal, dist_mirror)

    is_match = dist_min < threshold
    return is_match, dist_min

# 1. 이미지에서 사람 손동작 랜드마크 추출 후 저장하는 함수 (csv 저장 예시)
def save_hand_landmarks_to_csv(human_dir, csv_path='hand_landmarks.csv'):
    """
    human_dir: 사람 손동작 사진 폴더 (ex: 'img_hand/human')
    csv_path: 저장할 csv 파일 경로
    """
    import csv
    
    filenames = os.listdir(human_dir)
    landmarks_data = []
    labels = []
    
    for fname in filenames:
        if not re.match(r'.*\.(jpg|png|jpeg)$', fname, re.IGNORECASE):
            continue
        label = re.sub(r'(\_)(\w+)?(\.\w+)$', '', fname)
        
        img_path = os.path.join(human_dir, fname)
        img = cv2.imread(img_path)
        
        hand_landmarks_list, _ = detect_landmark(img)
        if hand_landmarks_list is None:
            print(f'손 인식 실패: {fname}')
            continue
        
        # 각 이미지마다 각각 손동작 중 첫 번째 (or 여러 개 중 하나 선택)
        landmarks = hand_landmarks_list[0].flatten()  # 21 landmarks * 3 coords = 63 길이 배열
        landmarks_data.append(landmarks)
        labels.append(label)
        
    # CSV 저장: 63개 좌표 + one label column
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = [f'coord_{i}' for i in range(len(landmarks_data[0]))] + ['label']
        writer.writerow(header)
        for data, label in zip(landmarks_data, labels):
            writer.writerow(list(data) + [label])
    print(f'csv 저장 완료: {csv_path}')

# 2. CSV 파일에서 손동작 데이터 읽기
def load_hand_landmarks_from_csv(csv_path='hand_landmarks.csv'):
    df = pd.read_csv(csv_path)
    landmarks_list = []
    labels = []
    for _, row in df.iterrows():
        coords = row[:-1].values.astype(float).reshape(21,3)
        label = row[-1]
        landmarks_list.append(coords)
        labels.append(label)
    return landmarks_list, labels

# 3. 사용자의 실제 손동작과 csv로부터 읽은 대표 손동작과 비교해 가장 유사한 label 찾기
def find_best_matching_hand_pose(user_landmarks, landmarks_list, labels, threshold=1.0):
    best_label = None
    best_score = float('inf')
    
    for landmark, label in zip(landmarks_list, labels):
        is_match, score = match_hand_pose(user_landmarks, landmark, threshold)
        if is_match and score < best_score:
            best_score = score
            best_label = label
    return best_label, best_score

# --- 테스트용 예시 ---

if __name__ == "__main__":
    # 1) 한 번만 손동작 사진에서 랜드마크 추출해 csv 저장 (필요시)
    save_hand_landmarks_to_csv('img_hand/human')
    
    # 2) csv에서 손동작 데이터 불러오기
    landmarks_list, labels = load_hand_landmarks_from_csv()
    
    # 단계별로 웹캠 등에서 입력 프레임 받았을 때 사용 예
    frame = cv2.imread('test_yr/peace_person_one_hand.jpg')  # 테스트용 이미지
    user_hands, annotated = detect_landmark(frame)
    if user_hands:
        user_landmarks = user_hands[0]
        best_label, best_score = find_best_matching_hand_pose(user_landmarks, landmarks_list, labels)
        print(f'가장 유사한 손동작: {best_label}, 거리: {best_score}')
        cv2.putText(annotated, f'Match: {best_label}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.imshow('Result', annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()