import cv2
import random
import os
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer 
from PyQt5.QtGui import QImage, QPixmap, QFont
from compare import calc_similarity 

VIDEO_WIDTH = 610
VIDEO_HEIGTH = 370

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
# 3. 게임 화면 (Game1Screen) - 간격 조절 반영
# ----------------------------------------------------------------------
class Game1Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_threads = []
        
        if os.path.isdir("img/emoji"):
            self.emotion_ids = os.listdir("img/emoji")
        else:
            self.emotion_ids = ["default.png"]
            print("경고: 'img/emoji' 폴더를 찾을 수 없습니다. 기본값 사용.")


        self.p1_score = 0
        self.p2_score = 0
        self.p1_max_similarity = 0.0
        self.p2_max_similarity = 0.0
        self.round = 0
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.total_game_time = 10
        self.time_left = self.total_game_time
        self.is_game_active = False
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0) 
        main_layout.setSpacing(0)                  

        # 상단 Mode1 바 (유지)
        mode1_bar = QLabel("MODE1")
        mode1_bar.setFont(QFont('ARCO', 30, QFont.Bold))
        mode1_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        mode1_bar.setStyleSheet("background-color: #FFE10A; color: #FF5CA7; padding-left: 20px;")
        mode1_bar.setFixedHeight(85)
        mode1_bar.setFixedWidth(1920) 
        main_layout.addWidget(mode1_bar)    
        
        # 타이틀/메뉴 버튼 레이아웃
        top_h_layout = QHBoxLayout()
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 타이머 레이블은 여전히 여기서 인스턴스화
        self.timer_label = QLabel(f"{self.total_game_time}")
        self.timer_label.setFont(QFont('ARCO', 50, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: black;")

        back_btn = QPushButton("메뉴로 돌아가기")
        back_btn.setFixedSize(150, 40)
        back_btn.clicked.connect(self.go_to_main_menu)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        # 타이머는 중앙 컨테이너로 이동했으므로, top_h_layout에서 제거
        top_h_layout.addWidget(back_btn, 0)
        main_layout.addLayout(top_h_layout)
        
        # main_layout의 상단 간격 조절
        main_layout.addSpacing(200) 

        # ------------------------------------------------------------------
        # 이모지 레이블 설정 (유지)
        # ------------------------------------------------------------------
        self.emotion_label = QLabel("표정 이미지 준비 중...")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(240, 240)
        self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;")
        
        # 하단 레이아웃 (웹캠 1 - 중앙 컨테이너 - 웹캠 2)
        bottom_h_layout = QHBoxLayout()
        
        # P1 웹캠 및 정확도
        player1_v_layout = QVBoxLayout()
        self.player1_video = QLabel('웹캠 1 피드')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(VIDEO_WIDTH, VIDEO_HEIGTH)
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        self.player1_accuracy = QLabel(f'P1 정확도: {self.p1_score: .2f}%')
        self.player1_accuracy.setFont(QFont('Jalnan Gothic', 25))
        self.player1_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        
        player1_v_layout.addWidget(self.player1_video)
        player1_v_layout.addWidget(self.player1_accuracy)
        player1_v_layout.addStretch(1) 

        # P2 웹캠 및 정확도
        player2_v_layout = QVBoxLayout()
        self.player2_video = QLabel('웹캠 2 피드')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(VIDEO_WIDTH, VIDEO_HEIGTH)
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        self.player2_accuracy = QLabel(f'P2 정확도: {self.p2_score: .2f}%')
        self.player2_accuracy.setFont(QFont('Jalnan Gothic', 25))
        self.player2_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player2_accuracy.setAlignment(Qt.AlignCenter)
        
        player2_v_layout.addWidget(self.player2_video)
        player2_v_layout.addWidget(self.player2_accuracy)
        player2_v_layout.addStretch(1)

        center_v_layout = QVBoxLayout()
        # 1. 타이머 추가
        center_v_layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        center_v_layout.addSpacing(40)
        center_v_layout.addWidget(self.emotion_label, alignment=Qt.AlignCenter)
        center_v_layout.addStretch(1) 
        # ------------------------------------------------------------------
        
        # bottom_h_layout에 요소들을 순서대로 추가 (유지)
        bottom_h_layout.addStretch(1) 
        bottom_h_layout.addLayout(player1_v_layout)
        bottom_h_layout.addSpacing(100) 
        bottom_h_layout.addLayout(center_v_layout) 
        bottom_h_layout.addSpacing(100) 
        bottom_h_layout.addLayout(player2_v_layout)
        bottom_h_layout.addStretch(1)
        main_layout.addLayout(bottom_h_layout)
        main_layout.addSpacing(50) 
        
        self.setLayout(main_layout)
        
    # 랜덤으로 선택된 이모지 파일명을 받아 QLabel에 표시하는 함수 (유지)
    def set_required_emotion(self, emotion_file):
        self.current_emotion_file = emotion_file
        file_path = os.path.join("img/emoji", emotion_file)

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
        
    # update_timer 함수 (유지)
    def update_timer(self):
        # 1. 게임 시간 카운트 다운
        if self.time_left > 0:
            self.time_left -= 1
            
            # 남은 시간 표시 업데이트
            self.timer_label.setText(f"{self.time_left}")
            
            self.timer_label.setStyleSheet("color: #0AB9FF; font-weight: bold;")
                
            # time_left == 0이 되는 순간 UI 업데이트를 멈춥니다.
            if self.time_left == 0:
                self.game_timer.stop()
                self.is_game_active = False # 화면 업데이트 중지 (스레드는 계속 실행)
                
                # --- 라운드 승패 판정 ---
                if self.p1_max_similarity == self.p2_max_similarity:
                    self.timer_label.setText("무승부입니다. 이모지를 바꾸어 다시 도전하세요!")
                    is_round_clear = False
                else:
                    self.round += 1
                    if self.p1_max_similarity > self.p2_max_similarity: # 플레이어1 승리
                        self.p1_score += 1
                        QTimer.singleShot(3000, self.start_next_round)
                    else: # 플레이어2 승리
                        self.p2_score += 1
                        QTimer.singleShot(3000, self.start_next_round)
                    is_round_clear = True
                    
                # --- 게임/다음 라운드 결정 ---
                if self.round >= 3 and is_round_clear: # 3라운드까지 완료하고 승패가 났을 때
                    self.round = 0
                    self.timer_label.setText("최종 게임 종료! 결과를 확인하세요.")
                    result_screen = self.stacked_widget.findChild(Resultscreen)
                    if result_screen:
                        result_screen.set_results(self.p1_score, self.p2_score)
                    self.p1_score = 0; self.p2_score = 0
                    self.stacked_widget.setCurrentIndex(2)

    # start_next_round 함수 (유지)
    def start_next_round(self):
        # 1. 새 이모지로 설정 및 점수 초기화
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        
        self.player1_accuracy.setText(f'P1 정확도: 0.00%')
        self.player2_accuracy.setText(f'P2 정확도: 0.00%')
        
        self.start_video_streams() # 재시작 함수 재사용

    # update_image_and_score 함수 (유지)
    def update_image_and_score(self, image, score, player_index):
        """VideoThread로부터 이미지, 정확도 점수, 인덱스를 받아 화면을 업데이트합니다."""
        if self.is_game_active:
            pixmap = QPixmap.fromImage(image)
            
            # 점수 업데이트 및 누적
            if player_index == 0:
                self.player1_video.setPixmap(pixmap)
                self.p1_max_similarity = max(self.p1_max_similarity, score)
                self.player1_accuracy.setText(f'P1 정확도: {self.p1_max_similarity: .2f}%')
                
            elif player_index == 1:
                self.player2_video.setPixmap(pixmap)
                self.p2_max_similarity = max(self.p2_max_similarity, score)
                self.player2_accuracy.setText(f'P2 정확도: {self.p2_max_similarity: .2f}%')

                        
    # start_video_streams 함수 (유지)
    def start_video_streams(self):
        # 기존 스레드가 실행 중일 수 있으므로 안전하게 중지 및 정리
        self.stop_video_streams()
        self.video_threads = []
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        self.is_game_active = True

        # 랜덤 이모지 가져오기
        if self.emotion_ids:
            random_emotion_id = random.choice(self.emotion_ids)
            self.set_required_emotion(random_emotion_id)
        
        # 첫 번째 웹캠 스레드
        thread1 = VideoThread(
            camera_index = 0,
            emotion_file = self.current_emotion_file,
            player_index = 0
            )
        thread1.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread1.start()
        self.video_threads.append(thread1)

        # 두 번째 웹캠 스레드
        thread2 = VideoThread(
            camera_index = 1,
            emotion_file = self.current_emotion_file,
            player_index = 1
            )
        thread2.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread2.start()
        self.video_threads.append(thread2)
        
        self.time_left = self.total_game_time
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.setStyleSheet("color: #0AB9FF;")
        self.game_timer.start(1000)
        
        print("웹캠 스트리밍 및 타이머 작동 시작")
    

    # stop_video_streams 함수 (유지)
    def stop_video_streams(self):
        # 1. 타이머 중지
        if self.game_timer.isActive():
            self.game_timer.stop()
        
        # 2. UI 업데이트 플래그 해제
        self.is_game_active = False
            
        # 3. 모든 스레드 안전하게 종료
        for thread in self.video_threads:
            if thread.isRunning():
                try:
                    thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
                except Exception:
                    pass 
                thread.stop()
        self.video_threads = []
        print("웹캠 스트리밍 및 타이머 작동 종료")

    # go_to_main_menu 함수 (유지)
    def go_to_main_menu(self):
        self.stop_video_streams()
        self.stacked_widget.setCurrentIndex(0)