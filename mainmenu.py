# ----------------------------------------------------------------------
# 3. 메인 메뉴 화면 (MainMenu)
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
        game3_btn = QPushButton('타임어택 모드')
        
        fixed_width, fixed_height = 400, 70
        button_style = "font-size: 24px; padding: 10px; margin: 10px;"
        game1_btn.setFixedSize(fixed_width, fixed_height)
        game3_btn.setFixedSize(fixed_width, fixed_height)
        game1_btn.setStyleSheet(button_style)
        game3_btn.setStyleSheet(button_style)
        
        game1_btn.clicked.connect(self.game1)
        game3_btn.clicked.connect(lambda: print("타임어택 모드 시작")) 

        h_layout_game1 = QHBoxLayout()
        h_layout_game1.addStretch(1)
        h_layout_game1.addWidget(game1_btn)
        h_layout_game1.addStretch(1)

        h_layout_game3 = QHBoxLayout()
        h_layout_game3.addStretch(1)
        h_layout_game3.addWidget(game3_btn)
        h_layout_game3.addStretch(1)
        
        main_layout.addWidget(title)
        main_layout.addStretch(1)
        main_layout.addLayout(h_layout_game1)
        main_layout.addLayout(h_layout_game3)
        main_layout.addStretch(1)
        
        self.setLayout(main_layout)

    def game1(self):
        # 1. 화면 전환
        self.stacked_widget.setCurrentIndex(1)
        
        # 2. 웹캠 스트리밍 시작
        game1_screen = self.stacked_widget.widget(1)
        game1_screen.start_video_streams()
        
        print("1:1 표정 대결 모드 시작 (웹캠 활성화)")

    def game3(self):
        # 1. 화면 전환
        self.stacked_widget.setCurrentIndex(1)
        
        print("타임어택 모드 시작")