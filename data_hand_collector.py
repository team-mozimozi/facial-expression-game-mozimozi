import cv2
import mediapipe as mp
import numpy as np
import os

# MediaPipe 설정 (손의 모양 추출)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands = 1,
    min_detection_confidence=0.5,
    min_tracking_confidence = 0.5
)

# 모양(shape) 특징 추출 함수: 관절 각도 계산
def calculate_joint_angles(joint):
    """
    손 랜드마크 좌표(21개)로부터 관절 사이의 벡터 정규화
    인접한 벡터 간의 각도를 계산하여 손의 모양을 특징화
    """

    v1_indices = [0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19]
    v2_indices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

    v1 = joint[v1_indices, :]
    v2 = joint[v2_indices, :]

    v = v2 - v1 # 20개의 뼈대 벡터

    # 벡터 정규화(크기를 1로 만듦)
    v = v / np.linalg.norm(v, axis=1)[:, np.newaxis]

    angle_v1_indices = [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18]
    angle_v2_indices = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19]

    # 내적 후 arccos으로 각도 계산(15개 관절 각도)
    angle = np.arccos(np.einsum('nt,nt->n',
        v[angle_v1_indices, :],
        v[angle_v2_indices, :]                 
    ))
    angle = np.degrees(angle)
    return angle

# 데이터 수집 및 저장
def collect_and_save_data(image_dir, output_csv):
    """
    지정된 디렉토리의 이미지에서 손 각도를 추출하고 CSV로 저장
    파일 이름의 첫 번째 숫자를 라벨로 사용
    """
    all_data = []

    # 디렉토리 내 파일 목록 순회
    for filename in os.listdir(image_dir):
        if filename.endswith(('.jpg', '.jpeg', '.png')): # 이미지 파일만 처리

            # 파일 이름에서 라벨 번호 추출
            try:
                label = int(filename.split('_')[0])
            except ValueError:
                print(f"경고: 파일 이름 '{filename}'에서 라벨 번호를 추출할 수 없습니다. 건너뜁니다.")
                continue

            image_path = os.path.join(image_dir, filename)
            img = cv2.imread(image_path)

            if img is None:
                print(f"경고: 이미지를 읽을 수 없습니다: {image_path}")
                continue

            # MediaPipe로 손 랜드마크 추출
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            result = hands.process(img_rgb)

            # 각도(특징) 추출 및 데이터 저장
            if result.multi_hand_landmarks:
                hand_landmarks = result.multi_hand_landmarks[0]

                joint = np.zeros((21, 3))
                for j, lm in enumerate(hand_landmarks.landmark):
                    # 랜드마크 좌표를 추출
                    joint[j] = [lm.x, lm.y, lm.z]

                angles = calculate_joint_angles(joint) # 15개의 각도 벡터

                # 각도 벡터(15개) 뒤에 라벨(1개)를 붙여 하나의 데이터 행을 만듦
                data_row = np.append(angles, label)
                all_data.append(data_row)
                print(f"처리 완료: {filename} -> 라벨 {label}. (총 {len(all_data)}개 데이터)")
            else:
                print(f"경고: {filename}에서 손을 인식하지 못 했습니다. 건너 뜁니다.")

    if all_data:
        all_data_np = np.array(all_data, dtype=np.float32)
        # 소수점 4자리까지, 쉼표(,)를 구분자로 저장
        np.savetxt(output_csv, all_data_np, delimiter=',', fmt='%.4f')
        print(f"\n===========================================")
        print(f"성공적으로 '{output_csv}' 파일에 데이터를 저장했습니다. 총 {len(all_data)}개 행")
    else:
        print("\n처리된 유효한 손 제스처 데이터가 없습니다. CSV 파일 생성하지 않습니다.")

if __name__ == '__main__':
    IMAGE_DIR = './img_hand/human'
    OUTPUT_CSV = 'data_hand.csv'

    collect_and_save_data(IMAGE_DIR, OUTPUT_CSV)