# (기존 import 및 클래스 정의 유지)
import cv2
import random
import os
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor, QIcon
from compare import calc_similarity
import numpy as np
from mainmenu import flag

# ClickableLabel 클래스
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# 웹캠 처리를 위한 QThread 클래스
class VideoThread(QThread):
    change_pixmap_score_signal = pyqtSignal(QImage, float, int)
                                        
    # 비교할 emoji 파일이름과 player_index를 받음
    def __init__(self, camera_index, emotion_file, player_index, width=flag["VIDEO_WIDTH"], height=flag["VIDEO_HEIGHT"]):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = width
        self.height = height
        self.emotion_file = emotion_file
        self.player_index = player_index

        # 추론 프레임 간격 증가
        self.frame_count = 0
        self.inference_interval = 3  # 3프레임당 1회 추론
        self.similarity = 0

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
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                self.frame_count += 1
                if self.frame_count % self.inference_interval == 1:
                    self.similarity = calc_similarity(frame, self.emotion_file)
                    self.frame_count = 0
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                self.change_pixmap_score_signal.emit(p, self.similarity, self.player_index)
            self.msleep(1)
        
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
        self.layout.addSpacing(30) 
        
        self.result_title = QLabel("게임 종료!")
        self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        
        self.winner_label = QLabel("결과 계산 중...")
        self.winner_label.setFont(QFont('Jalnan 2', 60))
        self.winner_label.setAlignment(Qt.AlignCenter)
        
        # "메인 메뉴로 돌아가기" 버튼을 이미지로 변경 및 위치 조정
        back_to_menu_button = ClickableLabel()
        back_to_menu_button.clicked.connect(self.main_menu_button)
        
        exit_pixmap = QPixmap(flag['MAIN_BUTTON_IMAGE'])
        if not exit_pixmap.isNull():
            back_to_menu_button.setPixmap(exit_pixmap)
            back_to_menu_button.setFixedSize(exit_pixmap.size()) # 이미지 크기에 맞게 설정
            back_to_menu_button.setFixedSize(250, 60)
        else:
            back_to_menu_button.setText("메인 메뉴로 돌아가기")
            back_to_menu_button.setFixedSize(250, 60) # 기본 크기
            back_to_menu_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;")
            print("경고: 'design/exit.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        h_layout = QHBoxLayout()
        h_layout.addSpacing(1) # 좌측에 공간을 추가하여 버튼을 오른쪽으로 밈
        h_layout.addWidget(back_to_menu_button)
        h_layout.addSpacing(1) # 우측 여백
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.winner_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout) # 하단 레이아웃 추가
        self.layout.addSpacing(20) # 하단 여백 추가

        self.setLayout(self.layout)

    def set_results(self, p1_score, p2_score):
        if p1_score > p2_score:
            self.winner_text = f"🎉 PLAYER 1 승리! 🎉 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: blue;")
        elif p2_score > p1_score:
            self.winner_text = f"🎉 PLAYER 2 승리! 🎉 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: blue;")
        else:
            self.winner_text = f"🤝 무승부입니다! 🤝 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: black;")
            
        self.winner_label.setText(self.winner_text)

    def main_menu_button(self):
        self.stacked_widget.setCurrentIndex(0)
        return

# ----------------------------------------------------------------------
# 3. 게임 화면 (Game1Screen) - 간격 조절 반영 및 스코어보드 추가
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
        
        # 새로운 이미지 스코어보드 레이블 리스트 초기화
        self.p1_score_images = []
        self.p2_score_images = []
        # 최대 라운드 수 (점수 이미지 개수) 정의
        self.MAX_ROUNDS = 3 # 3점 선취승을 의미
        
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
        
        # 상단 Mode1 바
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
        self.timer_label.setFont(QFont('Jalnan 2', 45))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: black;")
        # 초기에는 타이머를 숨깁니다.
        self.timer_label.hide() 

        self.back_btn = QPushButton("", self)
        self.back_btn.setGeometry(flag['BUTTON_EXIT_X'], flag['BUTTON_EXIT_Y'],
                                  flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'])

        # 버튼 색상 및 스타일 설정
        # 이 스타일은 모든 QPushButton에 기본적으로 적용됩니다.
        style = f"""
            QPushButton {{
                background-color: "transparent"; /* 배경색 사용 */
                color: #343a40;
                border-radius: 58px; /* 테두리 반경 사용 */
                font-family: 'Jalnan Gothic', 'Arial', sans-serif;
                font-size: 20pt; /* 폰트 크기 사용 */
                font-weight: light;
            }}
            QPushButton:hover {{
                background-color: #8FFF84B3; /* 마우스 오버 시 (메인 버튼 전용) */
                color: #8f343a40;
            }}
            QPushButton:pressed {{
                background-color: #8FFF84B3; /* 클릭 시 (메인 버튼 전용) */
                color: #8f343a40;
            }}
        """
        self.back_btn.setStyleSheet(style)
        # "메뉴로 돌아가기" 버튼을 이미지로 변경
        self.back_btn.clicked.connect(self.go_to_main_menu)

        # *** 우측 하단 버튼 스타일 분리를 위한 고유 이름 설정 ***
        self.back_btn.setObjectName("BottomRightIcon")
        
        # 아이콘 이미지 설정
        icon_path = flag['MAIN_BUTTON_IMAGE']
        icon_pixmap = QPixmap(icon_path)
        
        # QPixmap을 QIcon으로 변환하여 버튼에 설정
        icon_size = QSize(flag['BUTTON_EXIT_WIDTH'] - flag['BUTTON_EXIT_MARGIN'], flag['BUTTON_EXIT_HEIGHT'] - flag['BUTTON_EXIT_MARGIN'])
        scaled_icon = icon_pixmap.scaled(
            icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.back_btn.setIcon(QIcon(scaled_icon))
        self.back_btn.setIconSize(scaled_icon.size())

        # *** 우측 하단 버튼에 대한 고유 스타일시트 적용 ***
        # Object Name을 사용하여 기본 QPushButton 스타일을 덮어씁니다.
        unique_style = f"""
            QPushButton#BottomRightIcon {{
                background-color: transparent; /* 기본 상태: 투명 유지 */
                border-radius: 20px;
                border: none;
                color: transparent; /* 텍스트는 없으므로 투명하게 설정 */
            }}
            QPushButton#BottomRightIcon:hover {{
                background-color: rgba(255, 255, 255, 0.2); /* 마우스 오버 시: 약간의 투명한 흰색 배경 */
            }}
            QPushButton#BottomRightIcon:pressed {{
                background-color: rgba(255, 255, 255, 0.4); /* 클릭 시: 더 진한 투명한 흰색 배경 */
            }}
        """
        # 기존 스타일시트를 덮어쓰고 고유 스타일을 적용합니다.
        self.back_btn.setStyleSheet(self.back_btn.styleSheet() + unique_style)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        # top_h_layout에서 back_btn을 제거하고, 별도의 하단 레이아웃으로 옮기기 위해 잠시 주석 처리
        # top_h_layout.addWidget(self.back_btn, 0) 
        main_layout.addLayout(top_h_layout)
        
        main_layout.addSpacing(130) 

        # ------------------------------------------------------------------
        # 이모지 레이블 및 오버레이 버튼 설정
        # ------------------------------------------------------------------
        # 이모지 레이블 설정
        self.emotion_label = QLabel() 
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(240, 240)
        self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;")
        self.emotion_label.hide() # 초기에는 이모지 레이블 숨김

        # 게임 시작 오버레이 버튼 (ClickableLabel 사용)
        self.start_overlay_button = ClickableLabel() # ClickableLabel 인스턴스 생성
        self.start_overlay_button.setFixedSize(240, 240)
        self.start_overlay_button.setAlignment(Qt.AlignCenter)
        
        start_game_pixmap = QPixmap("design/start_game.png")
        if not start_game_pixmap.isNull():
            scaled_pixmap = start_game_pixmap.scaled(
                self.start_overlay_button.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.start_overlay_button.setPixmap(scaled_pixmap)
        else:
            self.start_overlay_button.setText("게임 시작 (이미지 없음)")
            self.start_overlay_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;") # 대체 스타일
            print("경고: 'design/start_game.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        self.start_overlay_button.clicked.connect(self.start_game_clicked) # 슬롯 연결
        
        # 이모지와 오버레이 버튼을 담을 위젯 (Stack)
        self.center_widget = QWidget()
        center_stack_layout = QStackedWidget(self.center_widget) # QStackedWidget을 사용하여 겹치게 처리
        center_stack_layout.addWidget(self.emotion_label) 
        center_stack_layout.addWidget(self.start_overlay_button)
        center_stack_layout.setCurrentWidget(self.start_overlay_button) # 처음에는 버튼이 보이도록 설정
        self.center_widget.setFixedSize(240, 240) # 크기를 맞춰줌
        
        # 하단 레이아웃 (웹캠 1 - 중앙 컨테이너 - 웹캠 2)
        bottom_h_layout = QHBoxLayout()
        
        # P1 웹캠 및 정확도
        player1_v_layout = QVBoxLayout()
        self.player1_webcam_title = QLabel('PLAYER 1') 
        self.player1_webcam_title.setFont(QFont('ARCO', 50)) 
        self.player1_webcam_title.setStyleSheet("""
            color: #FFD50A;  
            padding-bottom: 8px;
        """)
        self.player1_webcam_title.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_webcam_title) 
        
        self.player1_video = QLabel('웹캠 1 피드')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        player1_v_layout.addWidget(self.player1_video)
        
        self.player1_accuracy = QLabel(f'P1 정확도: {self.p1_score: .2f}%')
        self.player1_accuracy.setFont(QFont('Jalnan Gothic', 25))
        self.player1_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_accuracy)
        player1_v_layout.addSpacing(15) 
        
        p1_score_h_layout = QHBoxLayout()
        p1_score_h_layout.addStretch(1) 
        self._setup_score_images(p1_score_h_layout, self.p1_score_images)
        p1_score_h_layout.addStretch(1) 
        player1_v_layout.addLayout(p1_score_h_layout)

        player1_v_layout.addStretch(1) 

        # P2 웹캠 및 정확도
        player2_v_layout = QVBoxLayout()
        self.player2_webcam_title = QLabel('PLAYER 2')
        self.player2_webcam_title.setFont(QFont('ARCO', 50)) 
        self.player2_webcam_title.setStyleSheet("""
            color: #FFD50A; 
            padding-bottom: 8px;
        """)
        self.player2_webcam_title.setAlignment(Qt.AlignCenter)
        player2_v_layout.addWidget(self.player2_webcam_title) 

        self.player2_video = QLabel('웹캠 2 피드')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        player2_v_layout.addWidget(self.player2_video)

        self.player2_accuracy = QLabel(f'P2 정확도: {self.p2_score: .2f}%')
        self.player2_accuracy.setFont(QFont('Jalnan Gothic', 25))
        self.player2_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player2_accuracy.setAlignment(Qt.AlignCenter)
        player2_v_layout.addWidget(self.player2_accuracy)
        player2_v_layout.addSpacing(15) 
        
        p2_score_h_layout = QHBoxLayout()
        p2_score_h_layout.addStretch(1) 
        self._setup_score_images(p2_score_h_layout, self.p2_score_images)
        p2_score_h_layout.addStretch(1) 
        player2_v_layout.addLayout(p2_score_h_layout)

        player2_v_layout.addStretch(1) 
        
        # ------------------------------------------------------------------
        # 중앙 수직 컨테이너: 타이머 + 이모지/버튼 + 간격
        # ------------------------------------------------------------------
        center_v_layout = QVBoxLayout()
        center_v_layout.addSpacing(90) # 남는 공간을 이 위쪽에 할당
        center_v_layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        center_v_layout.addSpacing(20)
        center_v_layout.addWidget(self.center_widget, alignment=Qt.AlignCenter)
        center_v_layout.addSpacing(80) # 예시: 50 픽셀 간격
        center_v_layout.addStretch(1) 
        # ------------------------------------------------------------------
        bottom_h_layout.addStretch(1) 
        bottom_h_layout.addLayout(player1_v_layout)
        bottom_h_layout.addSpacing(100) 
        bottom_h_layout.addLayout(center_v_layout) 
        bottom_h_layout.addSpacing(100) 
        
        bottom_h_layout.addLayout(player2_v_layout)
        bottom_h_layout.addStretch(1)
        main_layout.addLayout(bottom_h_layout)
        
        # 🟢 종료 버튼을 위한 새로운 하단 레이아웃 추가
        bottom_exit_layout = QHBoxLayout()
        bottom_exit_layout.addStretch(0) # 좌측에 공간 추가
        bottom_exit_layout.addWidget(self.back_btn) # 종료 버튼 추가
        bottom_exit_layout.addSpacing(30)

        main_layout.addLayout(bottom_exit_layout)
        main_layout.addSpacing(20) # 최하단 여백 추가
        
        self.setLayout(main_layout)
        
        self.update_score_display()


    # 새로운 슬롯: 게임 시작 버튼 클릭 시
    def start_game_clicked(self):
        # 1. 게임 시작 오버레이 버튼 숨기기
        self.start_overlay_button.hide()
        # 2. 이모지 레이블 표시
        self.emotion_label.show() 
        
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.setStyleSheet("color: #0AB9FF; font-weight: bold;")
        self.timer_label.show() 
        
        # 3. 게임 상태 초기화
        self.p1_score = 0
        self.p2_score = 0
        self.round = 0
        self.update_score_display() # 점수 이미지 초기화

        # 4. 첫 라운드 시작
        self.start_next_round()
    
    # 스코어 이미지 레이블을 생성하고 레이아웃에 추가하는 헬퍼 함수
    def _setup_score_images(self, h_layout, score_image_list):
        for _ in range(self.MAX_ROUNDS):
            score_label = QLabel()
            score_label.setFixedSize(flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'])
            score_label.setAlignment(Qt.AlignCenter)
            h_layout.addSpacing(5) 
            score_image_list.append(score_label)
            h_layout.addWidget(score_label)
            h_layout.addSpacing(5) 
            
    # P1, P2 점수에 따라 이미지(하트)를 업데이트하는 함수
    def update_score_display(self):
        # P1 점수 표시 업데이트
        for i in range(self.MAX_ROUNDS):
            pixmap = QPixmap(flag['FILLED_SCORE_IMAGE'] if i < self.p1_score else flag['EMPTY_SCORE_IMAGE'])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'], Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.p1_score_images[i].setPixmap(scaled_pixmap)
            else:
                self.p1_score_images[i].setText("?") 

        # P2 점수 표시 업데이트
        for i in range(self.MAX_ROUNDS):
            pixmap = QPixmap(flag['FILLED_SCORE_IMAGE'] if i < self.p2_score else flag['EMPTY_SCORE_IMAGE'])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'], Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.p2_score_images[i].setPixmap(scaled_pixmap)
            else:
                self.p2_score_images[i].setText("?") 
        
    # 랜덤으로 선택된 이모지 파일명을 받아 QLabel에 표시하는 함수
    def set_required_emotion(self, emotion_file):
        self.current_emotion_file = emotion_file
        file_path = os.path.join("img/emoji", emotion_file)

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
            self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0; color: red;")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
            self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;") 
        
    # update_timer 함수
    def update_timer(self):
        # 게임 시간 카운트 다운
        if self.time_left > 0:
            self.time_left -= 1
            
            # 남은 시간 표시 업데이트
            self.timer_label.setText(f"{self.time_left}")
            self.timer_label.setStyleSheet("color: #0AB9FF; font-weight: bold;")
                
            # time_left == 0이 되는 순간 UI 업데이트를 멈춥니다.
            if self.time_left == 0:
                self.game_timer.stop()
                self.is_game_active = False
                
                # --- 라운드 승패 판정 ---
                if self.p1_max_similarity == self.p2_max_similarity:
                    self.timer_label.setText("무승부! 재도전")
                    QTimer.singleShot(2000, self.start_next_round) 
                else:
                    if self.p1_max_similarity > self.p2_max_similarity: # 플레이어1 승리
                        self.timer_label.setText("P1 승리!")
                        self.p1_score += 1
                        if self.p1_score < self.MAX_ROUNDS:
                            QTimer.singleShot(2000, self.start_next_round)


                    else: # 플레이어2 승리
                        self.timer_label.setText("P2 승리!")
                        self.p2_score += 1
                        if self.p2_score < self.MAX_ROUNDS:
                            QTimer.singleShot(2000, self.start_next_round)
                    self.update_score_display()

                # --- 게임 종료 결정 (3점 선취승) ---
                if self.p1_score >= self.MAX_ROUNDS or self.p2_score >= self.MAX_ROUNDS:
                    self.timer_label.setText("게임 종료!")
                    self.stop_video_streams()
                    
                    self.start_overlay_button.show()
                    self.emotion_label.hide()
                    self.timer_label.hide()
                    
                    result_screen = self.stacked_widget.findChild(Resultscreen)
                    if result_screen:
                        final_p1_score = self.p1_score
                        final_p2_score = self.p2_score
                        result_screen.set_results(final_p1_score, final_p2_score)

                    self.stacked_widget.setCurrentIndex(2)
                    self.p1_score = 0
                    self.p2_score = 0
                    self.p1_max_similarity = 0
                    self.p2_max_similarity = 0
                    self.player1_accuracy.setText(f'P1 정확도: {self.p1_score: .2f}%')
                    self.player2_accuracy.setText(f'P1 정확도: {self.p2_score: .2f}%')
                    self.player1_video.clear()
                    self.player2_video.clear()
                    self.update_score_display()

    # start_next_round 함수
    def start_next_round(self):
        if self.p1_score >= self.MAX_ROUNDS or self.p2_score >= self.MAX_ROUNDS:
            return 
            
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        
        self.player1_accuracy.setText(f'P1 정확도: 0.00%')
        self.player2_accuracy.setText(f'P2 정확도: 0.00%')
        
        print(f"새 라운드 시작 (P1 승리: {self.p1_score} / P2 승리: {self.p2_score})")

        self.start_video_streams() 

    # update_image_and_score 함수
    def update_image_and_score(self, image, score, player_index):
        if self.is_game_active:
            pixmap = QPixmap.fromImage(image)
            
            if player_index == 0:
                self.player1_video.setPixmap(pixmap)
                self.p1_max_similarity = max(self.p1_max_similarity, score)
                self.player1_accuracy.setText(f'P1 정확도: {self.p1_max_similarity: .2f}%')
                
            elif player_index == 1:
                self.player2_video.setPixmap(pixmap)
                self.p2_max_similarity = max(self.p2_max_similarity, score)
                self.player2_accuracy.setText(f'P2 정확도: {self.p2_max_similarity: .2f}%')

    def get_available_camera_index(self):
        """사용 가능한 가장 낮은 인덱스의 웹캠 번호를 반환합니다."""
        # 0부터 9까지 시도하며, 먼저 열리는 카메라의 인덱스를 반환
        count = 0
        idxs = []
        for index in range(10): 
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                count += 1
                idxs.append(index) # 성공적인 인덱스 반환
            if count >= 2:
                return idxs
        return [0, 1] # 찾지 못하면 기본값 0 반환

    # start_video_streams 함수
    def start_video_streams(self):
        # 기존 스레드가 실행 중일 수 있으므로 안전하게 중지 및 정리
        self.stop_video_streams()
        self.video_threads = []
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        self.is_game_active = True

        if self.emotion_ids:
            random_emotion_id = random.choice(self.emotion_ids)
            self.set_required_emotion(random_emotion_id)
        index = self.get_available_camera_index()
        # 첫 번째 웹캠 스레드
        thread1 = VideoThread(
            camera_index = index[0],
            emotion_file = self.current_emotion_file,
            player_index = 0
            )
        thread1.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread1.start()
        self.video_threads.append(thread1)

        # 두 번째 웹캠 스레드
        thread2 = VideoThread(
            camera_index = index[1],
            emotion_file = self.current_emotion_file,
            player_index = 1
            )
        thread2.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread2.start()
        self.video_threads.append(thread2)
        
        self.time_left = self.total_game_time
        # start_game_clicked에서 타이머를 보이게 했으므로, 여기서는 시간만 설정합니다.
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.setStyleSheet("color: #0AB9FF; font-weight: bold;")
        
        self.game_timer.start(1000)
        
        print(f"웹캠 스트리밍 및 타이머 작동 시작")
    

    # stop_video_streams 함수
    def stop_video_streams(self):
        if self.game_timer.isActive():
            self.game_timer.stop()
        
        self.is_game_active = False
            
        for thread in self.video_threads:
            if thread.isRunning():
                try:
                    thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
                except Exception:
                    pass
                thread.stop()
        self.video_threads = []
        print("웹캠 스트리밍 및 타이머 작동 종료")

    # go_to_main_menu 함수 (수정: 오버레이 버튼 표시)
    def go_to_main_menu(self):
        self.stop_video_streams()
        
        # 메뉴로 돌아갈 때 오버레이 버튼 다시 표시
        self.start_overlay_button.show()
        self.emotion_label.hide() # 이모지 레이블 숨김
        self.timer_label.hide() 
        
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.setStyleSheet("color: black;")
        self.player1_video.setText('웹캠 1 피드')
        self.player2_video.setText('웹캠 2 피드')
        self.player1_video.setPixmap(QPixmap())
        self.player2_video.setPixmap(QPixmap())
        self.player1_accuracy.setText(f'P1 정확도: 0.00%')
        self.player2_accuracy.setText(f'P2 정확도: 0.00%')
        self.p1_score = 0
        self.p2_score = 0
        self.round = 0
        self.update_score_display()
        self.stacked_widget.setCurrentIndex(0)