import sys
import cv2 
import time
import os
#import mediapipe as mp
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget, QMainWindow
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
from game1 import Game1Screen,Resultscreen
from mainmenu  import MainMenu
from game1 import VideoThread 
from compare import calc_similarity 

class EmojiMatchThread(QThread): # VideoThread가 QThread를 상속한다고 가정
    # QImage만 전송합니다.
    change_pixmap_signal = pyqtSignal(QImage)
    
    # VideoThread에 self.running 및 stop() 메서드가 있다고 가정
    
    def __init__(self, camera_index, all_emotion_files, width=400, height=300):
        super().__init__()
        self.camera_index = camera_index
        self.all_emotion_files = all_emotion_files
        self.width = width
        self.height = height
        self.running = True
        
        # ✨ 수정: current_frame_rgb를 OpenCV/NumPy 포맷으로 저장
        self.current_frame_rgb = None 
        
    def stop(self):
        self.running = False
        
    def run(self):
        # cap = cv2.VideoCapture(self.camera_index)
        # 윈도우 환경에서 카메라 인덱스 0이 아닌 경우를 대비해 DSHOW 백엔드 사용
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW) 
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}. Check index or availability.")
            self.running = False
            return
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        while self.running:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # ✨ 업데이트: QImage가 아닌 NumPy 배열(OpenCV RGB 프레임)을 저장
                self.current_frame_rgb = rgb_image.copy() 
                
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                # 웹캠 화면 업데이트를 위한 QImage 변환
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                
                # 웹캠 화면 업데이트 시그널 전송
                self.change_pixmap_signal.emit(p)
                
            self.msleep(50) 
        
        if cap.isOpened():
             cap.release()
        print(f"Camera {self.camera_index} released and EmojiMatchThread terminated.")

# ----------------------------------------------------------------------
# 7. 이모지 매칭 화면 (Game2Screen)
# ----------------------------------------------------------------------
class Game2Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_thread = None
        
        EMOJI_DIR = "img/emoji"
        try:
            self.emotion_files = [
                f for f in os.listdir(EMOJI_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')
            ]
        except FileNotFoundError:
            print(f"Error: 이모지 디렉토리 ({EMOJI_DIR})를 찾을 수 없습니다. 테스트 이모지 사용.")
            self.emotion_files = ["0_placeholder.png"]
            
        self.initUI()
        
    def initUI(self):
        # ... (상단 레이아웃 및 기타 설정은 기존과 동일)
        main_layout = QVBoxLayout()
        
        # 상단 레이아웃
        top_h_layout = QHBoxLayout()
        title = QLabel("✨ AI 이모지 매칭 ✨")
        title.setFont(QFont('Arial', 30, QFont.Bold))
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        back_btn = QPushButton("메인 메뉴로 돌아가기")
        back_btn.setFixedSize(150, 40)
        back_btn.clicked.connect(self.go_to_main_menu)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        top_h_layout.addWidget(back_btn, 0)
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(20)

        # 중앙 콘텐츠 레이아웃
        center_h_layout = QHBoxLayout()
        
        # 좌측: 웹캠 피드
        self.video_label = QLabel('웹캠 피드 (400x300)')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(400, 300)
        self.video_label.setStyleSheet("background-color: black; color: white; border: 3px solid #00f;")

        capture_btn = QPushButton("이모지 추천/캡쳐")
        capture_btn.setFixedSize(150, 40)
        # 버튼 연결: capture_and_match 함수 실행
        capture_btn.clicked.connect(self.capture_and_match)
        
        # 우측: 추천 이모지 및 정보
        match_v_layout = QVBoxLayout()
        self.match_label = QLabel("가장 유사한 이모지")
        self.match_label.setFont(QFont('Arial', 20))
        self.match_label.setAlignment(Qt.AlignCenter)
        
        self.emoji_image = QLabel('이모지 준비 중...')
        self.emoji_image.setAlignment(Qt.AlignCenter)
        self.emoji_image.setFixedSize(200, 200)
        self.emoji_image.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        
        self.similarity_label = QLabel(f'유사도: {0.00: .2f}%')
        self.similarity_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.similarity_label.setAlignment(Qt.AlignCenter)

        match_v_layout.addWidget(self.match_label)
        match_v_layout.addWidget(self.emoji_image)
        match_v_layout.addWidget(self.similarity_label)
        
        center_h_layout.addStretch(1)
        center_h_layout.addWidget(self.video_label)
        center_h_layout.addSpacing(40)
        center_h_layout.addLayout(match_v_layout)
        center_h_layout.addStretch(1)
        center_h_layout.addWidget(capture_btn)
        center_h_layout.addStretch(1)

        main_layout.addLayout(center_h_layout)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

    def update_match(self, image):
        """스레드에서 받은 웹캠 이미지를 업데이트합니다."""
        # 이 함수는 스트리밍 중에만 호출됩니다.
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
            
    def start_stream(self):
        self.stop_stream()
        
        self.video_thread = EmojiMatchThread(
            camera_index=0,
            all_emotion_files=self.emotion_files,
            width=400,
            height=300
        )
        self.video_thread.change_pixmap_signal.connect(self.update_match)
        self.video_thread.start()
        print("이모지 매칭 스트리밍 시작")
        
    def stop_stream(self):
        if self.video_thread and self.video_thread.isRunning():
            try:
                # 시그널 연결 해제
                self.video_thread.change_pixmap_signal.disconnect(self.update_match)
            except Exception:
                pass
            
            self.video_thread.stop()
            self.video_thread.wait() # 스레드가 완전히 종료될 때까지 대기
            self.video_thread = None
            print("이모지 매칭 스트리밍 종료")

    def go_to_main_menu(self):
        self.stop_stream()
        self.stacked_widget.setCurrentIndex(0)

    def capture_and_match(self):
        """버튼 클릭 시 스트리밍을 멈추고 최종 프레임으로 유사도 계산을 수행합니다."""
        if self.video_thread and self.video_thread.isRunning():
            # 1. 현재 스레드의 프레임 데이터 (OpenCV/NumPy) 가져오기
            frame_to_process = self.video_thread.current_frame_rgb
            
            # 2. 스레드 멈추기
            self.stop_stream()
            
            # 3. 가져온 프레임이 유효하면 이모지 매칭 실행
            if frame_to_process is not None:
                self.get_best_emoji(frame_to_process)
            else:
                print("Warning: No frame captured to process.")
        else:
            self.start_stream()

    def get_best_emoji(self, rgb_image):
        from compare import extract_blendshape_scores, compare_blendshape_scores
        import pandas as pd
        import re
        """캡처된 OpenCV 이미지로 유사도를 계산하고 GUI를 업데이트합니다."""
        best_similarity = 0.0
        best_match_emoji = "0_placeholder.png" 
        # 해당 이모지의 표정 특징 값 가져오기
        features = pd.read_csv('faces.csv')
        # emoji에서 라벨 분리
        blend1 = extract_blendshape_scores(rgb_image)
        # 유사도 계산 로직
        for emoji_file in self.emotion_files:
            try:
                label = int(re.sub(r'(\_)(\w+)(\.\w+)?$', '', emoji_file))
                feature = features[features["labels"] == label].values[0]
                blend2 = {features.keys()[i]: feature[i] for i in range(len(features.keys()))}
                similarity = compare_blendshape_scores(blend1, blend2)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_emoji = emoji_file
            except Exception as e:
                # print(f"Similarity calculation failed for {emoji_file}: {e}")
                continue
                
        # GUI 업데이트
        
        # 1. 웹캠 레이블에 캡처된 정지 프레임 표시 (OpenCV -> QPixmap 변환)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # 데이터 복사 없이 QImage 생성 (효율적)
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 비디오 레이블 크기에 맞게 조정
        p = q_img.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(QPixmap.fromImage(p))
        
        # 2. 추천 이모지 이미지 업데이트
        file_path = os.path.join("img/emoji", best_match_emoji)
        pixmap_emoji = QPixmap(file_path)
        if not pixmap_emoji.isNull():
            scaled_pixmap = pixmap_emoji.scaled(
                self.emoji_image.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emoji_image.setPixmap(scaled_pixmap)
            
        # 3. 유사도 텍스트 업데이트
        self.similarity_label.setText(f'유사도: {best_similarity: .2f}%')
        