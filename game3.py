import cv2
import random
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QMessageBox, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QPointF
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QMouseEvent, QPainter, QPainterPath, QColor, QCursor, QPen, QBrush
from compare import calc_similarity
from mainmenu import flag
from back_button import create_main_menu_button
from multiprocessing import Queue, Manager, Process

import numpy as np

# 1. 텍스트 테두리 기능을 위한 사용자 정의 QLabel 클래스
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
        y = rect.top() + (rect.height() - text_height) // 2 + fm.ascent()

        # X 위치 계산: 정렬에 따라 조정
        x = 0
        if self.alignment() & Qt.AlignLeft:
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
        base_size = super().sizeHint()
        compensation = int(self.outline_width * 2)
        new_width = base_size.width() + compensation
        new_height = base_size.height() + compensation
        return QSize(new_width, new_height)

# ClickableLabel 도우미 클래스 재사용
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event: QMouseEvent):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event: QMouseEvent):
        self.unsetCursor()
        super().leaveEvent(event)

# 유사도를 계산할 Worker함수
def similarity_worker(item_queue, similarity_value):
    while True:
        item = item_queue.get()
        if item is None:
            print("Queue empty!")
            continue
        # frame queue에 값이 들어올 때까지 대기
        frame, emoji = item
        if frame is None:
            print(f"Worker terminated.")
            break
        try:
            # 들어온 프레임으로 유사도 계산
            similarity_value.value = 0 if emoji == "" else calc_similarity(frame, emoji)
        except:
            print("유사도 계산 실패!")

# 웹캠 스트림 처리 스레드 (TimeAttack 모드 전용)
class TimeAttackThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    signal_ready = pyqtSignal()

    def __init__(self, item_queue, camera_index, emotion_file, width=flag['VIDEO_WIDTH'], height=flag['VIDEO_HEIGHT']):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
        self.width = width
        self.height = height
        self.emotion_file = emotion_file
        self.frame_count = 0
        self.inference_interval = 3
        self.item_queue = item_queue

    def set_emotion_file(self, new_emotion_file):
        self.emotion_file = new_emotion_file

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}.")
            self.running = False
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        TARGET_FPS = 30.0
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        self.signal_ready.emit()

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_count += 1
                if self.frame_count % self.inference_interval == 0:
                    self.item_queue.put((frame, self.emotion_file))
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)

                self.change_pixmap_signal.emit(p)
            self.msleep(50)
        if cap.isOpened():
             cap.release()

    def stop(self):
        self.running = False
        self.wait()


# 게임 결과 GUI
class Result3screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.total_text = " "
        # self.current_accuracy_text 변수 제거
        self.game_started = False
        self.initUI()
        
    def create_custom_button(self, text, x, y, width, height, font_size=20, border_radius=58, bg_color=flag['BUTTON_COLOR']):
        """Resultscreen에서 가져온 QPushButton 생성 및 스타일 설정 함수"""
        button = QPushButton(text, self)
        button.setGeometry(x, y, width, height)
        style = f"""
            QPushButton {{
                background-color: {bg_color}; color: #343A40; border-radius: {border_radius}px;
                font-family: 'Jalnan Gothic', 'Arial', sans-serif; font-size: {font_size}pt; font-weight: light; border: none;
            }}
        """
        button.setStyleSheet(style)
        return button

    # Resultscreen의 create_exit_button 로직 (QPushButton, setGeometry)
    def create_exit_button(self):
        # 우측 하단 종료 버튼 (QPushButton) 생성
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
        
        # 우측 하단 버튼 고유 스타일시트 적용
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
        
        # 커서 설정
        self.btn_exit.setCursor(QCursor(Qt.PointingHandCursor))
        
        # 클릭 시 메인 메뉴로 돌아가는 기능 연결
        self.btn_exit.clicked.connect(self.main_menu_button)
        
        return self.btn_exit

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.addSpacing(30) 
        
        # Resultscreen의 result_title 디자인/위치와 동일
        self.result_title = QLabel("게임 종료!")
        self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        
        # total_label이 Resultscreen의 winner_label의 역할과 디자인을 대신함
        # Resultscreen의 winner_label 초기 디자인: Font('Jalnan 2', 60), AlignCenter
        self.total_label = QLabel("결과 계산 중...") # 초기 텍스트를 Resultscreen의 winner_label과 유사하게 설정
        self.total_label.setFont(QFont('Jalnan 2', 60)) 
        self.total_label.setStyleSheet("color: black;") # 초기 색상
        self.total_label.setAlignment(Qt.AlignCenter)
        
        # current_accuracy_label 제거

        # Resultscreen 방식의 종료 버튼 추가 (setGeometry 방식)
        self.create_exit_button()

        # Resultscreen의 레이아웃 간격 비율 적용: (addStretch 5, title, addStretch 1, winner_label, addStretch 6)
        self.layout.addStretch(5) 
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.total_label) # winner_label 역할
        
        # winner_label 이후의 간격 (Resultscreen에서는 6)
        self.layout.addStretch(6) 
        
        self.layout.addSpacing(10) 
        
        self.setLayout(self.layout)

    def set_results3(self, total_score):
        # total_label 업데이트 (Resultscreen의 winner_label 최종 디자인/폰트 크기 50 적용)
        self.total_text = f"🎉 {total_score}개 맞추셨습니다! 🎉"
        
        current_font = self.total_label.font()
        current_font.setPointSize(50) # Resultscreen의 winner_label 최종 폰트 크기 적용
        self.total_label.setFont(current_font)
        
        # Resultscreen의 winner_label은 승리 시 'blue'를 사용하므로, 결과 표시에는 'blue'를 사용
        self.total_label.setStyleSheet("color: blue;") 
        
        self.total_label.setText(self.total_text)

    def main_menu_button(self):
        self.stacked_widget.setCurrentIndex(0)
        return
    
# 게임 3 GUI
class Game3Screen(QWidget):
    game_finished = pyqtSignal(int)
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_thread = None
        self.EMOJI_DIR = "img/emoji"
        # FileNotFoundError 처리를 여기서 진행하지 않고 원본 코드 구조 유지
        self.emotion_files = [
            f for f in os.listdir(self.EMOJI_DIR)
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')
        ]

        # Manager 객체를 인스턴스 멤버 변수로 선언하여 AttributeError 해결
        self.manager = Manager() 
        
        # self.manager를 사용하여 공유 값 및 Queue를 생성
        self.current_accuracy = self.manager.Value(float, 0.0)
        
        self.current_emotion_file = ""
        self.total_score = 0
        self.target_similarity = 70.0
        self.is_transitioning = False
        self.transition_delay_ms  = 1000
        self.total_game_time = 60
        self.time_left = self.total_game_time
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.game_started = False

        # 유사도 계산을 위한 worker와 queue
        self.similarity_worker = None
        # self.manager.Queue()를 사용하여 프로세스 간 통신을 확보
        self.item_queue = self.manager.Queue() 

        # 클린 종료를 위한 이벤트 객체 추가
        self.stop_event = self.manager.Event()

        # 성공 이미지 오버레이 관련 멤버 변수
        self.success_image_path = "design/o.png"
        self.success_overlay = QLabel(self) # 초기에는 self (Game3Screen)의 자식으로 설정
        self.success_overlay.setStyleSheet("background-color: transparent;")
        self.success_timer = QTimer(self)
        self.success_timer.setSingleShot(True)
        self.success_timer.timeout.connect(self.hide_success_overlay)
        # 1초 후 complete_transition이 호출되므로, success_overlay는 여기서 1초 후 숨기면 됩니다.
    
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # --- 1. 상단 바 영역 (고정) ---
        # ----------------------------------------------------------------------
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
        mode1_bar.setObjectName("mode_bar_label")
        mode1_bar.setStyleSheet("background-color: #FFE10A;")

        mode1_bar.setFixedHeight(85)
        mode1_bar.setFixedWidth(1920)
        main_layout.addWidget(mode1_bar)

        # 타이틀 / 메뉴 버튼 레이아웃 (고정)
        top_h_layout = QHBoxLayout()
        title = QLabel("60초 내에 가능한 한 많은 이모지를 따라 해보세요!")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.back_btn = create_main_menu_button(self, flag, self.go_to_main_menu)

        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)

        main_layout.addLayout(top_h_layout)

        # ----------------------------------------------------------------------
        # --- 2. 웹캠/이모지 중앙 컨텐츠 영역 (위치 조정) ---
        # ----------------------------------------------------------------------

        # 수직 중앙 정렬을 위해 stretch 추가
        main_layout.addStretch(1)

        # 1. 이모지 + 타이머 + 점수 컨테이너 (우측 고정 너비)
        emoji_v_container = QWidget()
        emoji_v_container.setFixedWidth(550)

        emoji_layout = QVBoxLayout(emoji_v_container)
        emoji_layout.setContentsMargins(0, 0, 0, 0)
        # 수직 중앙 정렬을 위해 stretch 추가
        emoji_layout.addStretch(1)

        # 타이머 레이블
        timer_font = QFont('Jalnan 2', 40)
        timer_fill_color = QColor("#0AB9FF")
        timer_outline_color = QColor("#00A4F3")
        timer_outline_width = 2.0
        self.timer_label = OutlinedLabel(
            f"{self.total_game_time}", timer_font, timer_fill_color, timer_outline_color, timer_outline_width, alignment=Qt.AlignCenter
        )
        self.timer_label.setStyleSheet("color: transparent;")
        self.timer_label.hide()

        # 이모지/시작 버튼 스택
        self.start_button = ClickableLabel()
        self.start_button.setAlignment(Qt.AlignCenter)
        self.start_button.setFixedSize(240, 240)
        self.start_button.clicked.connect(self.start_game)
        self.start_button.setStyleSheet("padding-top: 40px;")
        start_pixmap = QPixmap(flag['START_BUTTON_IMAGE'])
        if not start_pixmap.isNull():
            self.start_button.setPixmap(start_pixmap.scaled(self.start_button.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.emotion_label = QLabel("표정 이미지 준비 중...")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(240, 240)
        self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;")
        self.center_widget = QWidget()
        center_stack_layout = QStackedWidget(self.center_widget)
        center_stack_layout.addWidget(self.emotion_label)
        center_stack_layout.addWidget(self.start_button)
        center_stack_layout.setCurrentWidget(self.start_button)
        self.center_widget.setFixedSize(240, 240)

        self.pass_button = QPushButton("PASS") # 텍스트를 "PASS"로 변경
        self.pass_button.setFont(QFont('Jalnan 2', 24, QFont.Bold))
        self.pass_button.setFixedSize(200, 70)
        self.pass_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5CA7; 
                color: white; 
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #FF77BB;
            }
        """)
        self.pass_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.pass_button.clicked.connect(self.pass_emotion) # pass_emotion 기능 연결
        self.pass_button.hide()

        # 스코어 레이블
        score_font = QFont('ARCO', 40)
        score_color = QColor("#F85E6F")
        score_line_color = QColor("#9565B4")
        score_outline_width = 3.0
        self.score_label = OutlinedLabel(
            f"SCORE: {self.total_score}", score_font, score_color, score_line_color, score_outline_width, alignment=Qt.AlignCenter
        )
        self.score_label.hide()

        # 이모지 컨테이너 레이아웃 구성
        emoji_layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        emoji_layout.addSpacing(10)
        emoji_layout.addWidget(self.center_widget, alignment=Qt.AlignCenter)
        emoji_layout.addSpacing(10) # 이모지 스택과 버튼 사이 간격 추가
        emoji_layout.addWidget(self.pass_button, alignment=Qt.AlignCenter) # 중앙 정렬
        emoji_layout.addSpacing(10) # 버튼과 스코어 레이블 사이 간격 추가
        emoji_layout.addSpacing(20)
        emoji_layout.addWidget(self.score_label, alignment=Qt.AlignCenter)
        # 수직 중앙 정렬을 위해 stretch 추가
        emoji_layout.addStretch(1)

        # 2. 웹캠 + PLAYER + 유사도 컨테이너 (좌측 고정 너비)
        video_score_layout = QVBoxLayout()
        video_score_layout.setSpacing(10)
        video_score_container = QWidget()
        video_score_container.setFixedWidth(flag['VIDEO_WIDTH'] + 20) # 660
        video_score_container.setLayout(video_score_layout)

        # Player Label
        player_font = QFont('ARCO', 50)
        player_fill_color = QColor("#FFD50A")
        player_outline_color = QColor("#00A4F3")
        player_outline_width = 3.5
        self.player_label = OutlinedLabel(
            "PLAYER", player_font, player_fill_color, player_outline_color, player_outline_width, alignment=Qt.AlignCenter
        )

        # Video Label
        self.video_label = QLabel(f"웹캠 피드 ({flag['VIDEO_WIDTH']}x{flag['VIDEO_HEIGHT']})")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.video_label.setStyleSheet("background-color: black; color: white;")
        
        # [추가] success_overlay 초기 설정
        # video_label이 배치된 후에 success_overlay를 video_label의 자식으로 재설정하고 위치를 잡습니다.
        self.success_overlay.setParent(self.video_label)
        self.success_overlay.setGeometry(0, 0, self.video_label.width(), self.video_label.height())
        self.success_overlay.setAlignment(Qt.AlignCenter)
        self.success_overlay.setScaledContents(True)
        self.success_overlay.hide()
        
        # success_overlay에 이미지 로드
        pixmap_o = QPixmap(self.success_image_path)
        if not pixmap_o.isNull():
            # 웹캠 크기에 맞게 스케일링하거나 원하는 크기로 설정
            scaled_pixmap = pixmap_o.scaled(
                self.video_label.size() * 0.5, # 웹캠 크기의 50%로 설정 (원하는 크기로 변경 가능)
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.success_overlay.setPixmap(scaled_pixmap)
            # 오버레이의 크기를 이미지 크기에 맞게 설정하여 중앙에 위치하도록 조정
            self.success_overlay.setFixedSize(scaled_pixmap.size())
            # 부모 위젯 (video_label)의 중앙에 위치하도록 이동
            x = (self.video_label.width() - self.success_overlay.width()) // 2
            y = (self.video_label.height() - self.success_overlay.height()) // 2
            self.success_overlay.move(x, y)
        else:
            self.success_overlay.setText("O") # 이미지 로드 실패 시 대체 텍스트
            self.success_overlay.setStyleSheet("font-size: 100px; color: green; background-color: rgba(0,0,0,100);")

        # Accuracy Labels
        self.current_accuracy_label = QLabel(f'현재 유사도: {self.current_accuracy.value: .2f}%')
        self.current_accuracy_label.setFont(QFont('Jalnan Gothic', 25))
        self.current_accuracy_label.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 15px;")
        self.current_accuracy_label.setAlignment(Qt.AlignCenter)

        self.target_label = QLabel(f'목표 유사도: {self.target_similarity:.0f}%')
        self.target_label.setFont(QFont('Jalnan Gothic', 25))
        self.target_label.setStyleSheet("background-color: 'transparent'; color: #292E32;")
        self.target_label.setAlignment(Qt.AlignCenter)

        # 웹캠 컨테이너 레이아웃 구성
        # 수직 중앙 정렬을 위해 stretch 추가
        video_score_layout.addStretch(1)
        video_score_layout.addWidget(self.player_label)
        video_score_layout.addWidget(self.video_label)
        video_score_layout.addWidget(self.current_accuracy_label)
        video_score_layout.addWidget(self.target_label)
        # 수직 중앙 정렬을 위해 stretch 추가
        video_score_layout.addStretch(1)

        # 3. 중앙 컨텐츠를 수평 중앙에 배치

        # 중앙 컨텐츠 (웹캠 + 이모지)를 담을 QHBoxLayout
        center_content_h_layout = QHBoxLayout()
        center_content_h_layout.addStretch(1) # 좌측 여백 (수평 중앙 정렬을 위해)
        center_content_h_layout.addWidget(video_score_container)
        center_content_h_layout.addSpacing(10)
        center_content_h_layout.addWidget(emoji_v_container)
        center_content_h_layout.addStretch(1) # 우측 여백 (수평 중앙 정렬을 위해)

        # 중앙 컨텐츠 레이아웃을 메인 레이아웃에 추가
        main_layout.addLayout(center_content_h_layout)

        # 수직 중앙 정렬을 위해 stretch 추가
        main_layout.addStretch(2)

        # QWidget 기반 레이아웃 적용
        self.setLayout(main_layout)
        self.setGeometry(-10, -10, flag['SCREEN_WIDTH']+20, flag['SCREEN_HEIGHT']+20)


    # 이하 게임 로직 및 헬퍼 함수는 동일하게 유지됨
    def start_game(self):
        if self.game_started:
            return
        self.game_started = True
        self.set_next_emotion()
        self.center_widget.findChild(QStackedWidget).setCurrentWidget(self.emotion_label)
        self.timer_label.show()
        self.score_label.show()
        self.pass_button.show()
        self.time_left = self.total_game_time
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.repaint()
        self.game_timer.start(1000)

    def set_next_emotion(self):
        if not self.emotion_files: return
        available_emotions = [f for f in self.emotion_files if f != self.current_emotion_file]
        if not available_emotions: available_emotions = self.emotion_files
        self.current_emotion_file = random.choice(available_emotions)
        self.video_thread.set_emotion_file(self.current_emotion_file)
        file_path = os.path.join(self.EMOJI_DIR, self.current_emotion_file)
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {self.current_emotion_file}")
        else:
            scaled_pixmap = pixmap.scaled(self.emotion_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.emotion_label.setPixmap(scaled_pixmap)
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.set_emotion_file(self.current_emotion_file)

    def pass_emotion(self):
        """
        PASS 버튼 클릭 시 호출됩니다.
        현재 이모지를 성공한 것으로 간주하고 점수를 획득하며 다음 이모지로 전환합니다.
        """
        if not self.game_started or self.is_transitioning:
            return
            
        # 유사도 달성과 동일한 전환 로직 시작
        self.is_transitioning = True
        QTimer.singleShot(self.transition_delay_ms, self.complete_transition) # 딜레이 후 다음 이모지로 전환

    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"{self.time_left}")
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.fill_color = QColor("#FF1E0A")
            self.timer_label.outline_color = QColor("#FFF315")
        else:
            self.timer_label.fill_color = QColor("#0AB9FF")
            self.timer_label.outline_color = QColor("#00A4F3")
        self.timer_label.repaint()
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_stream()
            self.timer_label.setText("게임 종료!")
            self.game_started = False
            self.stacked_widget.findChild(Result3screen).set_results3(self.total_score)
            self.stacked_widget.setCurrentIndex(5)

    def show_success_overlay(self):
        self.success_overlay.show()
        # 1초 후에 hide_success_overlay 호출
        self.success_timer.start(self.transition_delay_ms) 

    def hide_success_overlay(self):
        self.success_overlay.hide()

    def update_image_and_score(self, image):
        if not self.is_transitioning:
            pixmap = QPixmap.fromImage(image)
            self.video_label.setPixmap(pixmap)
            self.current_accuracy_label.setText(f'현재 유사도: {self.current_accuracy.value: .2f}%')
            if self.current_accuracy.value >= self.target_similarity:
                self.is_transitioning = True
                self.total_score += 1
                self.score_label.setText(f"SCORE: {self.total_score}")
                self.video_thread.emotion_file = ""
                while not self.item_queue.empty():
                    try:
                        self.item_queue.get_nowait()
                    except:
                        break
                self.show_success_overlay()
                QTimer.singleShot(self.transition_delay_ms, self.complete_transition)

    def complete_transition(self):
        self.set_next_emotion()
        self.current_accuracy.value = 0.0
        self.video_label.setStyleSheet("border: none;")
        self.is_transitioning = False

    def get_available_camera_index(self):
        for index in range(10):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                return index
        return 0

    def start_similarity_worker(self):
        if not self.similarity_worker:
            self.stop_event.clear() # 새 게임 시작 전 이벤트 초기화 (보험용)
            self.similarity_worker = Process(target=similarity_worker, args=(self.item_queue, self.current_accuracy))
        if self.similarity_worker and not self.similarity_worker.is_alive():
            self.similarity_worker.start()
        self.video_thread.signal_ready.disconnect(self.start_similarity_worker)
        

    def start_stream(self):
        self.stop_stream()
        self.current_emotion_file = ""
        self.total_score = 0
        self.score_label.setText(f"SCORE: {self.total_score}")
        self.video_thread = TimeAttackThread(
            item_queue=self.item_queue,
            camera_index=self.get_available_camera_index(),
            emotion_file=self.current_emotion_file,
            width=flag['VIDEO_WIDTH'],
            height=flag['VIDEO_HEIGHT']
        )
        self.video_thread.change_pixmap_signal.connect(self.update_image_and_score)
        self.video_thread.signal_ready.connect(self.start_similarity_worker)
        self.video_thread.start()

    def stop_stream(self):
        if self.game_timer.isActive():
            self.game_timer.stop()
        if self.video_thread and self.video_thread.isRunning():
            try:
                self.video_thread.change_pixmap_signal.disconnect(self.update_image_and_score)
            except Exception: pass
            self.video_thread.stop()
            self.video_thread.wait()
            self.video_thread = None
            
        # 클린 종료 로직 적용: None 신호를 큐에 넣어 worker를 깨우고 종료
        if self.similarity_worker and self.similarity_worker.is_alive():
            # 큐에 None 신호를 넣어 blocking된 worker를 깨우고 exit합니다.
            self.item_queue.put((None, None))
            # worker가 종료되기를 기다립니다. (timeout 1초)
            self.similarity_worker.join(timeout=1) 
            # 1초 후에도 살아있다면 강제 종료 (보험)
            if self.similarity_worker.is_alive():
                self.similarity_worker.terminate()
                
        self.similarity_worker = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self.game_started:
            self.reset_game_state()

    def reset_game_state(self):
        self.game_started = False
        self.center_widget.findChild(QStackedWidget).setCurrentWidget(self.start_button)
        self.emotion_label.hide()
        self.timer_label.hide()
        self.score_label.hide()
        self.pass_button.hide()
        self.score_label.setText(f"SCORE: {0}")
        self.current_accuracy_label.setText(f'현재 유사도: {0.00: .2f}%')
        self.current_accuracy.value = 0.0
        self.video_label.setText(f"웹캠 피드 ({flag['VIDEO_WIDTH']}x{flag['VIDEO_HEIGHT']})")
        self.current_emotion_file = ""
        self.video_label.setPixmap(QPixmap())
        
        # 클린 종료 로직 적용
        if self.similarity_worker and self.similarity_worker.is_alive():
            self.item_queue.put((None, None))
            self.similarity_worker.join(timeout=1)
            if self.similarity_worker.is_alive():
                self.similarity_worker.terminate()

    def go_to_result_screen(self):
        self.stacked_widget.setCurrentIndex(5)

    def go_to_main_menu(self):
        self.stop_stream()
        self.reset_game_state()
        self.stacked_widget.setCurrentIndex(0)