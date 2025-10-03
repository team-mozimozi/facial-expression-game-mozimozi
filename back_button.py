from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QMouseEvent

# 표준 버튼 상수 정의 (109x101, 마진 20)
# 화면 크기 1920x1080 기준
BTN_WIDTH = 109
BTN_HEIGHT = 101
BTN_MARGIN = 20
BTN_X = 1920 - BTN_WIDTH - BTN_MARGIN  # 1791
BTN_Y = 1080 - BTN_HEIGHT - BTN_MARGIN # 959

class ClickableButton(QPushButton):
    """
    우측 하단에 배치되는 표준화된 버튼(109x101)입니다.
    마우스를 올리면 포인팅 핸드 커서가 나타나며,
    배경은 투명하고 테두리가 없습니다.
    """
    def __init__(self, parent, icon_path, connect_func):
        super().__init__("", parent)
        
        # 1. 크기 및 위치 설정 (우측 하단 표준)
        self.setGeometry(BTN_X, BTN_Y, BTN_WIDTH, BTN_HEIGHT)
        
        # 2. 기능 연결
        self.clicked.connect(connect_func)
        
        # 3. 스타일 및 아이콘 설정
        icon_pixmap = QPixmap(icon_path)
        icon_size = QSize(BTN_WIDTH, BTN_HEIGHT)
        scaled_icon = icon_pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.setIcon(QIcon(scaled_icon))
        self.setIconSize(icon_size)
        self.setStyleSheet("background-color: transparent; border: none;")

    def enterEvent(self, event: QMouseEvent):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event: QMouseEvent):
        self.unsetCursor() 
        super().leaveEvent(event)

# 메인 메뉴 버튼 생성을 위한 헬퍼 함수
def create_main_menu_button(parent_widget, flag_dict, connect_func):
    """주어진 위젯의 우측 하단에 메인 메뉴 버튼을 생성합니다."""
    return ClickableButton(
        parent_widget, 
        flag_dict['MAIN_BUTTON_IMAGE'], 
        connect_func
    )

# 종료 버튼 생성을 위한 헬퍼 함수
def create_exit_button(parent_widget, flag_dict, connect_func):
    """주어진 위젯의 우측 하단에 종료 버튼을 생성합니다."""
    return ClickableButton(
        parent_widget, 
        flag_dict['BUTTON_EXIT_IMAGE_PATH'], 
        connect_func
    )