import sys
import cv2 
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont


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
        title = QLabel('감정에 맞는 표정 짓기 게임')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 50px; font-weight: bold;")
        title.setFont(QFont('나눔고딕', 24))

        game1_btn = QPushButton('1:1 표정 대결')
        game2_btn = QPushButton('이모지 매칭 모드')
        
        fixed_width, fixed_height = 400, 70
        button_style = "font-size: 24px; padding: 10px; margin: 10px;"
        game1_btn.setFixedSize(fixed_width, fixed_height)
        game2_btn.setFixedSize(fixed_width, fixed_height)
        
        game1_btn.setStyleSheet(button_style)
        game2_btn.setStyleSheet(button_style)
        
        game1_btn.clicked.connect(self.game1)
        game2_btn.clicked.connect(self.game2) 

        h_layout_game1 = QHBoxLayout()
        h_layout_game1.addStretch(1)
        h_layout_game1.addWidget(game1_btn)
        h_layout_game1.addStretch(1)

        h_layout_game2 = QHBoxLayout()
        h_layout_game2.addStretch(1)
        h_layout_game2.addWidget(game2_btn)
        h_layout_game2.addStretch(1)
        
        main_layout.addWidget(title)
        main_layout.addStretch(1)
        main_layout.addLayout(h_layout_game1)
        main_layout.addLayout(h_layout_game2)
        main_layout.addStretch(1)
        
        self.setLayout(main_layout)

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