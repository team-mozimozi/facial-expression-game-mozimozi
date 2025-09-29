import sys
import cv2 
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon

# ===============================================
# 상수 정의
# ===============================================
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
BUTTON_WIDTH = 402
BUTTON_HEIGHT = 410
BUTTON_COLOR = "transparent"
BUTTON_LABELS = ["MODE1", "MODE2", "MODE3"]

# 버튼의 기준 위치 (1번째 버튼)
BUTTON1_X = 316
BUTTON1_Y = 538

# 계산된 버튼 간격 및 위치
BUTTON_SPACING = 41
BUTTON2_X = BUTTON1_X + BUTTON_WIDTH + BUTTON_SPACING
BUTTON3_X = BUTTON2_X + BUTTON_WIDTH + BUTTON_SPACING

# 우측 하단 버튼 정의 (추가)
BUTTON_EXIT_WIDTH = 129
BUTTON_EXIT_HEIGHT = 101
BUTTON_EXIT_MARGIN = 20 # 우측 및 하단으로부터의 마진
BUTTON_EXIT_X = SCREEN_WIDTH - BUTTON_EXIT_WIDTH - BUTTON_EXIT_MARGIN
BUTTON_EXIT_Y = SCREEN_HEIGHT - BUTTON_EXIT_HEIGHT - BUTTON_EXIT_MARGIN

# 이미지 파일 경로 (사용자 환경에 맞게 경로를 수정해야 할 수 있습니다.)
BACKGROUND_IMAGE_PATH = 'design/page_main.png' 
# 우측 하단 도움말 아이콘 이미지 경로 (사용자가 실제 경로로 변경해야 합니다.)
BUTTON_EXIT_IMAGE_PATH = 'design/exit.png'

# ----------------------------------------------------------------------
# 4. 메인 메뉴 화면 (MainMenu)
# ----------------------------------------------------------------------
class MainMenu(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        # 1. 전체화면 (1920x1080) 설정 및 프레임리스 모드 적용
        self.setWindowFlag(Qt.FramelessWindowHint) 
        self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT) 
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT) 
        self.initUI()
    
    def setup_background(self):
        """배경 이미지를 QLabel에 로드하고 윈도우 전체 크기로 설정합니다.
           이미지 로드 실패에 대한 대체 코드가 모두 제거되었습니다.
        """
        self.background_label = QLabel(self)
        
        pixmap = QPixmap(BACKGROUND_IMAGE_PATH)
        
        # 윈도우 크기에 맞게 이미지 스케일 조정 (꽉 채움)
        scaled_pixmap = pixmap.scaled(QSize(SCREEN_WIDTH, SCREEN_HEIGHT), 
                                     Qt.IgnoreAspectRatio, 
                                     Qt.SmoothTransformation)
        self.background_label.setPixmap(scaled_pixmap)
        
        self.background_label.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

    
    def create_buttons(self):
        """조건에 맞는 3개의 메인 버튼과 우측 하단 버튼을 생성하고 정렬합니다."""
        
        # 1. 첫 번째 버튼 (게임 시작)
        self.btn1 = self.create_custom_button(
            BUTTON_LABELS[0], BUTTON1_X, BUTTON1_Y, BUTTON_WIDTH, BUTTON_HEIGHT, 20, 58, BUTTON_COLOR
        )
        # 2. 두 번째 버튼 (설정)
        self.btn2 = self.create_custom_button(
            BUTTON_LABELS[1], BUTTON2_X, BUTTON1_Y, BUTTON_WIDTH, BUTTON_HEIGHT, 20, 58, BUTTON_COLOR
        )
        # 3. 세 번째 버튼 (종료)
        self.btn3 = self.create_custom_button(
            BUTTON_LABELS[2], BUTTON3_X, BUTTON1_Y, BUTTON_WIDTH, BUTTON_HEIGHT, 20, 58, BUTTON_COLOR
        )

        # 4. 우측 하단 버튼 (이미지로 대체)
        self.btn_exit = self.create_custom_button(
            "", # 텍스트 대신 아이콘 사용
            BUTTON_EXIT_X, 
            BUTTON_EXIT_Y, 
            BUTTON_EXIT_WIDTH, 
            BUTTON_EXIT_HEIGHT,
            bg_color="transparent"
        )
        
        # *** 우측 하단 버튼 스타일 분리를 위한 고유 이름 설정 ***
        self.btn_exit.setObjectName("BottomRightIcon")
        
        # 아이콘 이미지 설정
        icon_path = BUTTON_EXIT_IMAGE_PATH
        icon_pixmap = QPixmap(icon_path)
        
        # QPixmap을 QIcon으로 변환하여 버튼에 설정
        icon_size = QSize(BUTTON_EXIT_WIDTH - 20, BUTTON_EXIT_HEIGHT - 20)
        scaled_icon = icon_pixmap.scaled(
            icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.btn_exit.setIcon(QIcon(scaled_icon))
        self.btn_exit.setIconSize(scaled_icon.size())

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
        self.btn_exit.setStyleSheet(self.btn_exit.styleSheet() + unique_style)


        # 버튼 클릭 시 동작 연결
        self.btn1.clicked.connect(self.game1)
        self.btn2.clicked.connect(self.game2)
        self.btn3.clicked.connect(self.game3)
        
        # 우측 하단 버튼 클릭 동작 연결 (추가)
        self.btn_exit.clicked.connect(lambda: self.button_action("EXIT"))

    def create_custom_button(self, text, x, y, width, height, font_size=20, border_radius=58, bg_color=BUTTON_COLOR):
        """지정된 속성으로 QPushButton을 생성하고 스타일시트를 설정합니다."""
        button = QPushButton(text, self)
        # 버튼 크기 설정
        button.setGeometry(x, y, width, height)

        # 버튼 색상 및 스타일 설정
        # 이 스타일은 모든 QPushButton에 기본적으로 적용됩니다.
        style = f"""
            QPushButton {{
                background-color: {bg_color}; /* 배경색 사용 */
                color: #343a40;
                border-radius: {border_radius}px; /* 테두리 반경 사용 */
                font-family: 'Jalnan Gothic', 'Arial', sans-serif;
                font-size: {font_size}pt; /* 폰트 크기 사용 */
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
        button.setStyleSheet(style)
        return button

    def initUI(self):
        self.setup_background()
        self.create_buttons()

    def game1(self):
        """1:1 표정 대결 모드 시작 (Index 1)"""
        self.stacked_widget.setCurrentIndex(1)
        # Game1Screen에서 start_video_streams()를 호출하여 웹캠 스트림 시작
        if hasattr(self.stacked_widget.widget(1), 'start_video_streams'):
            self.stacked_widget.widget(1).start_video_streams()
            
    def game2(self):
        """이모지 매칭 모드 시작 (Index 3)"""
        self.stacked_widget.setCurrentIndex(3)
        # Game2Screen에서 start_stream()을 호출하여 웹캠 스트림 시작
        if hasattr(self.stacked_widget.widget(3), 'start_stream'):
            self.stacked_widget.widget(3).start_stream()
    
    def game3(self):
        return None