import cv2
import numpy as np
from compare_hand import detect_landmark, match_hand_pose

# 이전에 작성한 함수들 (detect_landmark, normalize_landmarks, mirror_landmarks, calculate_similarity, match_hand_pose) 가 포함되어 있다고 가정

# 예시: 12개 이모지 대표 손동작 랜드마크 중 1개 임시 샘플 (실제는 여러 샘플 평균 또는 여러 사진 추출 결과로 대체)
emoji_samples = {
    'peace': np.array([
        [0.5, 0.5, 0],
        [0.52, 0.45, 0],
        # ... 총 21개 좌표 필요, 여기서는 축약함
    ]),
    # 나머지 이모지들 더 추가
}

def main():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 손 랜드마크 추출
        hand_landmarks_list, annotated_image = detect_landmark(frame)
        if hand_landmarks_list is not None:
            for user_landmarks in hand_landmarks_list:
                best_match = None
                best_score = float('inf')
                # 이모지별 비교
                for emoji_name, emoji_landmarks in emoji_samples.items():
                    is_match, score = match_hand_pose(user_landmarks, emoji_landmarks)
                    if is_match and score < best_score:
                        best_score = score
                        best_match = emoji_name

                if best_match:
                    cv2.putText(
                        annotated_image,
                        f'Matched: {best_match}',
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2
                    )

        cv2.imshow('Hand Gesture Recognition', annotated_image)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC 키 누르면 종료
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()