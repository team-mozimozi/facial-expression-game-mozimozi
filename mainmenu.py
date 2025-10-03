import sys
import cv2 
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QRect
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QColor, QMouseEvent, QCursor
import re 

# 플래그 (Flag) 정의는 변경 없음
flag = {
    'SCREEN_WIDTH': 1920,
    'SCREEN_HEIGHT': 1080,

    'VIDEO_WIDTH': 500,
    'VIDEO_HEIGHT': 370,

    'BUTTON_WIDTH': 402,
    'BUTTON_HEIGHT': 410,
    'BUTTON_COLOR': "transparent",
    'BUTTON_LABELS': ["MODE1", "MODE2", "MODE3"],
    'BUTTON1_X': 316,
    'BUTTON1_Y': 538,
    'BUTTON_SPACING': 41,
    'BUTTON2_X': 759, 
    'BUTTON3_X': 1202, 

    'BUTTON_EXIT_WIDTH': 129,
    'BUTTON_EXIT_HEIGHT': 101,
    'BUTTON_EXIT_MARGIN': 20,
    'BUTTON_EXIT_X': 1771, 
    'BUTTON_EXIT_Y': 959, 
    'SCORE_IMAGE_SIZE': 100,

    'BACKGROUND_IMAGE_PATH': 'design/page_main.png',
    'BUTTON_EXIT_IMAGE_PATH': 'design/exit.png',
    'EMPTY_SCORE_IMAGE': "design/score_empty_heart.png", 
    'FILLED_SCORE_IMAGE': "design/score_filled_heart.png", 
    'MAIN_BUTTON_IMAGE': "design/main.png", 
    'START_BUTTON_IMAGE': "design/start_game.png",

    'MODE3_FONT_FAMILY': 'ARCO',
    'MODE3_FILL_COLOR': QColor("#EBE052"),      
    'MODE3_OUTLINE_COLOR': QColor("#1608D8"), 
    'MODE3_OUTLINE_WIDTH': 0.3
}

# ----------------------------------------------------------------------
# 1. ClickableLabel 클래스 (QPushButton 스타일 모방 로직)
# ----------------------------------------------------------------------
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    HOVER_COLOR = "#8FFF84B3" 
    PRESSED_COLOR = "#8FFF84B3" 
    NORMAL_COLOR = "transparent"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)

    def set_background_color(self, color):
        """배경색을 설정하고 기존 텍스트 스타일은 유지합니다."""
        current_style = self.styleSheet()
        # background-color: [색상]; 패턴을 찾아 교체합니다.
        new_style = re.sub(r'background-color: [^;]+;', f'background-color: {color};', current_style)
        self.setStyleSheet(new_style)

    def mousePressEvent(self, event):
        self.set_background_color(self.PRESSED_COLOR)
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            self.set_background_color(self.HOVER_COLOR)
        else:
            self.set_background_color(self.NORMAL_COLOR)
        super().mouseReleaseEvent(event)
        
    def enterEvent(self, event: QMouseEvent):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.set_background_color(self.HOVER_COLOR)
        super().enterEvent(event)

    def leaveEvent(self, event: QMouseEvent):
        self.unsetCursor() 
        self.set_background_color(self.NORMAL_COLOR)
        super().leaveEvent(event)

# ----------------------------------------------------------------------
# 2. 메인 메뉴 화면 (MainMenu)
# ----------------------------------------------------------------------
class MainMenu(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setWindowFlag(Qt.FramelessWindowHint) 
        self.setGeometry(0, 0, flag['SCREEN_WIDTH'], flag['SCREEN_HEIGHT']) 
        self.setFixedSize(flag['SCREEN_WIDTH'], flag['SCREEN_HEIGHT']) 
        self.initUI()
    
    def setup_background(self):
        """배경 이미지를 QLabel에 로드하고 윈도우 전체 크기로 설정합니다."""
        self.background_label = QLabel(self)
        pixmap = QPixmap(flag['BACKGROUND_IMAGE_PATH'])
        scaled_pixmap = pixmap.scaled(QSize(flag['SCREEN_WIDTH'], flag['SCREEN_HEIGHT']), 
                                     Qt.IgnoreAspectRatio, 
                                     Qt.SmoothTransformation)
        self.background_label.setPixmap(scaled_pixmap)
        self.background_label.setGeometry(0, 0, flag['SCREEN_WIDTH'], flag['SCREEN_HEIGHT'])

    
    def create_buttons(self):
        """ClickableLabel과 QPushButton을 생성하고 정렬합니다."""
        
        # 메인 버튼 (ClickableLabel)
        self.btn1 = self.create_mode_label(
            flag['BUTTON_LABELS'][0], flag['BUTTON1_X'], flag['BUTTON1_Y'],
            flag['BUTTON_WIDTH'], flag['BUTTON_HEIGHT'], font_size=20, border_radius=58
        )
        self.btn2 = self.create_mode_label(
            flag['BUTTON_LABELS'][1], flag['BUTTON2_X'], flag['BUTTON1_Y'],
            flag['BUTTON_WIDTH'], flag['BUTTON_HEIGHT'], font_size=20, border_radius=58
        )
        self.btn3 = self.create_mode_label(
            flag['BUTTON_LABELS'][2], flag['BUTTON3_X'], flag['BUTTON1_Y'],
            flag['BUTTON_WIDTH'], flag['BUTTON_HEIGHT'], font_size=20, border_radius=58
        )

        # 우측 하단 종료 버튼 (QPushButton)
        self.btn_exit = self.create_custom_button(
            "", flag['BUTTON_EXIT_X'], flag['BUTTON_EXIT_Y'], 
            flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'],
            bg_color="transparent"
        )
        self.btn_exit.setObjectName("BottomRightIcon")
        
        # 아이콘 이미지 설정 및 크기 조정
        icon_path = flag['BUTTON_EXIT_IMAGE_PATH']
        icon_pixmap = QPixmap(icon_path)
        icon_size = QSize(
            int(flag['BUTTON_EXIT_WIDTH'] * 0.8), 
            int(flag['BUTTON_EXIT_HEIGHT'] * 0.8)
        )
        scaled_icon = icon_pixmap.scaled(
            icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.btn_exit.setIcon(QIcon(scaled_icon))
        self.btn_exit.setIconSize(scaled_icon.size())

        # 우측 하단 버튼 고유 스타일시트 적용 (커서 설정은 제외)
        unique_style = f"""
            QPushButton#BottomRightIcon {{
                background-color: transparent; border-radius: 20px; border: none; color: transparent;
            }}
            QPushButton#BottomRightIcon:hover {{
                background-color: rgba(255, 255, 255, 0.2); 
            }}
            QPushButton#BottomRightIcon:pressed {{
                background-color: rgba(255, 255, 255, 0.4); 
            }}
        """
        self.btn_exit.setStyleSheet(self.btn_exit.styleSheet() + unique_style)

        # 🚀 문제 해결 부분: setCursor를 이용해 커서를 직접 강제 적용 🚀
        self.btn_exit.setCursor(QCursor(Qt.PointingHandCursor))


        # 버튼 클릭 시 동작 연결
        self.btn1.clicked.connect(self.game1)
        self.btn2.clicked.connect(self.game2)
        self.btn3.clicked.connect(self.game3)
        self.btn_exit.clicked.connect(self.exit)

    def create_custom_button(self, text, x, y, width, height, font_size=20, border_radius=58, bg_color=flag['BUTTON_COLOR']):
        """QPushButton (우측 하단 아이콘용)을 생성하고 스타일을 설정합니다."""
        button = QPushButton(text, self)
        button.setGeometry(x, y, width, height)
        style = f"""
            QPushButton {{
                background-color: {bg_color}; color: #343a40; border-radius: {border_radius}px; 
                font-family: 'Jalnan Gothic', 'Arial', sans-serif; font-size: {font_size}pt; font-weight: light; border: none;
            }}
        """
        button.setStyleSheet(style)
        return button

    def create_mode_label(self, text, x, y, width, height, font_size=20, border_radius=58):
        """ClickableLabel을 생성하고 QPushButton 스타일을 모방하여 적용합니다."""
        label = ClickableLabel(text, self)
        label.setGeometry(x, y, width, height)
        
        # QPushButton 기본 스타일 모방
        style = f"""
            ClickableLabel {{
                background-color: {ClickableLabel.NORMAL_COLOR}; /* 초기 상태 투명 */
                color: #343a40; 
                border-radius: {border_radius}px;
                font-family: 'Jalnan Gothic', 'Arial', sans-serif;
                font-size: {font_size}pt; 
                font-weight: light;
            }}
        """
        label.setStyleSheet(style)
        
        return label

    def initUI(self):
        self.setup_background()
        self.create_buttons()

    def game1(self):
        """1:1 표정 대결 모드 시작 (Index 1)"""
        self.stacked_widget.widget(1).start_video_streams()
        self.stacked_widget.setCurrentIndex(1)
            
    def game2(self):
        """이모지 매칭 모드 시작 (Index 3)"""
        self.stacked_widget.setCurrentIndex(3)
        if hasattr(self.stacked_widget.widget(3), 'start_stream'):
            self.stacked_widget.widget(3).start_stream()
    
    def game3(self):
        """이모지 매칭 모드 시작 (Index 4)"""
        self.stacked_widget.setCurrentIndex(4)
        if hasattr(self.stacked_widget.widget(4), 'start_stream'):
            self.stacked_widget.widget(4).start_stream()
    
    def exit(self):
        """프로그램 종료"""
        QApplication.quit()