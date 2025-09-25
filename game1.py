import cv2
import random
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer # QTimer 추가
from PyQt5.QtGui import QImage, QPixmap, QFont

# ----------------------------------------------------------------------
# 1. 웹캠 스트림 처리를 위한 별도의 QThread
# ----------------------------------------------------------------------
class VideoThread(QThread):
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
# 2. 게임 결과 화면 (Resultscreen)
# ----------------------------------------------------------------------
class Resultscreen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()
        self.winner_text = ""
        
    def initUI(self):
        self.layout = QVBoxLayout()
        
        self.result_title = QLabel("게임 종료!")
        self.result_title.setFont(QFont('Arial', 40, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        
        self.winner_label = QLabel("결과 계산 중...")
        self.winner_label.setFont(QFont('Arial', 30))
        self.winner_label.setAlignment(Qt.AlignCenter)
        
        back_to_menu_btn = QPushButton("메인 메뉴로 돌아가기")
        back_to_menu_btn.setFixedSize(250, 60)
        back_to_menu_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(back_to_menu_btn)
        h_layout.addStretch(1)
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.winner_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout)
        
        self.setLayout(self.layout)

    def set_results(self, p1_score, p2_score):
        if p1_score > p2_score:
            self.winner_text = f"🎉 P1 승리! (P1: {p1_score}점, P2: {p2_score}점) 🎉"
            self.winner_label.setStyleSheet("color: blue;")
        elif p2_score > p1_score:
            self.winner_text = f"🎉 P2 승리! (P2: {p2_score}점, P1: {p1_score}점) 🎉"
            self.winner_label.setStyleSheet("color: red;")
        else:
            self.winner_text = f"🤝 무승부입니다! (P1: {p1_score}점, P2: {p2_score}점) 🤝"
            self.winner_label.setStyleSheet("color: black;")
            
        self.winner_label.setText(self.winner_text)

# ----------------------------------------------------------------------
# 3. 게임 화면 (Game1Screen)
# ----------------------------------------------------------------------
class Game1Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_threads = []
        
        self.emojis = ["😀", "😂", "😍", "😡", "😢", "😎", "😲", "😴"]
        
        self.p1_correct_count = 0
        self.p2_correct_count = 0
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.total_game_time = 20
        self.time_left = self.total_game_time
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        top_h_layout = QHBoxLayout()
        title = QLabel("1:1 표정 대결")
        title.setFont(QFont('Arial', 30, QFont.Bold))
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.timer_label = QLabel(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: black;")

        back_btn = QPushButton("메뉴로 돌아가기")
        back_btn.setFixedSize(150, 40)
        back_btn.clicked.connect(self.go_to_main_menu)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        top_h_layout.addWidget(self.timer_label, 1)
        top_h_layout.addWidget(back_btn, 0)
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(20)

        self.emotion_label = QLabel(random.choice(self.emojis))
        self.emotion_label.setFont(QFont('Arial', 150))
        self.emotion_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.emotion_label)
        main_layout.addSpacing(20)
        
        bottom_h_layout = QHBoxLayout()
        player1_v_layout = QVBoxLayout()
        self.player1_video = QLabel('웹캠 1 피드 (320x240)')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(320, 240)
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        self.player1_accuracy = QLabel('P1 정확도: 0%')
        self.player1_accuracy.setFont(QFont('Arial', 16))
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_video)
        player1_v_layout.addWidget(self.player1_accuracy)

        player2_v_layout = QVBoxLayout()
        self.player2_video = QLabel('웹캠 2 피드 (320x240)')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(320, 240)
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        self.player2_accuracy = QLabel('P2 정확도: 0%')
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
        
    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"남은 시간: {self.time_left}초")
        
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: black; font-weight: normal;")
            
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_video_streams()
            self.timer_label.setText("게임 종료! 결과를 확인하세요.")
            
            # Note: The following line assumes the correct class name is Resultscreen
            self.stacked_widget.findChild(Resultscreen).set_results(
                self.p1_correct_count, self.p2_correct_count
            )
            self.stacked_widget.setCurrentIndex(2)
            print("게임 시간이 모두 소진되었습니다.")

    def update_image(self, player_index, image):
        pixmap = QPixmap.fromImage(image)
        if player_index == 0:
            self.player1_video.setPixmap(pixmap)
        elif player_index == 1:
            self.player2_video.setPixmap(pixmap)
            
    def start_video_streams(self):
        self.stop_video_streams()
        self.video_threads = []
        self.emotion_label.setText(random.choice(self.emojis))
        
        thread1 = VideoThread(camera_index=0)
        thread1.change_pixmap_signal.connect(lambda img: self.update_image(0, img))
        thread1.start()
        self.video_threads.append(thread1)

        thread2 = VideoThread(camera_index=1)
        thread2.change_pixmap_signal.connect(lambda img: self.update_image(1, img))
        thread2.start()
        self.video_threads.append(thread2)
        
        self.time_left = self.total_game_time
        self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setStyleSheet("color: black;")
        self.game_timer.start(1000)
        
        print("웹캠 스트리밍 및 타이머 작동 시작")

    def stop_video_streams(self):
        for thread in self.video_threads:
            if thread.isRunning():
                thread.stop()
        self.video_threads = []
        
        if self.game_timer.isActive():
            self.game_timer.stop()
        
        print("웹캠 스트리밍 및 타이머 작동 종료")

    def go_to_main_menu(self):
        self.stop_video_streams()
        self.stacked_widget.setCurrentIndex(0)
