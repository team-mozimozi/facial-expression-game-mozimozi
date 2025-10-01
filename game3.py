# game3.py 내용 시작
import cv2
import random
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QPointF 
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QMouseEvent, QPainter, QPainterPath, QColor, QCursor, QPen, QBrush
from compare import calc_similarity  

import numpy as np

from mainmenu import flag

# mainmenu.py에서 flag 딕셔너리를 import했다고 가정
# 기본 상수 정의 (flag import에 실패하거나 키가 없을 경우 사용)
VIDEO_WIDTH = 500
VIDEO_HEIGHT = 370
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080 

# 사용자 요청에 따른 상수 정의
SCORE_IMAGE = 100
EMPTY_SCORE_IMAGE = "design/score_empty_heart.png"
FILLED_SCORE_IMAGE = "design/score_filled_heart.png"
EXIT_BUTTON_IMAGE = "design/exit.png"
START_BUTTON_IMAGE = "design/start_game.png"
MAIN_BUTTON_IMAGE = "design/main.png"

BUTTON_EXIT_WIDTH = 129
BUTTON_EXIT_HEIGHT = 101
BUTTON_EXIT_MARGIN = 20
BUTTON_EXIT_X = SCREEN_WIDTH - BUTTON_EXIT_WIDTH - BUTTON_EXIT_MARGIN
BUTTON_EXIT_Y = SCREEN_HEIGHT - BUTTON_EXIT_HEIGHT - BUTTON_EXIT_MARGIN


# --- MODE 3 스타일 상수 정의 ---
MODE3_FONT_FAMILY = 'ARCO'
MODE3_FILL_COLOR = QColor("#EBE052")    # 핫핑크
MODE3_OUTLINE_COLOR = QColor("#1608D8") # 거의 흰색
MODE3_OUTLINE_WIDTH = 0.3

# ======================================================================
# 1. 텍스트 테두리 기능을 위한 사용자 정의 QLabel 클래스
# ======================================================================
class OutlinedLabel(QLabel):
    def __init__(self, text, font, fill_color, outline_color, outline_width, alignment=Qt.AlignLeft | Qt.AlignVCenter, parent=None):
        super().__init__(text, parent)
        self.setFont(font)
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.setAlignment(alignment)
        # 텍스트 색상을 투명하게 설정하여 QPainter만 사용하도록 함
        self.setStyleSheet("color: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 부드러운 렌더링

        text = self.text()
        font = self.font()
        
        path = QPainterPath()
        rect = self.contentsRect()
        
        fm = painter.fontMetrics()
        text_height = fm.height()
        
        # 텍스트의 실제 위치를 계산합니다.
        
        # Y 위치 계산: QFontMetrics를 사용하여 텍스트 기준선(Baseline) 위치를 찾습니다.
        # 중앙 정렬: (전체 높이 - 텍스트 높이) / 2 + 텍스트 기준선
        y = rect.top() + (rect.height() - text_height) // 2 + fm.ascent()
        
        # X 위치 계산: 정렬에 따라 조정
        x = 0
        if self.alignment() & Qt.AlignLeft:
             # 스타일시트의 padding-left: 20px를 수동으로 적용할 경우
             # mode_bar는 padding-left를 스타일시트에서 설정하므로, 여기서 20을 더합니다.
            if self.objectName() == "mode_bar_label":
                x = rect.left() + 20
            else:
                x = rect.left() 
        elif self.alignment() & Qt.AlignHCenter:
            text_width = fm.horizontalAdvance(text)
            x = rect.left() + (rect.width() - text_width) // 2

        # QPainterPath에 텍스트를 폰트와 함께 추가합니다.
        path.addText(QPointF(x, y), font, text)

        # 1. 테두리 설정 (QPen)
        outline_pen = QPen(self.outline_color, self.outline_width)
        outline_pen.setJoinStyle(Qt.RoundJoin) # 테두리 모서리를 둥글게 처리
        painter.setPen(outline_pen)

        # 2. 채우기 설정 (QBrush)
        fill_brush = QBrush(self.fill_color)
        painter.setBrush(fill_brush)

        # 3. 경로 그리기 (테두리와 채우기 모두 적용)
        painter.drawPath(path)
        
    # QWidget의 sizeHint를 오버라이드하여 레이블의 크기가 텍스트에 맞도록 힌트를 제공
    def sizeHint(self):
        # 텍스트 크기에 따라 적절한 크기를 반환 (테두리 두께 고려)
        return super().sizeHint()
# =====================================================================



# ----------------------------------------------------------------------
# ClickableLabel 도우미 클래스 (새로 추가)
# ----------------------------------------------------------------------
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
        
    # [추가] 마우스가 위젯 영역에 들어올 때 호출
    def enterEvent(self, event: QMouseEvent):
        # 마우스 포인터를 '손가락' 모양으로 설정
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    # [추가] 마우스가 위젯 영역을 벗어날 때 호출
    def leaveEvent(self, event: QMouseEvent):
        # 마우스 포인터를 기본 모양(화살표)으로 되돌림
        self.unsetCursor() 
        super().leaveEvent(event)


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


        #self.is_transitioning = False
        #self.transition_delay_ms = 1000

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
                 # 유사도 계산
                similarity = calc_similarity(frame, self.emotion_file)
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                
                
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
        
        self.game_started = False 
        self.initUI()
        
    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.addSpacing(30)
        #  OutlinedLabel 적용: result_title 
        result_font = QFont('Jalnan 2', 60, QFont.Bold)
        self.result_title = OutlinedLabel(
            "게임 종료!", 
            result_font, 
            QColor("#FF5CA7"),  # Pink fill
            QColor(Qt.white),   # Black outline
            4.0, 
            alignment=Qt.AlignCenter
        )
        # self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold)) # OutlinedLabel에서 설정
        # self.result_title.setAlignment(Qt.AlignCenter) # OutlinedLabel에서 설정
        
        #  OutlinedLabel 적용: total_label 
        total_font = QFont('Jalnan 2', 60)
        self.total_label = OutlinedLabel(
            "결과 계산 중...", 
            total_font, 
            QColor(Qt.white), # White fill
            QColor(Qt.black),  # Black outline
            3.0, 
            alignment=Qt.AlignCenter
        )
        # self.total_label.setFont(QFont('Jalnan 2', 60)) # OutlinedLabel에서 설정
        # self.total_label.setAlignment(Qt.AlignCenter) # OutlinedLabel에서 설정
        
        # self.result_title = QLabel("게임 종료!")
        # self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        # self.result_title.setAlignment(Qt.AlignCenter)
        # self.total_label = QLabel("결과 계산 중...")
        # self.total_label.setFont(QFont('Jalnan 2', 60))
        # self.total_label.setAlignment(Qt.AlignCenter)
        
        # "메인 메뉴로 돌아가기" 버튼을 이미지로 변경 및 위치 조정
        back_to_menu_button = ClickableLabel()
        back_to_menu_button.clicked.connect(self.main_menu_button)
        
        back_to_menu_button.setScaledContents(True)
        
        exit_pixmap = QPixmap(flag['MAIN_BUTTON_IMAGE'])
        if not exit_pixmap.isNull():
            back_to_menu_button.setPixmap(exit_pixmap)
            back_to_menu_button.setFixedSize(exit_pixmap.size()) # 이미지 크기에 맞게 설정
            back_to_menu_button.setFixedSize(120, 60)
        else:
            back_to_menu_button.setText("메인 메뉴로 돌아가기")
            back_to_menu_button.setFixedSize(120, 60) # 기본 크기
            back_to_menu_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;")
            print("경고: 'design/exit.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        h_layout = QHBoxLayout()
        h_layout.addSpacing(1) # 좌측에 공간을 추가하여 버튼을 오른쪽으로 밈
        h_layout.addWidget(back_to_menu_button)
        h_layout.addSpacing(1) # 우측 여백
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.total_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout) # 하단 레이아웃 추가
        self.layout.addSpacing(10) # 하단 여백 추가

        self.setLayout(self.layout)
        
        
    def set_results3(self, total_score):
        self.total_text = f" Result!! (total_score: {total_score:.2f}점) "
        
        # 폰트와 색상 스타일은 OutlinedLabel이 관리하므로 중복 코드를 제거하거나 수정
        current_font = self.total_label.font()
        current_font.setPointSize(50)
        self.total_label.setFont(current_font)
            
        self.total_label.setText(self.total_text)
    
    def main_menu_button(self):
        self.stacked_widget.setCurrentIndex(0)    
        # 2.[핵심 수정]: Game3Screen의 인스턴스를 찾아 초기화 함수 호출
        # Game3Screen은 보통 인덱스 1에 위치합니다.
        GAME3_SCREEN_INDEX = 4 
    
        if self.stacked_widget.count() > GAME3_SCREEN_INDEX:
            game3_screen_instance = self.stacked_widget.widget(GAME3_SCREEN_INDEX)
        
        # 'reset_game_state' 함수가 Game3Screen에 정의되어 있다면 호출합니다.
        if hasattr(game3_screen_instance, 'reset_game_state'):
            game3_screen_instance.stop_stream() # 혹시 모를 상황 대비하여 스트림 종료
            game3_screen_instance.reset_game_state() # UI를 시작 전 상태로 완벽 리셋
        return    
        
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
            self.emotion_files = ["0_angry.png"]

        self.current_emotion_file = None
        self.total_score = 0
        self.target_similarity = 40.0  # 목표 유사도 (예: 80%)
        
        self.is_transitioning = False # 이모지 전환 중인지 확인하는 플래그
        self.transition_delay_ms  = 1000  # 딜레이 시간(1000ms = 1초)
        
        
        self.total_game_time = 5     # 총 게임 시간 (60초)
        self.time_left = self.total_game_time
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        
         # 추가: 게임 상태 플래그
        self.game_started = False 
        
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()

        # 상단 Mode1 바 (유지)
        # [수정] QLabel -> OutlinedLabel 적용
        # 이전 스타일: background-color: #FFE10A; color: #FF5CA7; padding-left: 20px;
        mode1_bar_font = QFont('ARCO', 30, QFont.Bold)
        mode1_bar_fill = QColor("#FF5CA7")
        mode1_bar_outline = QColor("#FFF0FA")
        mode1_bar_width = 3.5
        
        mode1_bar = OutlinedLabel(
            "MODE3", 
            mode1_bar_font, 
            mode1_bar_fill, 
            mode1_bar_outline, 
            mode1_bar_width, 
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            parent=self
        )
        mode1_bar.setObjectName("mode_bar_label") # padding-left 처리를 위해 이름 지정
        mode1_bar.setStyleSheet("background-color: #FFE10A;") 
        
        mode1_bar.setFixedHeight(85)
        mode1_bar.setFixedWidth(1920) 
        main_layout.addWidget(mode1_bar) 

        # --- 타이틀 / 메뉴 버튼 레이아웃 ---
        top_h_layout = QHBoxLayout()
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)


        


        # OutlinedLabel 적용: timer_label - MODE 3 스타일로 통일
        timer_font = QFont(MODE3_FONT_FAMILY, 30, QFont.Bold)
        self.timer_label = OutlinedLabel(
            f"남은 시간: {self.total_game_time}초", 
            timer_font, 
            MODE3_FILL_COLOR,  # 핫핑크로 변경
            MODE3_OUTLINE_COLOR, # 거의 흰색
            MODE3_OUTLINE_WIDTH, # 3.5
            alignment=Qt.AlignCenter
        )
        # self.timer_label.setStyleSheet("color: blue;") # 제거



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
        self.back_btn.clicked.connect(self.go_to_main_menu)
        # "메뉴로 돌아가기" 버튼을 이미지로 변경
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
        self.back_btn.setStyleSheet(self.back_btn.styleSheet() + unique_style)

        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(230)

        # --- 중앙 레이아웃 ---
        center_h_layout = QHBoxLayout()

        # 1. 이모지 + 타이머 + 점수 (세로 중앙)
        emoji_layout = QVBoxLayout()
        emoji_layout.addStretch(1)  # 상단 여백

        # self.timer_label = QLabel(f"남은 시간: {self.total_game_time}초")
        # self.timer_label.setFont(QFont('Jalnan Gothic', 24, QFont.Bold))
        # self.timer_label.setStyleSheet("color: blue;")
        # self.timer_label.setAlignment(Qt.AlignCenter)

        # 변경 시작: 이모지 대신 ClickableLabel을 사용하여 시작 버튼 추가
        self.start_button = ClickableLabel()
        self.start_button.setAlignment(Qt.AlignCenter)
        self.start_button.setFixedSize(300, 200)
        #self.start_button.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        self.start_button.clicked.connect(self.start_game) # 👈 버튼 클릭 시 게임 시작
        
        # 시작 버튼 이미지 설정
        start_pixmap = QPixmap(START_BUTTON_IMAGE)
        if not start_pixmap.isNull():
            scaled_start_pixmap = start_pixmap.scaled(
                self.start_button.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.start_button.setPixmap(scaled_start_pixmap)
        else:
            self.start_button.setText("게임 시작")
            self.start_button.setFont(QFont('Jalnan Gothic', 24, QFont.Bold))
            print(f"경고: '{START_BUTTON_IMAGE}' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")



        self.emotion_label = QLabel("표정 이미지 준비 중...")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(300, 200)
        #self.emotion_label.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        self.emotion_label.hide() # 초기에는 숨김
        
        # OutlinedLabel 적용: score_label - MODE 3 스타일로 통일
        score_font = QFont(MODE3_FONT_FAMILY, 30, QFont.Bold)
        self.score_label = OutlinedLabel(
            f"SCORE: {self.total_score}점", 
            score_font, 
            MODE3_FILL_COLOR, 
            MODE3_OUTLINE_COLOR, 
            MODE3_OUTLINE_WIDTH, 
            alignment=Qt.AlignCenter
        )
        # self.score_label.setStyleSheet("color: red;") # 제거
        


        # self.score_label = QLabel(f"SCORE: {self.total_score}점")
        # self.score_label.setFont(QFont('Jalnan Gothic', 20, QFont.Bold))
        # self.score_label.setStyleSheet("color: red;")
        # self.score_label.setAlignment(Qt.AlignCenter)

        emoji_layout.addWidget(self.timer_label)
        # 변경: 시작 버튼과 이모지 레이블을 번갈아 표시
        emoji_layout.addWidget(self.start_button) 
        emoji_layout.addWidget(self.emotion_label)
        # 변경 끝
        emoji_layout.addWidget(self.score_label)
        emoji_layout.addStretch(2)  # 하단 여백
        

        # 2. 웹캠 + PLAYER + 유사도 (세로 중앙)
        video_score_layout = QVBoxLayout()
        video_score_layout.addStretch(1)  # 상단 여백

        self.player_label = QLabel("PLAYER")
        
        # OutlinedLabel 적용: player_label - MODE 3 스타일로 통일
        # 이미지의 'PLAYER 1'과 유사하게 폰트 크기 조정
        player_font = QFont(MODE3_FONT_FAMILY, 30, QFont.Bold) 
        self.player_label = OutlinedLabel(
            "PLAYER", 
            player_font, 
            MODE3_FILL_COLOR, 
            MODE3_OUTLINE_COLOR, 
            MODE3_OUTLINE_WIDTH, 
            alignment=Qt.AlignCenter
        )
        
        
        # self.player_label.setFont(QFont('Jalnan Gothic', 18, QFont.Bold))
        # self.player_label.setStyleSheet("color: green;")
        # self.player_label.setAlignment(Qt.AlignCenter)

        self.video_label = QLabel('웹캠 피드 (400x300)')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(400, 300)
        self.video_label.setStyleSheet("background-color: black; color: white;")

        # self.current_accuracy = QLabel(f'현재 유사도: {0.00: .2f}%')
        # self.current_accuracy.setFont(QFont('Jalnan Gothic', 18, QFont.Bold))
        # self.current_accuracy.setAlignment(Qt.AlignCenter)

        # self.target_label = QLabel(f'목표 유사도: {self.target_similarity:.0f}%')
        # self.target_label.setFont(QFont('Jalnan Gothic', 18, QFont.Bold))
        # self.target_label.setStyleSheet("color: #007bff;")
        # self.target_label.setAlignment(Qt.AlignCenter)

        # OutlinedLabel 적용: current_accuracy - MODE 3 스타일로 통일 
        current_acc_font = QFont(MODE3_FONT_FAMILY, 18, QFont.Bold)
        self.current_accuracy = OutlinedLabel(
            f'현재 유사도: {0.00: .2f}%', 
            current_acc_font, 
            MODE3_FILL_COLOR, 
            MODE3_OUTLINE_COLOR, 
            MODE3_OUTLINE_WIDTH, 
            alignment=Qt.AlignCenter
        )

        # OutlinedLabel 적용: target_label - MODE 3 스타일로 통일
        target_font = QFont(MODE3_FONT_FAMILY, 18, QFont.Bold)
        self.target_label = OutlinedLabel(
            f'목표 유사도: {self.target_similarity:.0f}%', 
            target_font, 
            MODE3_FILL_COLOR, 
            MODE3_OUTLINE_COLOR, 
            MODE3_OUTLINE_WIDTH, 
            alignment=Qt.AlignCenter
        )


        video_score_layout.addWidget(self.player_label)
        video_score_layout.addWidget(self.video_label)
        video_score_layout.addWidget(self.current_accuracy)
        video_score_layout.addWidget(self.target_label)
        video_score_layout.addStretch(2)  # 하단 여백

        # --- 중앙 레이아웃에 배치 ---
        center_h_layout.addStretch(1)
        center_h_layout.addLayout(video_score_layout)
        center_h_layout.addSpacing(200)  # 좌우 간격
        center_h_layout.addLayout(emoji_layout)
        center_h_layout.addStretch(1)

        main_layout.addLayout(center_h_layout)
        main_layout.addStretch(1)

        # --- QWidget 기반 레이아웃 적용 ---
        self.setLayout(main_layout)
        
    # 추가: 게임 시작을 처리하는 함수
    def start_game(self):
        """게임 시작 버튼 클릭 시 호출되며, 게임을 초기화하고 스트림을 시작합니다."""
        if self.game_started:
            return

        print("게임 시작 버튼 클릭. 게임을 시작합니다.")
        self.game_started = True
        
        # 1. 시작 버튼 숨기기, 이모지 레이블 표시
        self.start_button.hide()
        self.emotion_label.show()
        
        # 2. 스트림 및 타이머 시작
        self.start_stream()
            
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
        
        # [수정] OutlinedLabel의 fill_color를 동적으로 변경하고 repaint를 호출
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.fill_color = QColor("red") # 빨간색 채우기
        else:
            # 기본 색상 복귀 (initUI에서 설정한 Blue fill)
            self.timer_label.fill_color = QColor("#4285F4") # Blue fill 
            
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
        if score >= self.target_similarity and not self.is_transitioning:
            
            self.is_transitioning = True
            
            # 점수 획득
            self.total_score += 1 
            self.score_label.setText(f"SCORE: {self.total_score}점")
            
            self.video_label.setStyleSheet("border: 5px solid #0f0;") # 초록색 테두리
            
            
            QTimer.singleShot(self.transition_delay_ms, self.complete_transition)
        
            print(f"목표 달성! 점수 {self.total_score}점 획득. 1초 딜레이 시작.")

            
            # 다음 이모지 설정 (새로운 목표)
            #self.set_next_emotion()
            
            # 목표 달성 시 시각적 피드백
            self.video_label.setStyleSheet("border: 3px solid #0f0; background-color: black; color: white;")
            QTimer.singleShot(1000, lambda: self.video_label.setStyleSheet("background-color: black; color: white;")) # 0.2초 후 원래대로 복귀
    
    
    def complete_transition(self):
        """
        QTimer에 의해 딜레이 시간(1초) 경과 후 호출되어
        다음 이모지 설정 및 전환 플래그를 해제합니다.
        """
        
        # 1. 다음 이모지 설정 (랜덤 선택 및 TimeAttackThread에 전달)
        # 이 함수 안에 TimeAttackThread.set_emotion_file 호출 로직이 포함되어 있어야 합니다.
        self.set_next_emotion() 
        
        # 2. 웹캠 피드 스타일 초기화 (테두리 제거)
        self.video_label.setStyleSheet("border: none;") 
        
        # 3. 플래그 해제: 이제 다시 점수 획득을 할 수 있게 됩니다.
        self.is_transitioning = False
        
        print("이모지 전환 완료 및 플래그 해제. 다음 목표 표정 시작.")


    def start_stream(self):
        """스트리밍을 시작하고 게임 타이머를 리셋합니다."""
        
        if not self.game_started:
            print("경고: start_stream이 game_started=False인 상태에서 호출되었습니다. 실행을 중단합니다.")
            return
        
        self.stop_stream()
        
        # 초기화
        self.total_score = 0
        self.score_label.setText(f"SCORE: {self.total_score}점")
        
        
        self.time_left = self.total_game_time 
        
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
        
        # [수정] OutlinedLabel 색상 초기화
        #self.timer_label.fill_color = QColor("#4285F4") # Blue fill (기본값)
        #self.timer_label.repaint()
        
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
    # 추가: 게임 화면이 다시 나타날 때 상태를 초기화
    def showEvent(self, event):
        """위젯이 화면에 표시될 때 호출됩니다."""
        super().showEvent(event)
        # 게임이 종료된 상태에서 다시 돌아왔을 때만 초기화
        if not self.game_started:
            self.reset_game_state()
            
    def reset_game_state(self):
        """
        게임을 시작 전 상태로 되돌립니다.
        메뉴 복귀 시 타이머를 TOTAL_GAME_TIME으로 확실하게 초기화합니다.
        """
        
        # 1. 상태 변수 초기화
        self.total_score = 0
        #[핵심 수정]: 남은 시간을 TOTAL_GAME_TIME으로 강제 재설정
        self.total_game_time = 5

        self.game_started = False
        # 2. UI 요소 초기화 (hasattr 검사를 통해 crash 방지)
        
        # start_button을 다시 표시하고, 게임 진행 위젯을 숨깁니다.
        if hasattr(self, 'start_button'): # start_button이 있다면
            self.start_button.show()
        
        # 타이머 레이블을 초기 시간으로 설정
        self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
           
       
       # 점수 초기화
        if hasattr(self, 'score_display'):
            self.score_display.setText(f"SCORE : {self.total_score}") 


        
       # self.game_started = False
        
        self.start_button.show()
        self.emotion_label.hide()
        
        
        
        #self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
        #self.timer_label.setStyleSheet("color: blue; font-weight: bold;")
        self.score_label.setText(f"SCORE: {0}점")
        self.current_accuracy.setText(f'현재 유사도: {0.00: .2f}%')
        self.video_label.setText('웹캠 피드 (400x300)')
        self.video_label.setPixmap(QPixmap()) # 웹캠 피드 이미지 초기화

     # 전환 플래그 초기화
        self.is_transitioning = False
        self.current_emotion_file = None
        self.game_started = False

    def go_to_result_screen(self, Qwidget):
        result_screen = self.stacked_widget.widget(5) 
        


        
    def go_to_main_menu(self):
        self.stop_stream()
        self.reset_game_state()
        
        self.stacked_widget.setCurrentIndex(0)