import mediapipe as mp
import cv2
import numpy as np

def extract_blendshape_scores(img):
    """
    주어진 이미지로부터 표정 특징점들을 추출하는 함수
    Argv:
        img (np.ndarray): 웹캠의 frame이나 이미지 파일. (H, W, C)

    Returns:
        detection_result.face_blendshapes[0] (list with dict): {특징 이름: 값} 형태의 모든 특징값들을 담은 딕셔너리 리스트
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
        blendshape1, blendshape2 (list with dict): extract_blendshape_score함수로 구한 특징값 리스트

    Returns:
        similarity (float): 두 특징점들 사이의 유사도. cosine 유사도 사용.
                            두 특징값들중 None값이 있거나 공통된 특징이 없을 경우 0 반환
                            아닐 경우 코사인 유사도를 %단위로 반환.
    """
    # 두 이미지 중 얼굴 표정이 아닌 이미지가 있다면 0 % 반환
    if blendshape1 is None or blendshape2 is None:
        return 0.0

    score_dict1 = {bs.category_name: bs.score for bs in blendshape1}
    score_dict2 = {bs.category_name: bs.score for bs in blendshape2}

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

# 테스트 코드. import시 작동하지 않음.
if __name__ == "__main__":
    img1_path = "angry01_360.jpg"
    img2_path = "angry02_360.jpg"
    image1 = cv2.imread(img1_path)
    image2 = cv2.imread(img2_path)
    blendshape1 = extract_blendshape_scores(image1)
    blendshape2 = extract_blendshape_scores(image2)
    print(compare_blendshape_scores(blendshape1, blendshape2), "%")