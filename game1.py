import cv2
import random
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer # QTimer 추가
from PyQt5.QtGui import QImage, QPixmap, QFont

# ----------------------------------------------------------------------
# 1. 웹캠 스트림 처리를 위한 별도의 QThread (변동 없음)
# ----------------------------------------------------------------------
class VideoThread(QThread):
    # (코드 내용은 이전과 동일)
    change_pixmap_signal = pyqtSignal(QImage)

    def __init__(self, camera_index, width=320, height=240):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = width
        self.height = height

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
                
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                self.change_pixmap_signal.emit(p)
            
            self.msleep(30)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


# ----------------------------------------------------------------------
# 2. 게임 1 화면 (Game1Screen) - 타이머 로직 추가됨
# ----------------------------------------------------------------------
class Game1Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_threads = []
        
        self.emojis = ["😀", "😂", "😍", "😡", "😢", "😎", "😲", "😴"]
        
        
        # --- 플레이어 정확도 추적 변수-----#
        self.cam1_correct_count =0
        self.cam2_correct_count =0
        
        
        # --- 타이머 관련 변수 초기화 ---
        self.game_timer = QTimer(self)         # QTimer 객체
        self.game_timer.timeout.connect(self.update_timer) # 1초마다 update_timer 호출
        self.total_game_time = 20              # 총 게임 시간 (60초 설정)
        self.time_left = self.total_game_time  # 남은 시간
        
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 1. 상단 영역: 제목, 타이머, 버튼
        top_h_layout = QHBoxLayout()
        
        title = QLabel("1:1 표정 대결")
        title.setFont(QFont('Arial', 30, QFont.Bold))
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 타이머 표시 레이블
        self.timer_label = QLabel(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: black;")

        back_btn = QPushButton("메뉴로 돌아가기")
        back_btn.setFixedSize(150, 40)
        back_btn.clicked.connect(self.go_to_main_menu)
        
        top_h_layout.addWidget(title, 1)  # 타이틀
        top_h_layout.addStretch(1)
        top_h_layout.addWidget(self.timer_label, 1) # 타이머 추가
        top_h_layout.addWidget(back_btn, 0)
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(20)

        # 2. 중앙 영역: 요구 이모티콘 (기존과 동일)
        self.emotion_label = QLabel(random.choice(self.emojis))
        
        self.emotion_label.setFont(QFont('Arial', 150))
        self.emotion_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.emotion_label)
        main_layout.addSpacing(20)
        
        # 3. 하단 영역: 웹캠 자리 및 정확도 (기존과 동일)
        bottom_h_layout = QHBoxLayout()
        # --- 플레이어 1 영역 ---
        player1_v_layout = QVBoxLayout()
        self.player1_video = QLabel('웹캠 1 피드 (320x240)')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(320, 240)
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        self.player1_accuracy = QLabel('CAM1 정확도: 0%')
        self.player1_accuracy.setFont(QFont('Arial', 16))
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_video)
        player1_v_layout.addWidget(self.player1_accuracy)

        # --- 플레이어 2 영역 ---
        player2_v_layout = QVBoxLayout()
        self.player2_video = QLabel('웹캠 2 피드 (320x240)')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(320, 240)
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        self.player2_accuracy = QLabel('CAM2 정확도: 0%')
        self.player2_accuracy.setFont(QFont('Arial', 16))
        self.player2_accuracy.setAlignment(Qt.AlignCenter)
        player2_v_layout.addWidget(self.player2_video)
        player2_v_layout.addWidget(self.player2_accuracy)
        
        bottom_h_layout.addStretch(1)
        bottom_h_layout.addLayout(player1_v_layout)
        bottom_h_layout.addSpacing(40) 
        bottom_h_layout.addLayout(player2_v_layout)
        bottom_h_layout.addStretch(1)

        main_layout.addLayout(bottom_h_layout)
        main_layout.addStretch(1) 
        self.setLayout(main_layout)

    # ----------------------------------------
    # 타이머 업데이트 로직
    # ----------------------------------------
    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"남은 시간: {self.time_left}초")
        
        # 10초 미만일 때 경고 색상 표시
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: black; font-weight: normal;")
            
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_video_streams() # 웹캠도 중지
            self.timer_label.setText("게임 종료! 결과를 확인하세요.")
            
            #CAM1, CAM2 정확도를 계산하고 결과 화면으로 전환
            self.stacked_widget.findChild(ResultScreen).set_results(self.cam1_correct_count, self.cam2_correct_count)
            self.stacked_widget.setCurrentIndex(3) 
            
            
            print("게임 시간이 모두 소진되었습니다.")


    def update_image(self, player_index, image):
        # (기존과 동일)
        pixmap = QPixmap.fromImage(image)
        if player_index == 0:
            self.player1_video.setPixmap(pixmap)
        elif player_index == 1:
            self.player2_video.setPixmap(pixmap)
            
    def start_video_streams(self):
        self.stop_video_streams()
        self.video_threads = []
        self.emotion_label.setText(random.choice(self.emojis))  #게임 시작, 웹캠 스트리밍 될때마다 이모지 선택
        
        
        # 웹캠 시작 (기존과 동일)
        thread1 = VideoThread(camera_index=0)
        thread1.change_pixmap_signal.connect(lambda img: self.update_image(0, img))
        thread1.start()
        self.video_threads.append(thread1)

        thread2 = VideoThread(camera_index=1)
        thread2.change_pixmap_signal.connect(lambda img: self.update_image(1, img))
        thread2.start()
        self.video_threads.append(thread2)
        
        # --- 타이머 재설정 및 시작 ---
        self.time_left = self.total_game_time
        self.timer_label.setText(f"남은 시간: {self.time_left}초")
        self.timer_label.setStyleSheet("color: black;")
        self.game_timer.start(1000) # 1초(1000ms)마다 타이머 업데이트
        
        print("웹캠 스트리밍 및 타이머 작동 시작")

    def stop_video_streams(self):
        # 웹캠 중지 (기존과 동일)
        for thread in self.video_threads:
            if thread.isRunning():
                thread.stop()
        self.video_threads = []
        
        # --- 타이머 중지 ---
        if self.game_timer.isActive():
            self.game_timer.stop()
        
        print("웹캠 스트리밍 및 타이머 작동 종료")

    def go_to_main_menu(self):
        self.stop_video_streams()
        self.stacked_widget.setCurrentIndex(0)
        
