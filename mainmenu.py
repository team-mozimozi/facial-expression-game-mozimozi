import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize
# QPropertyAnimation, QEasingCurve, pyqtProperty는 현재 사용되지 않으므로 제거합니다.
# import random

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
# ===============================================
# 새로운 화면 클래스 정의
# ===============================================

class GameScreen(QWidget):
    """'게임 시작' 버튼 클릭 시 나타날 화면"""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window # 메인 윈도우 참조 저장
        self.setWindowTitle("게임 화면")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: darkgreen;") # 배경색으로 구분
        
        layout = QVBoxLayout()
        label = QLabel("게임 진행 화면입니다!", self)
        # 게임 화면 텍스트 폰트 설정
        label.setFont(QFont('Malgun Gothic', 50, QFont.Bold))
        label.setStyleSheet("color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # 메인으로 돌아가는 버튼 추가
        back_button = QPushButton("메인으로 돌아가기", self)
        back_button.setFont(QFont('Malgun Gothic', 30, QFont.Bold))
        back_button.setStyleSheet("background-color: #333333; color: white; padding: 20px;")
        back_button.clicked.connect(self.go_to_main)
        layout.addWidget(back_button)

        self.setLayout(layout)

    def go_to_main(self):
        """메인 윈도우를 다시 표시하고 현재 화면을 숨깁니다."""
        self.hide()
        self.main_window.show()


class SettingScreen(QWidget):
    """'설정' 버튼 클릭 시 나타날 화면"""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window # 메인 윈도우 참조 저장
        self.setWindowTitle("설정 화면")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: darkblue;") # 배경색으로 구분
        
        layout = QVBoxLayout()
        label = QLabel("설정 화면입니다!", self)
        # 설정 화면 텍스트 폰트 설정
        label.setFont(QFont('Malgun Gothic', 50, QFont.Bold))
        label.setStyleSheet("color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # 메인으로 돌아가는 버튼 추가
        back_button = QPushButton("메인으로 돌아가기", self)
        back_button.setFont(QFont('Malgun Gothic', 30, QFont.Bold))
        back_button.setStyleSheet("background-color: #333333; color: white; padding: 20px;")
        back_button.clicked.connect(self.go_to_main)
        layout.addWidget(back_button)

        self.setLayout(layout)

    def go_to_main(self):
        """메인 윈도우를 다시 표시하고 현재 화면을 숨깁니다."""
        self.hide()
        self.main_window.show()

# ===============================================
# 메인 윈도우 클래스 (이미지 로드 대체 코드 제거됨)
# ===============================================
class GameMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("게임 메인 화면")
        
        # 1. 전체화면 (1920x1080) 설정 및 프레임리스 모드 적용
        self.setWindowFlag(Qt.FramelessWindowHint) 
        self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT) 
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT) 
        
        # 다른 화면 인스턴스 저장할 변수
        self.game_screen = None
        self.setting_screen = None
        
        self.init_ui()
        # 다른 화면 인스턴스 생성
        self.create_screens() 

    def create_screens(self):
        """이동할 화면들을 미리 생성합니다."""
        # 생성 시 자신의 인스턴스(self)를 전달하여 돌아올 때 사용하도록 합니다.
        self.game_screen = GameScreen(self)
        self.setting_screen = SettingScreen(self)
        # 생성된 다른 화면들은 처음엔 숨겨둡니다.
        self.game_screen.hide()
        self.setting_screen.hide()

    def init_ui(self):
        # 2. 배경 이미지 설정
        self.setup_background()
        
        # 3. 버튼 배치
        self.create_buttons()
    
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
        self.background_label.lower() # 다른 위젯들보다 아래에 위치하도록


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
        self.btn1.clicked.connect(lambda: self.button_action(BUTTON_LABELS[0]))
        self.btn2.clicked.connect(lambda: self.button_action(BUTTON_LABELS[1]))
        self.btn3.clicked.connect(lambda: self.button_action(BUTTON_LABELS[2]))
        
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

    def button_action(self, button_name):
        """버튼 클릭 시 실행될 화면 이동 로직"""
        print(f"'{button_name}' 버튼이 클릭되었습니다.")
        
        if button_name == BUTTON_LABELS[0]:
            self.hide() # 현재 메인 화면 숨기기
            self.game_screen.show() # 게임 화면 표시
        elif button_name == BUTTON_LABELS[1]:
            self.hide() # 현재 메인 화면 숨기기
            self.setting_screen.show()
        elif button_name == BUTTON_LABELS[2]:
            self.hide() # 현재 메인 화면 숨기기
            self.game_screen.show() # 게임 화면 표시
        elif button_name == "EXIT":
            QApplication.instance().quit()


# ===============================================
# 메인 실행부
# ===============================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 이미지 로드 실패 시 디버깅을 돕기 위해 리소스 검색 경로를 추가할 수 있습니다.
    # 예: QDir.addSearchPath('design', 'facial-expression-game-mozimozi/design')
    main_window = GameMainWindow()
    main_window.show()
    sys.exit(app.exec_())
