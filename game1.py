import cv2
import random
import os
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer # QTimer 추가
from PyQt5.QtGui import QImage, QPixmap, QFont
from compare import calc_similarity 
from face_recognition import person_to_face

# ----------------------------------------------------------------------
# 1. 웹캠 스트림 처리를 위한 별도의 QThread
# ----------------------------------------------------------------------
class VideoThread(QThread):
    change_pixmap_score_signal = pyqtSignal(QImage, float, int)
                                                                                       
     # emoji_filename과 player_index를 추가로 받습니다.
    def __init__(self, camera_index, emotion_file, player_index, width=320, height=240):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = width
        self.height = height
        # 2. 비교할 이모지 파일 이름과 플레이어 인덱스 저장
        self.emotion_file = emotion_file
        self.player_index = player_index

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
                similarity = calc_similarity(rgb_image, self.emotion_file)
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                self.change_pixmap_score_signal.emit(p, similarity, self.player_index)
            self.msleep(50)
        
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
            self.winner_text = f"🎉 P1 승리! (P1: {p1_score:.2f}점, P2: {p2_score:.2f}점) 🎉"
            self.winner_label.setStyleSheet("color: blue;")
        elif p2_score > p1_score:
            self.winner_text = f"🎉 P2 승리! (P2: {p2_score:.2f}점, P1: {p1_score:.2f}점) 🎉"
            self.winner_label.setStyleSheet("color: red;")
        else:
            self.winner_text = f"🤝 무승부입니다! (P1: {p1_score:.2f}점, P2: {p2_score:.2f}점) 🤝"
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
        
        #self.emotion_ids = list(range(24))   #0부터 24까지 ID(0_0.jpg ~ 0_24.jpg)
        #self.current_emotion_id = -1   
        #self.emojis = ["😀", "😂", "😍", "😡", "😢", "😎", "😲", "😴"]
        self.emotion_ids = os.listdir("img/emoji")
        #cv2.imread("img/emoji/"+filename)

        self.p1_score = 0
        self.p2_score = 0
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.total_game_time = 10
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

        #self.emotion_label = QLabel(random.choice(self.emojis))
        self.emotion_label = QLabel("표정 이미지 준비 중...")
        #self.emotion_label.setFont(QFont('Arial', 150))
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(200, 200)
        self.emotion_label.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        
        main_layout.addWidget(self.emotion_label)
        main_layout.addSpacing(20)
        
        bottom_h_layout = QHBoxLayout()
        player1_v_layout = QVBoxLayout()
        self.player1_video = QLabel('웹캠 1 피드 (320x240)')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(320, 240)
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        self.player1_accuracy = QLabel(f'P1 정확도: {self.p1_score: .2f}%')
        self.player1_accuracy.setFont(QFont('Arial', 16))
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_video)
        player1_v_layout.addWidget(self.player1_accuracy)

        player2_v_layout = QVBoxLayout()
        self.player2_video = QLabel('웹캠 2 피드 (320x240)')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(320, 240)
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        self.player2_accuracy = QLabel(f'P2 정확도: {self.p2_score: .2f}%')
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
        
    # 랜덤으로 선택된 이모지 파일명을 받아 QLabel에 표시하는 함수
    def set_required_emotion(self, emotion_file):
        # current_emotion_file 변수에 현재 이모지 파일명을 저장합니다.
        self.current_emotion_file = emotion_file
        file_path = os.path.join("img/emoji", emotion_file)

        pixmap = QPixmap(file_path)
        # 이미지가 로딩되지 않았을 때 디버깅 메시지를 명확히 출력합니다.
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                #Qt.SmoothTransformation
                Qt.FastTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
        
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
                self.p1_score, self.p2_score
            )
            self.stacked_widget.setCurrentIndex(2)
            print("게임 시간이 모두 소진되었습니다.")

    # def update_image(self, player_index, image):
    #     pixmap = QPixmap.fromImage(image)
    #     if player_index == 0:
    #         self.player1_video.setPixmap(pixmap)
    #     elif player_index == 1:
    #         self.player2_video.setPixmap(pixmap)
    
    # 새로 추가/수정: 이미지와 점수를 함께 받아 처리하는 함수
    def update_image_and_score(self, image, score, player_index):
        """VideoThread로부터 이미지, 정확도 점수, 인덱스를 받아 화면을 업데이트합니다."""
        pixmap = QPixmap.fromImage(image)
        
        # 점수 업데이트 및 누적
        if player_index == 0:
            self.player1_video.setPixmap(pixmap)
            self.p1_score = max(self.p1_score, score)
            self.player1_accuracy.setText(f'P1 정확도: {self.p1_score: .2f}%')
            
        elif player_index == 1:
            self.player2_video.setPixmap(pixmap)
            self.p2_score = max(self.p2_score, score)
            self.player2_accuracy.setText(f'P2 정확도: {self.p2_score: .2f}%')

                    
    def start_video_streams(self):
        self.stop_video_streams()
        self.video_threads = []
        #self.emotion_label.setText(random.choice(self.emojis))
        
        # [수정] 랜덤 텍스트 이모지 대신 랜덤 이미지 로드 함수 호출
        random_emotion_id = random.choice(self.emotion_ids)
        self.set_required_emotion(random_emotion_id)
        
        thread1 = VideoThread(
            camera_index=0,
            emotion_file = self.current_emotion_file,
            player_index = 0
            )
        thread1.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread1.start()
        self.video_threads.append(thread1)

        thread2 = VideoThread(
            camera_index=1,
            emotion_file = self.current_emotion_file,
            player_index = 1
            )
        thread2.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread2.start()
        self.video_threads.append(thread2)
        
        self.time_left = self.total_game_time
        self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setStyleSheet("color: black;")
        self.game_timer.start(1000)
        
        print("웹캠 스트리밍 및 타이머 작동 시작")
    

    def stop_video_streams(self):
        # 1. 타이머 중지
        if self.game_timer.isActive():
            self.game_timer.stop()
            
        # 2. 모든 스레드 안전하게 종료
        for thread in self.video_threads:
            if thread.isRunning():
                # CRASH FIX: 스레드 종료 전 시그널 연결을 먼저 끊습니다.
                try:
                    # VideoThread의 시그널 이름(change_pixmap_score_signal)을 사용하여 연결 해제
                    thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
                except Exception:
                    # 이미 연결이 끊어졌거나 다른 문제가 있어도 무시 (안전 장치)
                    pass 
                
                # thread.stop()은 이미 timeout/terminate 로직을 포함하고 있어 안전합니다.
                thread.stop() 
                
        self.video_threads = []
        print("웹캠 스트리밍 및 타이머 작동 종료")

    def go_to_main_menu(self):
        self.stop_video_streams()
        self.stacked_widget.setCurrentIndex(0)