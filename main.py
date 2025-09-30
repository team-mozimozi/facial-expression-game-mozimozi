import sys
import cv2 
import time
#import mediapipe as mp
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget, QMainWindow
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
from game1 import Game1Screen, Resultscreen
from game2 import Game2Screen
from game3 import Game3Screen, Result3screen
from mainmenu  import MainMenu

# ----------------------------------------------------------------------
# 5. 앱 전환기 역할을 하는 메인 윈도우
# ----------------------------------------------------------------------
class AppSwitcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        SCREEN_WIDTH = 1920
        SCREEN_HEIGHT = 1080
        self.setWindowTitle("PyQt 앱 전환기")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.stacked_widget = QStackedWidget()
        
        # 각 화면 인스턴스 생성
        self.main_menu = MainMenu(self.stacked_widget)         # mainmenu 인스턴스
        self.game1_screen = Game1Screen(self.stacked_widget)   # game1Screen 인스턴스 
        self.result1_screen = Resultscreen(self.stacked_widget) # game1Result 
        self.game2_screen = Game2Screen(self.stacked_widget)   # game2Screen 인스턴스
        self.game3_screen = Game3Screen(self.stacked_widget)   # game2Screen 인스턴스
        self.result3_screen = Result3screen(self.stacked_widget)   # game2Screen 인스턴스
        
        
        # QStackedWidget에 화면 추가 (인덱스 순서)
        self.stacked_widget.addWidget(self.main_menu)         #Index 0
        self.stacked_widget.addWidget(self.game1_screen)      #Index 1
        self.stacked_widget.addWidget(self.result1_screen)     #Index 2
        self.stacked_widget.addWidget(self.game2_screen)      #Index 3
        self.stacked_widget.addWidget(self.game3_screen)
        self.stacked_widget.addWidget(self.result3_screen)
        
        
        # 메인 윈도우에 QStackedWidget 설정
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(central_widget)
        
        # 웹캠 스레드 정리
        QApplication.instance().aboutToQuit.connect(self.game1_screen.stop_video_streams)
        
        # ⭐ CRASH FIX: closeEvent 핸들러를 추가하여 앱 종료 시 안전하게 스레드 종료
    def closeEvent(self, event):
        """메인 창이 닫힐 때 모든 스레드를 안전하게 종료합니다."""
        print("메인 창 닫힘 감지: 모든 스레드 종료 요청")
        
        if hasattr(self.game2_screen, 'stop_video_streams'):
            self.game1_screen.stop_video_streams()
            
        event.accept() # 이벤트를 승인하여 창 닫기를 계속 진행합니다.
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AppSwitcher()
    ex.show()
    sys.exit(app.exec_())