# game3.py 내용 시작
import cv2
import random
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer 
from PyQt5.QtGui import QImage, QPixmap, QFont
from compare import calc_similarity 

# ----------------------------------------------------------------------
# 1. 웹캠 스트림 처리 스레드 (TimeAttack 모드 전용)
# ----------------------------------------------------------------------
class TimeAttackThread(QThread):
    # 이미지와 현재 유사도 점수만 전송
    change_pixmap_score_signal = pyqtSignal(QImage, float)
                                                                                       
    def __init__(self, camera_index, emotion_file, width=400, height=300):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = width
        self.height = height
        # 비교할 현재 이모지 파일 이름
        self.emotion_file = emotion_file

    def set_emotion_file(self, new_emotion_file):
        """실행 중인 스레드의 목표 이모지를 변경합니다."""
        self.emotion_file = new_emotion_file
        
    def run(self):
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
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                # 유사도 계산
                similarity = calc_similarity(rgb_image, self.emotion_file)
                
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                
                # 이미지와 유사도 시그널 전송
                self.change_pixmap_score_signal.emit(p, similarity)
            self.msleep(50)
        
        if cap.isOpened():
             cap.release()
        print(f"TimeAttackThread terminated.")
        

    def stop(self):
        self.running = False
        self.wait()
# ----------------------------------------------------------------------
# 1. 게임 결과창 (Game3Screen)
# ----------------------------------------------------------------------
class Result3screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        
        self.total_text = " "
        self.initUI()
        
    def initUI(self):
        self.layout = QVBoxLayout()  
        self.result_title = QLabel("게임 종료!")
        
        self.total_label = QLabel("결과 계산 중...")
        self.total_label.setFont(QFont('Arial', 30))
        self.total_label.setAlignment(Qt.AlignCenter)
        
        back_to_menu_btn = QPushButton("메인 메뉴로 돌아가기")
        back_to_menu_btn.setFixedSize(250, 60)
        back_to_menu_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(back_to_menu_btn)
        h_layout.addStretch(1)
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.total_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout)
        
        self.setLayout(self.layout)
        
        
    def set_results3(self, total_score):
        self.total_text = f" Result!! (total_score: {total_score:.2f}점) "
        self.total_label.setStyleSheet("color: black;")
            
        self.total_label.setText(self.total_text)
        
        
# ----------------------------------------------------------------------
# 2. 게임 화면 (Game3Screen)
# ----------------------------------------------------------------------
class Game3Screen(QWidget):
    # 게임 종료 시그널 (Resultscreen으로 전환)
    game_finished = pyqtSignal(int) 

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_thread = None
        
        self.EMOJI_DIR = "img/emoji"
        try:
            # 이모지 파일 리스트 로드
            self.emotion_files = [
                f for f in os.listdir(self.EMOJI_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')
            ]
        except FileNotFoundError:
            print(f"Error: 이모지 디렉토리 ({self.EMOJI_DIR})를 찾을 수 없습니다. 테스트 이모지 사용.")
            self.emotion_files = ["0_placeholder.png"]

        self.current_emotion_file = None
        self.total_score = 0
        self.target_similarity = 80.0  # 목표 유사도 (예: 80%)
        self.total_game_time = 10      # 총 게임 시간 (60초)
        self.time_left = self.total_game_time
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # --- 상단 레이아웃 (제목, 점수, 타이머) ---
        top_h_layout = QHBoxLayout()
        title = QLabel("⏰ 타임어택 모드")
        title.setFont(QFont('Arial', 30, QFont.Bold))
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.score_label = QLabel(f"획득 점수: {self.total_score}점")
        self.score_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.score_label.setAlignment(Qt.AlignCenter)
        
        self.timer_label = QLabel(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)

        back_btn = QPushButton("메뉴로 돌아가기")
        back_btn.setFixedSize(150, 40)
        back_btn.clicked.connect(self.go_to_main_menu)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        top_h_layout.addWidget(self.score_label, 1)
        top_h_layout.addWidget(self.timer_label, 1)
        top_h_layout.addWidget(back_btn, 0)
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(20)

        # --- 중앙 레이아웃 (이모지, 웹캠, 유사도) ---
        center_h_layout = QHBoxLayout()
        
        # 1. 목표 이모지
        self.emotion_label = QLabel("표정 이미지 준비 중...")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(200, 200)
        self.emotion_label.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        
        # 2. 웹캠 피드
        self.video_label = QLabel('웹캠 피드 (400x300)')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(400, 300)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        
        # 3. 현재 유사도 및 목표 표시
        v_layout_score = QVBoxLayout()
        self.current_accuracy = QLabel(f'현재 유사도: {0.00: .2f}%')
        self.current_accuracy.setFont(QFont('Arial', 18, QFont.Bold))
        self.current_accuracy.setAlignment(Qt.AlignCenter)
        
        self.target_label = QLabel(f'목표 유사도: {self.target_similarity:.0f}%')
        self.target_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.target_label.setStyleSheet("color: #007bff;")
        self.target_label.setAlignment(Qt.AlignCenter)
        
        v_layout_score.addStretch(1)
        v_layout_score.addWidget(self.current_accuracy)
        v_layout_score.addWidget(self.target_label)
        v_layout_score.addStretch(1)

        center_h_layout.addStretch(1)
        center_h_layout.addWidget(self.emotion_label)
        center_h_layout.addSpacing(40)
        center_h_layout.addWidget(self.video_label)
        center_h_layout.addSpacing(40)
        center_h_layout.addLayout(v_layout_score)
        center_h_layout.addStretch(1)

        main_layout.addLayout(center_h_layout)
        main_layout.addStretch(1) 
        self.setLayout(main_layout)
        
    def set_next_emotion(self):
        """랜덤으로 다음 이모지를 설정하고 스레드를 업데이트합니다."""
        if not self.emotion_files:
            return 
            
        # 기존 이모지 제외하고 새로운 이모지 선택
        available_emotions = [f for f in self.emotion_files if f != self.current_emotion_file]
        if not available_emotions:
            # 모든 이모지를 다 썼다면 리스트를 리셋합니다. (선택 사항)
            available_emotions = self.emotion_files
            
        self.current_emotion_file = random.choice(available_emotions)
        file_path = os.path.join(self.EMOJI_DIR, self.current_emotion_file)

        # 1. QLabel에 이모지 이미지 표시
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {self.current_emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
            
        # 2. 웹캠 스레드에 목표 파일명 업데이트
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.set_emotion_file(self.current_emotion_file)
            print(f"새로운 목표 이모지 설정: {self.current_emotion_file}")

    def update_timer(self):
        """1초마다 타이머를 업데이트하고 게임 종료를 확인합니다."""
        self.time_left -= 1
        self.timer_label.setText(f"남은 시간: {self.time_left}초")
        
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: black; font-weight: normal;")
            
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_stream()
            self.timer_label.setText("게임 종료!")
            #QMessageBox.information(self, "게임 종료", f"총 점수: {self.total_score}점!")
            
            # 메인 메뉴로 돌아가거나 결과 화면이 있다면 결과 화면으로 전환
            # game3 결과창 load
            self.stacked_widget.findChild(Result3screen).set_results3(
                self.total_score
            )
            self.stacked_widget.setCurrentIndex(5)
            
            print("게임 시간이 모두 소진되었습니다.")


    def update_image_and_score(self, image, score):
        """VideoThread로부터 이미지와 유사도 점수를 받아 화면을 업데이트합니다."""
        
        # 1. 웹캠 피드 업데이트
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        
        # 2. 유사도 표시 업데이트
        self.current_accuracy.setText(f'현재 유사도: {score: .2f}%')
        
        # 3. 목표 달성 확인 및 다음 이모지로 전환
        if score >= self.target_similarity:
            # 점수 획득
            self.total_score += 1 
            self.score_label.setText(f"획득 점수: {self.total_score}점")
            
            # 다음 이모지 설정 (새로운 목표)
            self.set_next_emotion()
            
            # 목표 달성 시 시각적 피드백
            self.video_label.setStyleSheet("border: 3px solid #0f0; background-color: black; color: white;")
            QTimer.singleShot(200, lambda: self.video_label.setStyleSheet("background-color: black; color: white;")) # 0.2초 후 원래대로 복귀


    def start_stream(self):
        """스트리밍을 시작하고 게임 타이머를 리셋합니다."""
        self.stop_stream()
        
        # 초기화
        self.total_score = 0
        self.score_label.setText(f"획득 점수: {self.total_score}점")
        
        # 1. 비디오 스레드 시작
        # 스레드 생성 시 초기 이모지 설정을 위해 set_next_emotion 호출
        self.set_next_emotion() 
        
        # TimeAttackThread 생성 시에는 current_emotion_file이 설정되어 있어야 합니다.
        self.video_thread = TimeAttackThread(
            camera_index=0, # 타임어택은 1인 모드이므로 보통 0번 카메라 사용
            emotion_file=self.current_emotion_file,
            width=400,
            height=300
        )
        self.video_thread.change_pixmap_score_signal.connect(self.update_image_and_score)
        self.video_thread.start()
        
        # 2. 타이머 시작
        self.time_left = self.total_game_time
        self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setStyleSheet("color: black;")
        self.game_timer.start(1000)
        
        print("타임어택 스트리밍 및 타이머 작동 시작")

    def stop_stream(self):
        """타이머와 웹캠 스레드를 안전하게 종료합니다."""
        if self.game_timer.isActive():
            self.game_timer.stop()
            
        if self.video_thread and self.video_thread.isRunning():
            try:
                self.video_thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
            except Exception:
                pass 
            
            self.video_thread.stop()
            self.video_thread.wait() 
            self.video_thread = None
            
        print("타임어택 스트리밍 및 타이머 작동 종료")

    def go_to_result_screen(Qwidget):
        result_screen = self.stacked_widget.widget(5) 
        
        
        
        
        
    def go_to_main_menu(self):
        self.stop_stream()
        self.stacked_widget.setCurrentIndex(0)

# game3.py 내용 끝