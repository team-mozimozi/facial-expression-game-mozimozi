import sys
import cv2 
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
# from game1 import Game1Screen # Game1Screen을 직접 import할 필요는 없습니다.

# ----------------------------------------------------------------------
# 4. 메인 메뉴 화면 (MainMenu)
# ----------------------------------------------------------------------
class MainMenu(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 1. 타이틀 설정 (가장 위에 배치될 요소)
        title = QLabel('감정에 맞는 표정 짓기 게임')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 50px; font-weight: bold;")
        title.setFont(QFont('나눔고딕', 24))

        game1_btn = QPushButton('1:1 표정 대결')
        game2_btn = QPushButton('이모지 매칭 모드') # game3_btn 대신 game2_btn 사용
        
        fixed_width, fixed_height = 400, 70
        button_style = "font-size: 24px; padding: 10px; margin: 10px;"
        game1_btn.setFixedSize(fixed_width, fixed_height)
        game2_btn.setFixedSize(fixed_width, fixed_height)
        
        game1_btn.setStyleSheet(button_style)
        game2_btn.setStyleSheet(button_style)
        
        game1_btn.clicked.connect(self.game1)
        game2_btn.clicked.connect(self.game2) 

        # 2. 버튼들을 가로로 배치하는 레이아웃 (QHBoxLayout)
        game_buttons_h_layout = QHBoxLayout()
        game_buttons_h_layout.addStretch(1) 
        game_buttons_h_layout.addWidget(game1_btn)
        game_buttons_h_layout.addWidget(game2_btn) # 버튼을 나란히 추가
        game_buttons_h_layout.addStretch(1)
        
        # 3. 메인 레이아웃 (QVBoxLayout)에 요소 배치
        main_layout.addWidget(title)                 # 타이틀: 맨 위 (Top)
        main_layout.addSpacing(400)                  # 타이틀 아래 작은 고정 간격
        
        main_layout.addLayout(game_buttons_h_layout) #  버튼: 가로 배치된 레이아웃 추가
        
        main_layout.addStretch(10)                   #  큰 비율의 여백: 버튼 아래에 추가하여
                                                     # 타이틀과 버튼을 화면 상단으로 밀어 올립니다.
        
        self.setLayout(main_layout)
        
    def game1(self):
        # Index 1: 1:1 표정 대결
        # 1. Game1Screen 인스턴스 가져오기 (Index 1)
        game1_screen = self.stacked_widget.widget(1)
        
        # 2. start_video_streams 함수를 호출하여 스트리밍 시작
        if hasattr(game1_screen, 'start_video_streams'):
            # 이 부분을 추가/확인해야 합니다
            game1_screen.start_video_streams()
            
        # 3. 화면 전환
        self.stacked_widget.setCurrentIndex(1)
        
    def game2(self):
        # AppSwitcher에서 Game2Screen 인스턴스 (인덱스 3)를 가져옵니다.
        game2_screen = self.stacked_widget.widget(3)
        if game2_screen:
            #화면 전환 전에 미리 보기 스트리밍 시작
            game2_screen.start_stream() 
            self.stacked_widget.setCurrentIndex(3)