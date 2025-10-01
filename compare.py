import mediapipe as mp
import cv2
import numpy as np
import os, re
import pandas as pd
from person_in_frame import person_in_frame

def extract_blendshape_scores(img):
    """
    주어진 이미지로부터 표정 특징점들을 추출하는 함수
    Argv:
        img (np.ndarray): 웹캠의 frame이나 이미지 파일. (H, W, C)

    Returns:
        List of dict: {특징 이름: 값} 형태의 모든 특징값들을 담은 딕셔너리 리스트
                      만약 받은 사진이 얼굴 사진이 아니라면 None 반환
    """
    # 특징을 추출할 mediapipe의 모델 설정 값 가져오기
    baseoptions = mp.tasks.BaseOptions
    facelandmarker = mp.tasks.vision.FaceLandmarker
    facelandmarkeroptions = mp.tasks.vision.FaceLandmarkerOptions
    visionrunningmode = mp.tasks.vision.RunningMode
    model_path = 'face_landmarker.task'
    options = facelandmarkeroptions(
        base_options=baseoptions(model_asset_path=model_path),
        running_mode=visionrunningmode.IMAGE,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    # face_landmarker.task에 저장된 모델을 불러와 특징 추출에 사용
    with facelandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
        detection_result = landmarker.detect(mp_image)

        # 추출된 표정 특징이 존재하면 blendshape score 반환
        if detection_result.face_blendshapes:
            return detection_result.face_blendshapes[0]
        # 표정 특징이 없으면 None 반환
        else:
            return None
        
def compare_blendshape_scores(blendshape1, blendshape2):
    """
    구한 두 특징점을 비교해 유사도를 반환하는 함수
    Argv:
        blendshape1 (list with dict): extract_blendshape_score함수로 구한 특징값 리스트
        blendshape2 (dict): csv 파일에서 불러온 blendscore 딕셔너리

    Returns:
        Float: 두 특징점들 사이의 유사도. cosine 유사도 사용.
               두 특징값들중 None값이 있거나 공통된 특징이 없을 경우 0 반환
               아닐 경우 코사인 유사도를 %단위로 반환.
    """
    # 두 이미지 중 얼굴 표정이 아닌 이미지가 있다면 0 % 반환
    if blendshape1 is None or blendshape2 is None:
        return 0.0

    score_dict1 = {bs.category_name: bs.score for bs in blendshape1}
    score_dict2 = blendshape2

    common_keys = set(score_dict1.keys()).intersection(set(score_dict2.keys()))
    # 공통된 표정 특징이 존재하지 않으면 0 % 반환
    if not common_keys:
        return 0.0

    # 두 특징들 간의 코사인 유사도 계산
    score_common1 = [score_dict1[key] for key in common_keys]
    score_common2 = [score_dict2[key] for key in common_keys]
    dot_product = sum(a * b for a, b in zip(score_common1, score_common2))
    magnitude1 = sum(a ** 2 for a in score_common1) ** 0.5
    magnitude2 = sum(b ** 2 for b in score_common2) ** 0.5

    similarity = np.clip(dot_product / (magnitude1 * magnitude2), 0, 1) * 100.0
    return similarity

def emoji_to_csv(emoji_dir, human_dir):
    import csv
    img_paths = os.listdir(emoji_dir)
    labels = [re.sub(r'(\_)(\w+)(\.\w+)$', '', f) for f in img_paths]
    img_paths = [re.sub(r'(\.\w+)$', '', f)+".jpg" for f in img_paths]
    print(img_paths)
    for img_path, label in zip(img_paths, labels):
        img = cv2.imread(os.path.join(human_dir, img_path))
        blendshape = extract_blendshape_scores(img)
        scores = [bs.score for bs in blendshape]
        if not os.path.exists("faces.csv"):
            with open("faces.csv", "w", encoding="UTF-8", newline="") as file:
                header = [bs.category_name for bs in blendshape]
                header.extend(["labels"])
                writer = csv.writer(file)
                writer.writerow(header)
        with open("faces.csv", "a", encoding="UTF-8", newline="") as file:
            writer = csv.writer(file)
            scores.extend([label])
            writer.writerow(scores)
            
def calc_similarity(face_img, emoji):
    """
    잘라낸 얼굴 이미지와 비교할 이모지의 표정 유사도를 구하는 함수
    Argv:
        face_img (np.ndarray): 비교할 얼굴 사진
        emoji (str): 비교할 이모지의 파일 이름.
                     ex) 15_sullen.png

    Returns:
        Float: 사진과 이모지 사이의 유사도 값 (%)
    """
    # 해당 이모지의 표정 특징 값 가져오기
    try:
        features = pd.read_csv('faces.csv')
        # emoji에서 라벨 분리
        img2 = person_in_frame(face_img)
        if img2 is None: return 0
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        label = int(re.sub(r'(\_)(\w+)(\.\w+)?$', '', emoji))
        feature = features[features["labels"] == label].values[0]
        blend1 = extract_blendshape_scores(img2)
        blend2 = {features.keys()[i]: feature[i] for i in range(len(features.keys()))}
        
        return compare_blendshape_scores(blend1, blend2)
    except:
        print("유사도 측정 실패")
        return 0

# 테스트 코드. import시 작동하지 않음.
if __name__ == "__main__":
    img1 = cv2.imread("img/human/13_sleepy.jpg")
    emoji = "13_sleepy"
    print(calc_similarity(img1, emoji))