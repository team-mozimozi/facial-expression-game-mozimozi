import mediapipe as mp
import cv2
import numpy as np

def extract_blendshape_scores(img):
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
    with facelandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
        detection_result = landmarker.detect(mp_image)

        if detection_result.face_blendshapes:
            return detection_result.face_blendshapes[0]
        else:
            return None
        
def compare_blendshape_scores(blendshape1, blendshape2):
    if blendshape1 is None or blendshape2 is None:
        return 0.0

    score_dict1 = {bs.category_name: bs.score for bs in blendshape1}
    score_dict2 = {bs.category_name: bs.score for bs in blendshape2}

    common_keys = set(score_dict1.keys()).intersection(set(score_dict2.keys()))
    if not common_keys:
        return 0.0 # Not matching

    # Calculate cosine similarity
    score_common1 = [score_dict1[key] for key in common_keys]
    score_common2 = [score_dict2[key] for key in common_keys]
    dot_product = sum(a * b for a, b in zip(score_common1, score_common2))
    magnitude1 = sum(a ** 2 for a in score_common1) ** 0.5
    magnitude2 = sum(b ** 2 for b in score_common2) ** 0.5

    similarity = np.clip(dot_product / (magnitude1 * magnitude2), 0, 1) * 100.0
    return similarity


if __name__ == "__main__":
    img1_path = "angry01_360.jpg"
    img2_path = "angry02_360.jpg"
    image1 = cv2.imread(img1_path)
    image2 = cv2.imread(img2_path)
    blendshape1 = extract_blendshape_scores(image1)
    blendshape2 = extract_blendshape_scores(image2)
    print(compare_blendshape_scores(blendshape1, blendshape2), "%")