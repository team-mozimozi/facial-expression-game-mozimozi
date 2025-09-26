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

# ----------------------------------------------------------------------
# 6. 이모지 매칭 스레드 (VideoThread 재활용)
# ----------------------------------------------------------------------
class EmojiMatchThread(VideoThread):
    # change_pixmap_score_signal 대신 (QImage, 추천 이모지 파일명, 최고 유사도)를 전송
    change_pixmap_match_signal = pyqtSignal(QImage, str, float)
    
    def __init__(self, camera_index, all_emotion_files, width=400, height=300):
        # VideoThread의 __init__은 emotion_file, player_index를 요구하므로 더미 값 전달
        super().__init__(camera_index, emotion_file="", player_index=-1, width=width, height=height)
        self.all_emotion_files = all_emotion_files # 모든 이모지 파일 리스트
        
        # NOTE: calc_similarity 함수는 'faces.csv' 파일을 사용하여 이모지 특징을 로드합니다.
        # 이 파일이 프로젝트 루트 디렉토리에 있는지 확인해야 합니다.
        
    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        
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
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                best_similarity = 0.0
                best_match_emoji = "0_placeholder.png" 

                # ✨ 핵심 로직: 모든 이모지와 유사도 비교
                for emoji_file in self.all_emotion_files:
                    try:
                        similarity = calc_similarity(rgb_image, emoji_file)
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match_emoji = emoji_file
                    except Exception as e:
                        # 얼굴 인식 실패 또는 calc_similarity 오류 시 무시
                        # print(f"Similarity calculation failed for {emoji_file}: {e}")
                        continue

                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                
                # ✨ 추천된 이미지, 파일명, 유사도 전송
                self.change_pixmap_match_signal.emit(p, best_match_emoji, best_similarity)
            
            self.msleep(50) 
        
        if cap.isOpened():
             cap.release()
        cap = None
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

        main_layout.addLayout(center_h_layout)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

    def update_match(self, image, emoji_file, similarity):
        """스레드에서 받은 웹캠 이미지, 추천 이모지, 유사도를 업데이트합니다."""
        # 1. 웹캠 이미지 업데이트
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        
        # 2. 추천 이모지 이미지 업데이트
        file_path = os.path.join("img/emoji", emoji_file)
        pixmap_emoji = QPixmap(file_path)
        if not pixmap_emoji.isNull():
            scaled_pixmap = pixmap_emoji.scaled(
                self.emoji_image.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emoji_image.setPixmap(scaled_pixmap)
            
        # 3. 유사도 텍스트 업데이트
        self.similarity_label.setText(f'유사도: {similarity: .2f}%')
            
    def start_stream(self):
        self.stop_stream()
        
        self.video_thread = EmojiMatchThread(
            camera_index=0, # 단일 웹캠 사용 (index 0)
            all_emotion_files=self.emotion_files,
            width=400,
            height=300
        )
        self.video_thread.change_pixmap_match_signal.connect(self.update_match)
        self.video_thread.start()
        print("이모지 매칭 스트리밍 시작")
        
    def stop_stream(self):
        if self.video_thread and self.video_thread.isRunning():
            # ⭐ 안전한 종료를 위해 시그널 연결 해제 후 스레드 종료
            try:
                self.video_thread.change_pixmap_match_signal.disconnect(self.update_match)
            except Exception:
                pass
            
            self.video_thread.stop() # VideoThread의 안전한 stop() 메서드를 사용
            self.video_thread = None
            print("이모지 매칭 스트리밍 종료")

    def go_to_main_menu(self):
        self.stop_stream()
        self.stacked_widget.setCurrentIndex(0)