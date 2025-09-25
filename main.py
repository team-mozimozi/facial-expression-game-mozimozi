import sys
import cv2 
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget, QMainWindow
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
from game1 import Game1Screen,Resultscreen
from mainmenu  import MainMenu

# ----------------------------------------------------------------------
# 5. 앱 전환기 역할을 하는 메인 윈도우
# ----------------------------------------------------------------------
class AppSwitcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PyQt 앱 전환기")
        self.setGeometry(100, 100, 900, 750)

        self.stacked_widget = QStackedWidget()
        
        # 각 화면 인스턴스 생성
        self.main_menu = MainMenu(self.stacked_widget)
        self.game1_screen = Game1Screen(self.stacked_widget)
        self.result_screen = Resultscreen(self.stacked_widget)
        
        # QStackedWidget에 화면 추가 (인덱스 순서)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.game1_screen)
        self.stacked_widget.addWidget(self.result_screen)
        
        # 메인 윈도우에 QStackedWidget 설정
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(central_widget)
        
        # 웹캠 스레드 정리
        QApplication.instance().aboutToQuit.connect(self.game1_screen.stop_video_streams)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AppSwitcher()
    ex.show()
    sys.exit(app.exec_())