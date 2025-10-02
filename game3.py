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
from mainmenu import flag # 원본 임포트 유지

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


# 웹캠 스트림 처리 스레드 (TimeAttack 모드 전용)
class TimeAttackThread(QThread):
    change_pixmap_score_signal = pyqtSignal(QImage, float)

    def __init__(self, camera_index, emotion_file, width=flag['VIDEO_WIDTH'], height=flag['VIDEO_HEIGHT']):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
        self.width = width
        self.height = height
        self.emotion_file = emotion_file
        self.frame_count = 0
        self.inference_interval = 3
        self.similarity = 0

    def set_emotion_file(self, new_emotion_file):
        self.emotion_file = new_emotion_file

    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}.")
            self.running = False
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        TARGET_FPS = 30.0
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_count += 1
                if self.frame_count % self.inference_interval == 1:
                    self.similarity = calc_similarity(frame, self.emotion_file)
                    self.frame_count = 0
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)

                self.change_pixmap_score_signal.emit(p, self.similarity)
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
        self.game_started = False
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.addSpacing(30) 
        
        self.result_title = QLabel("게임 종료!")
        self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        
        self.total_label = QLabel("")
        self.total_label.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        self.total_label.setStyleSheet("color: blue;")
        self.total_label.setAlignment(Qt.AlignCenter)
        
        back_to_menu_button = ClickableLabel()
        back_to_menu_button.clicked.connect(self.main_menu_button)
        back_to_menu_button.setScaledContents(True)

        exit_pixmap = QPixmap(flag['MAIN_BUTTON_IMAGE'])
        if not exit_pixmap.isNull():
            back_to_menu_button.setPixmap(exit_pixmap)
            back_to_menu_button.setFixedSize(flag['BUTTON_EXIT_WIDTH']-20, flag['BUTTON_EXIT_HEIGHT']-20)
            back_to_menu_button.setStyleSheet("background-color: transparent;")
        else:
            back_to_menu_button.setText("메인 메뉴로 돌아가기")
            back_to_menu_button.setFixedSize(flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'])
            back_to_menu_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;")

        h_layout = QHBoxLayout()
        h_layout.addStretch(1) 
        h_layout.addWidget(back_to_menu_button)
        h_layout.addSpacing(20)

        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.total_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout)
        self.layout.addSpacing(10)

        self.setLayout(self.layout)

    def set_results3(self, total_score):
        self.total_text = f"{total_score}개 맞추셨습니다! "
        current_font = self.total_label.font()
        current_font.setPointSize(50)
        self.total_label.setFont(current_font)
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

        self.current_emotion_file = None
        self.total_score = 0
        self.target_similarity = 40.0
        self.is_transitioning = False
        self.transition_delay_ms  = 1000
        self.total_game_time = 5
        self.time_left = self.total_game_time
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.game_started = False

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
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.back_btn = QPushButton("", self)
        self.back_btn.setGeometry(flag['BUTTON_EXIT_X'], flag['BUTTON_EXIT_Y'],
                                 flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'])

        icon_path = flag['MAIN_BUTTON_IMAGE']
        icon_pixmap = QPixmap(icon_path)
        icon_size = QSize(flag['BUTTON_EXIT_WIDTH'] - flag['BUTTON_EXIT_MARGIN'], flag['BUTTON_EXIT_HEIGHT'] - flag['BUTTON_EXIT_MARGIN'])
        scaled_icon = icon_pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.back_btn.setIcon(QIcon(scaled_icon))
        self.back_btn.setIconSize(scaled_icon.size())
        self.back_btn.clicked.connect(self.go_to_main_menu)
        self.back_btn.setObjectName("BottomRightIcon")
        unique_style = f"""
            QPushButton#BottomRightIcon {{ background-color: transparent; border-radius: 20px; border: none; color: transparent; }}
            QPushButton#BottomRightIcon:hover {{ background-color: rgba(255, 255, 255, 0.2); }}
            QPushButton#BottomRightIcon:pressed {{ background-color: rgba(255, 255, 255, 0.4); }}
        """
        self.back_btn.setStyleSheet(unique_style)

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
        emoji_layout.addSpacing(20)
        emoji_layout.addWidget(self.center_widget, alignment=Qt.AlignCenter)
        emoji_layout.addSpacing(50)
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

        # Accuracy Labels
        self.current_accuracy = QLabel(f'현재 유사도: {0.00: .2f}%')
        self.current_accuracy.setFont(QFont('Jalnan Gothic', 25))
        self.current_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 15px;")
        self.current_accuracy.setAlignment(Qt.AlignCenter)

        self.target_label = QLabel(f'목표 유사도: {self.target_similarity:.0f}%')
        self.target_label.setFont(QFont('Jalnan Gothic', 25))
        self.target_label.setStyleSheet("background-color: 'transparent'; color: #292E32;")
        self.target_label.setAlignment(Qt.AlignCenter)

        # 웹캠 컨테이너 레이아웃 구성
        # 수직 중앙 정렬을 위해 stretch 추가
        video_score_layout.addStretch(1)
        video_score_layout.addWidget(self.player_label)
        video_score_layout.addWidget(self.video_label)
        video_score_layout.addWidget(self.current_accuracy)
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
        self.center_widget.findChild(QStackedWidget).setCurrentWidget(self.emotion_label)
        self.timer_label.show()
        self.score_label.show()
        self.start_stream()

    def set_next_emotion(self):
        if not self.emotion_files: return
        available_emotions = [f for f in self.emotion_files if f != self.current_emotion_file]
        if not available_emotions: available_emotions = self.emotion_files
        self.current_emotion_file = random.choice(available_emotions)
        file_path = os.path.join(self.EMOJI_DIR, self.current_emotion_file)
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {self.current_emotion_file}")
        else:
            scaled_pixmap = pixmap.scaled(self.emotion_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.emotion_label.setPixmap(scaled_pixmap)
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.set_emotion_file(self.current_emotion_file)

    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"{self.time_left}")
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.fill_color = QColor("red")
        else:
            self.timer_label.fill_color = QColor("#0AB9FF")
        self.timer_label.repaint()
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_stream()
            self.timer_label.setText("게임 종료!")
            self.stacked_widget.findChild(Result3screen).set_results3(self.total_score)
            self.stacked_widget.setCurrentIndex(5)

    def update_image_and_score(self, image, score):
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        self.current_accuracy.setText(f'현재 유사도: {score: .2f}%')
        if score >= self.target_similarity and not self.is_transitioning:
            self.is_transitioning = True
            self.total_score += 1
            self.score_label.setText(f"SCORE: {self.total_score}")
            self.video_label.setStyleSheet("border: 5px solid #0f0; background-color: black; color: white;")
            QTimer.singleShot(self.transition_delay_ms, self.complete_transition)
            self.video_label.setStyleSheet("border: 3px solid #0f0; background-color: black; color: white;")
            QTimer.singleShot(500, lambda: self.video_label.setStyleSheet("background-color: black; color: white;"))


    def complete_transition(self):
        self.set_next_emotion()
        self.video_label.setStyleSheet("border: none;")
        self.is_transitioning = False

    def get_available_camera_index(self):
        for index in range(10):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                return index
        return 0

    def start_stream(self):
        if not self.game_started: return
        self.stop_stream()
        self.total_score = 0
        self.score_label.setText(f"SCORE: {self.total_score}")
        self.set_next_emotion()
        self.video_thread = TimeAttackThread(
            camera_index=self.get_available_camera_index(),
            emotion_file=self.current_emotion_file,
            width=flag['VIDEO_WIDTH'],
            height=flag['VIDEO_HEIGHT']
        )
        self.video_thread.change_pixmap_score_signal.connect(self.update_image_and_score)
        self.video_thread.start()
        self.time_left = self.total_game_time
        self.timer_label.setText(f"{self.total_game_time}")
        self.timer_label.repaint()
        self.game_timer.start(1000)

    def stop_stream(self):
        if self.game_timer.isActive():
            self.game_timer.stop()
        if self.video_thread and self.video_thread.isRunning():
            try:
                self.video_thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
            except Exception: pass
            self.video_thread.stop()
            self.video_thread.wait()
            self.video_thread = None

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
        self.score_label.setText(f"SCORE: {0}")
        self.current_accuracy.setText(f'현재 유사도: {0.00: .2f}%')
        self.video_label.setText(f"웹캠 피드 ({flag['VIDEO_WIDTH']}x{flag['VIDEO_HEIGHT']})")
        self.video_label.setPixmap(QPixmap())

    def go_to_result_screen(self):
        self.stacked_widget.setCurrentIndex(5)

    def go_to_main_menu(self):
        self.stop_stream()
        self.reset_game_state()
        self.stacked_widget.setCurrentIndex(0)

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