# game3.py 내용 시작
import cv2
import random
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, 
    QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QPointF 
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QMouseEvent, QPainter, QPainterPath, QColor, QCursor, QPen, QBrush
from compare import calc_similarity  

import numpy as np

from mainmenu import flag

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
        
        # Y 위치 계산: QFontMetrics를 사용하여 텍스트 기준선(Baseline) 위치를 찾습니다.
        # 중앙 정렬: (전체 높이 - 텍스트 높이) / 2 + 텍스트 기준선
        y = rect.top() + (rect.height() - text_height) // 2 + fm.ascent()
        
        # X 위치 계산: 정렬에 따라 조정
        x = 0
        if self.alignment() & Qt.AlignLeft:
             # 스타일시트의 padding-left: 20px를 수동으로 적용할 경우
             # mode_bar는 padding-left를 스타일시트에서 설정하므로, 여기서 20을 더합니다.
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
        # 텍스트 크기에 따라 적절한 크기를 반환 (테두리 두께 고려)
        return super().sizeHint()

# ClickableLabel 도우미 클래스 재사용
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
        
    # 마우스가 위젯 영역에 들어올 때 호출
    def enterEvent(self, event: QMouseEvent):
        # 마우스 포인터를 '손가락' 모양으로 설정
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    # 마우스가 위젯 영역을 벗어날 때 호출
    def leaveEvent(self, event: QMouseEvent):
        # 마우스 포인터를 기본 모양(화살표)으로 되돌림
        self.unsetCursor() 
        super().leaveEvent(event)



# 웹캠 스트림 처리 스레드 (TimeAttack 모드 전용)
class TimeAttackThread(QThread):
    # 이미지와 현재 유사도 점수만 전송
    change_pixmap_score_signal = pyqtSignal(QImage, float)
                                                                                       
    def __init__(self, camera_index, emotion_file, width=flag['VIDEO_WIDTH'], height=flag['VIDEO_HEIGHT']):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = width
        self.height = height
        # 비교할 현재 이모지 파일 이름
        self.emotion_file = emotion_file

        self.frame_count = 0
        self.inference_interval = 3  # 3프레임당 1회 추론
        self.similarity = 0

    def set_emotion_file(self, new_emotion_file):
        """실행 중인 스레드의 목표 이모지를 변경합니다."""
        self.emotion_file = new_emotion_file
        
    def run(self):
        # 카메라 인덱스 0이 아닌 경우를 대비해 DSHOW 백엔드 사용
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}. Check index or availability.")
            self.running = False
            return
        # 카메라의 FRAME_WIDTH, HEIGHT를 입력받은 width, height로 변경
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        while self.running:
            ret, frame = cap.read()
            if ret:
                # 3프레임마다 추론
                self.frame_count += 1
                if self.frame_count % self.inference_interval == 1:
                    # 유사도 계산
                    self.similarity = calc_similarity(frame, self.emotion_file)
                    self.frame_count = 0
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                # PyQt에 적용시키기 위해 frame을 QImage 객체로 변경
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                
                # 이미지와 유사도 시그널 전송
                self.change_pixmap_score_signal.emit(p, self.similarity)
            self.msleep(50)
        if cap.isOpened():
             cap.release()
        print(f"TimeAttackThread terminated.")
        
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
        # result_title에 OutlinedLabel 적용
        result_font = QFont('Jalnan 2', 60, QFont.Bold)
        self.result_title = OutlinedLabel(
            "게임 종료!", 
            result_font, 
            QColor("#FF5CA7"),  # Pink fill
            QColor(Qt.white),   # Black outline
            4.0, 
            alignment=Qt.AlignCenter
        )

        # total_label에 OutlinedLabel 적용
        total_font = QFont('Jalnan 2', 60)
        self.total_label = OutlinedLabel(
            "결과 계산 중...", 
            total_font, 
            QColor(Qt.white), # White fill
            QColor(Qt.black),  # Black outline
            3.0, 
            alignment=Qt.AlignCenter
        )
        # "메인 메뉴로 돌아가기" 버튼을 이미지로 변경 및 위치 조정
        back_to_menu_button = ClickableLabel()
        back_to_menu_button.clicked.connect(self.main_menu_button)
        
        back_to_menu_button.setScaledContents(True)
        
        exit_pixmap = QPixmap(flag['MAIN_BUTTON_IMAGE'])
        if not exit_pixmap.isNull():
            back_to_menu_button.setPixmap(exit_pixmap)
            back_to_menu_button.setFixedSize(exit_pixmap.size()) # 이미지 크기에 맞게 설정
            back_to_menu_button.setFixedSize(120, 60)
        else:
            back_to_menu_button.setText("메인 메뉴로 돌아가기")
            back_to_menu_button.setFixedSize(120, 60) # 기본 크기
            back_to_menu_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;")
            print("경고: 'design/exit.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        h_layout = QHBoxLayout()
        h_layout.addSpacing(1)
        h_layout.addWidget(back_to_menu_button)
        h_layout.addSpacing(1)
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.total_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout)
        self.layout.addSpacing(10)

        self.setLayout(self.layout)
        
    # 결과 창 텍스트와 폰트 수정
    def set_results3(self, total_score):
        self.total_text = f" Result!! (total_score: {total_score:.2f}점) "
        current_font = self.total_label.font()
        current_font.setPointSize(50)
        self.total_label.setFont(current_font)
        self.total_label.setText(self.total_text)
    
    # 메인 메뉴로 돌아가기
    def main_menu_button(self):
        self.stacked_widget.setCurrentIndex(0)
        return    
        
# 게임 3 GUI
class Game3Screen(QWidget):
    # 게임 종료 시그널
    game_finished = pyqtSignal(int) 
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_thread = None
        # 비교할 이모티콘들의 경로
        self.EMOJI_DIR = "img/emoji"
        try:
            # 이모지 파일 리스트 로드
            self.emotion_files = [
                f for f in os.listdir(self.EMOJI_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')
            ]
        except FileNotFoundError:
            print(f"Error: 이모지 디렉토리 ({self.EMOJI_DIR})를 찾을 수 없습니다. 테스트 이모지 사용.")
            self.emotion_files = ["0_angry.png"]

        self.current_emotion_file = None
        self.total_score = 0
        self.target_similarity = 40.0  # 목표 유사도 (예: 80%)
        
        self.is_transitioning = False # 이모지 전환 중인지 확인하는 플래그
        self.transition_delay_ms  = 1000  # 딜레이 시간(1000ms = 1초)
        
        # 총 게임 시간 (60초)
        self.total_game_time = 5
        self.time_left = self.total_game_time
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        
         # 게임 상태 플래그
        self.game_started = False 
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
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
        mode1_bar.setObjectName("mode_bar_label") # padding-left 처리를 위해 이름 지정
        mode1_bar.setStyleSheet("background-color: #FFE10A;") 
        
        mode1_bar.setFixedHeight(85)
        mode1_bar.setFixedWidth(1920) 
        main_layout.addWidget(mode1_bar) 

        # 타이틀 / 메뉴 버튼 레이아웃
        top_h_layout = QHBoxLayout()
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # OutlinedLabel 적용: timer_label - MODE 3 스타일로 통일
        timer_font = QFont(flag['MODE3_FONT_FAMILY'], 30, QFont.Bold)
        self.timer_label = OutlinedLabel(
            f"남은 시간: {self.total_game_time}초", 
            timer_font, 
            flag['MODE3_FILL_COLOR'],  # 핫핑크로 변경
            flag['MODE3_OUTLINE_COLOR'], # 거의 흰색
            flag['MODE3_OUTLINE_WIDTH'], # 3.5
            alignment=Qt.AlignCenter
        )

        self.back_btn = QPushButton("", self)
        self.back_btn.setGeometry(flag['BUTTON_EXIT_X'], flag['BUTTON_EXIT_Y'],
                                flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'])
        
        # 기본 버튼 스타일시트
        style = f"""
            QPushButton {{
                background-color: "transparent"; /* 배경색 사용 */
                color: #343a40;
                border-radius: 58px; /* 테두리 반경 사용 */
                font-family: 'Jalnan Gothic', 'Arial', sans-serif;
                font-size: 20pt; /* 폰트 크기 사용 */
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
        self.back_btn.setStyleSheet(style)
        self.back_btn.clicked.connect(self.go_to_main_menu)
        # "메뉴로 돌아가기" 버튼을 이미지로 변경
        self.back_btn.setObjectName("BottomRightIcon")
        
        # 아이콘 이미지 설정
        icon_path = flag['MAIN_BUTTON_IMAGE']
        icon_pixmap = QPixmap(icon_path)
       
        # QPixmap을 QIcon으로 변환하여 버튼에 설정
        icon_size = QSize(flag['BUTTON_EXIT_WIDTH'] - flag['BUTTON_EXIT_MARGIN'], flag['BUTTON_EXIT_HEIGHT'] - flag['BUTTON_EXIT_MARGIN'])
        scaled_icon = icon_pixmap.scaled(
            icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.back_btn.setIcon(QIcon(scaled_icon))
        self.back_btn.setIconSize(scaled_icon.size())
        
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
        self.back_btn.setStyleSheet(self.back_btn.styleSheet() + unique_style)

        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        
        main_layout.addLayout(top_h_layout)
        main_layout.addSpacing(230)

        # --- 중앙 레이아웃 ---
        center_h_layout = QHBoxLayout()

        # 1. 이모지 + 타이머 + 점수 (세로 중앙)
        emoji_layout = QVBoxLayout()
        emoji_layout.addStretch(1)

        # 변경 시작: 이모지 대신 ClickableLabel을 사용하여 시작 버튼 추가
        self.start_button = ClickableLabel()
        self.start_button.setAlignment(Qt.AlignCenter)
        self.start_button.setFixedSize(300, 200)
        self.start_button.clicked.connect(self.start_game) # 버튼 클릭 시 게임 시작
        
        # 시작 버튼 이미지 설정
        start_pixmap = QPixmap(flag['START_BUTTON_IMAGE'])
        if not start_pixmap.isNull():
            scaled_start_pixmap = start_pixmap.scaled(
                self.start_button.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.start_button.setPixmap(scaled_start_pixmap)
        else:
            self.start_button.setText("게임 시작")
            self.start_button.setFont(QFont('Jalnan Gothic', 24, QFont.Bold))
            print(f"경고: '{flag['START_BUTTON_IMAGE']}' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")



        self.emotion_label = QLabel("표정 이미지 준비 중...")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(300, 200)
        self.emotion_label.hide() # 초기에는 숨김
        
        # OutlinedLabel 적용: score_label - MODE 3 스타일로 통일
        score_font = QFont(flag['MODE3_FONT_FAMILY'], 30, QFont.Bold)
        self.score_label = OutlinedLabel(
            f"SCORE: {self.total_score}점", 
            score_font, 
            flag['MODE3_FILL_COLOR'], 
            flag['MODE3_OUTLINE_COLOR'], 
            flag['MODE3_OUTLINE_WIDTH'], 
            alignment=Qt.AlignCenter
        )
        # self.score_label.setStyleSheet("color: red;") # 제거
        
        emoji_layout.addWidget(self.timer_label)
        emoji_layout.addWidget(self.start_button) 
        emoji_layout.addWidget(self.emotion_label)
        emoji_layout.addWidget(self.score_label)
        emoji_layout.addStretch(2)
        
        # 2. 웹캠 + PLAYER + 유사도 (세로 중앙)
        video_score_layout = QVBoxLayout()
        video_score_layout.addStretch(1)

        self.player_label = QLabel("PLAYER")
        
        # OutlinedLabel 적용: player_label - MODE 3 스타일로 통일
        # 이미지의 'PLAYER 1'과 유사하게 폰트 크기 조정
        player_font = QFont(flag['MODE3_FONT_FAMILY'], 30, QFont.Bold) 
        self.player_label = OutlinedLabel(
            "PLAYER", 
            player_font, 
            flag['MODE3_FILL_COLOR'], 
            flag['MODE3_OUTLINE_COLOR'], 
            flag['MODE3_OUTLINE_WIDTH'], 
            alignment=Qt.AlignCenter
        )
        
        self.video_label = QLabel(f"웹캠 피드 ({flag['VIDEO_WIDTH']}x{flag['VIDEO_HEIGHT']})")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.video_label.setStyleSheet("background-color: black; color: white;")

        # OutlinedLabel 적용: current_accuracy - MODE 3 스타일로 통일
        current_acc_font = QFont(flag['MODE3_FONT_FAMILY'], 18, QFont.Bold)
        self.current_accuracy = OutlinedLabel(
            f'현재 유사도: {0.00: .2f}%', 
            current_acc_font, 
            flag['MODE3_FILL_COLOR'], 
            flag['MODE3_OUTLINE_COLOR'], 
            flag['MODE3_OUTLINE_WIDTH'], 
            alignment=Qt.AlignCenter
        )

        # OutlinedLabel 적용: target_label - MODE 3 스타일로 통일
        target_font = QFont(flag['MODE3_FONT_FAMILY'], 18, QFont.Bold)
        self.target_label = OutlinedLabel(
            f'목표 유사도: {self.target_similarity:.0f}%', 
            target_font, 
            flag['MODE3_FILL_COLOR'], 
            flag['MODE3_OUTLINE_COLOR'], 
            flag['MODE3_OUTLINE_WIDTH'], 
            alignment=Qt.AlignCenter
        )

        video_score_layout.addWidget(self.player_label)
        video_score_layout.addWidget(self.video_label)
        video_score_layout.addWidget(self.current_accuracy)
        video_score_layout.addWidget(self.target_label)
        video_score_layout.addStretch(2)

        # --- 중앙 레이아웃에 배치 ---
        center_h_layout.addStretch(1)
        center_h_layout.addLayout(video_score_layout)
        center_h_layout.addSpacing(200)
        center_h_layout.addLayout(emoji_layout)
        center_h_layout.addStretch(1)

        main_layout.addLayout(center_h_layout)
        main_layout.addStretch(1)

        # QWidget 기반 레이아웃 적용
        self.setLayout(main_layout)
        
    # 게임 시작을 처리하는 함수
    def start_game(self):
        """게임 시작 버튼 클릭 시 호출되며, 게임을 초기화하고 스트림을 시작합니다."""
        if self.game_started:
            return

        print("게임 시작 버튼 클릭. 게임을 시작합니다.")
        self.game_started = True
        
        # 시작 버튼 숨기기, 이모지 레이블 표시
        self.start_button.hide()
        self.emotion_label.show()
        
        # 스트림 및 타이머 시작
        self.start_stream()
            
    def set_next_emotion(self):
        """랜덤으로 다음 이모지를 설정하고 스레드를 업데이트합니다."""
        if not self.emotion_files:
            return 
            
        # 기존 이모지 제외하고 새로운 이모지 선택
        available_emotions = [f for f in self.emotion_files if f != self.current_emotion_file]
        if not available_emotions:
            # 모든 이모지를 다 썼다면 리스트를 리셋합니다.
            available_emotions = self.emotion_files
            
        self.current_emotion_file = random.choice(available_emotions)
        file_path = os.path.join(self.EMOJI_DIR, self.current_emotion_file)

        # QLabel에 이모지 이미지 표시
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {self.current_emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
            
        # 웹캠 스레드에 목표 파일명 업데이트
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.set_emotion_file(self.current_emotion_file)
            print(f"새로운 목표 이모지 설정: {self.current_emotion_file}")

    def update_timer(self):
        """1초마다 타이머를 업데이트하고 게임 종료를 확인합니다."""
        self.time_left -= 1
        self.timer_label.setText(f"남은 시간: {self.time_left}초")
        
        # OutlinedLabel의 fill_color를 동적으로 변경하고 repaint를 호출
        if self.time_left <= 10 and self.time_left > 0:
            self.timer_label.fill_color = QColor("red")
        else:
            # 기본 색상 복귀 (initUI에서 설정한 Blue fill)
            self.timer_label.fill_color = QColor("#4285F4")
            
        if self.time_left <= 0:
            self.game_timer.stop()
            self.stop_stream()
            self.timer_label.setText("게임 종료!")
            
            # 메인 메뉴로 돌아가거나 결과 화면이 있다면 결과 화면으로 전환
            # game3 결과창 load
            self.stacked_widget.findChild(Result3screen).set_results3(
                self.total_score
            )
            self.stacked_widget.setCurrentIndex(5)
            
            print("게임 시간이 모두 소진되었습니다.")


    def update_image_and_score(self, image, score):
        """VideoThread로부터 이미지와 유사도 점수를 받아 화면을 업데이트합니다."""
        
        # 웹캠 피드 업데이트
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        
        # 유사도 표시 업데이트
        self.current_accuracy.setText(f'현재 유사도: {score: .2f}%')
        
        # 목표 달성 확인 및 다음 이모지로 전환
        if score >= self.target_similarity and not self.is_transitioning:
            
            self.is_transitioning = True
            
            # 점수 획득
            self.total_score += 1 
            self.score_label.setText(f"SCORE: {self.total_score}점")
            
            self.video_label.setStyleSheet("border: 5px solid #0f0;") # 초록색 테두리
            
            
            QTimer.singleShot(self.transition_delay_ms, self.complete_transition)
        
            print(f"목표 달성! 점수 {self.total_score}점 획득. 1초 딜레이 시작.")
            
            # 목표 달성 시 시각적 피드백
            self.video_label.setStyleSheet("border: 3px solid #0f0; background-color: black; color: white;")
            QTimer.singleShot(500, lambda: self.video_label.setStyleSheet("background-color: black; color: white;")) # 0.5초 후 원래대로 복귀
    
    
    def complete_transition(self):
        """
        QTimer에 의해 딜레이 시간(1초) 경과 후 호출되어
        다음 이모지 설정 및 전환 플래그를 해제합니다.
        """
        # 다음 이모지 설정 (랜덤 선택 및 TimeAttackThread에 전달)
        self.set_next_emotion() 
        
        # 웹캠 피드 스타일 초기화 (테두리 제거)
        self.video_label.setStyleSheet("border: none;") 
        
        # 플래그 해제: 이제 다시 점수 획득을 할 수 있게 됩니다.
        self.is_transitioning = False
        
        print("이모지 전환 완료 및 플래그 해제. 다음 목표 표정 시작.")

    def get_available_camera_index(self):
        """사용 가능한 가장 낮은 인덱스의 웹캠 번호를 반환합니다."""
        # 0부터 9까지 시도하며, 먼저 열리는 카메라의 인덱스를 반환
        for index in range(10): 
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                return index
        return 0 # 찾지 못하면 기본값 0 반환

    def start_stream(self):
        """스트리밍을 시작하고 게임 타이머를 리셋합니다."""
        
        if not self.game_started:
            print("경고: start_stream이 game_started=False인 상태에서 호출되었습니다. 실행을 중단합니다.")
            return
        
        self.stop_stream()
        
        # 초기화
        self.total_score = 0
        self.score_label.setText(f"SCORE: {self.total_score}점")
        
        # 비디오 스레드 시작
        # 스레드 생성 시 초기 이모지 설정을 위해 set_next_emotion 호출
        self.set_next_emotion() 
        
        self.video_thread = TimeAttackThread(
            camera_index=self.get_available_camera_index(), # 타임어택은 1인 모드이므로 보통 0번 카메라 사용
            emotion_file=self.current_emotion_file,
            width=flag['VIDEO_WIDTH'],
            height=flag['VIDEO_HEIGHT']
        )
        self.video_thread.change_pixmap_score_signal.connect(self.update_image_and_score)
        self.video_thread.start()
        
        # 타이머 시작
        self.time_left = self.total_game_time
        self.timer_label.setText(f"남은 시간: {self.total_game_time}초")
        self.timer_label.setStyleSheet("color: black;")
        self.game_timer.start(1000)
        
        #self.timer_label.fill_color = QColor("#4285F4") # Blue fill (기본값)
        #self.timer_label.repaint()
        
        print("타임어택 스트리밍 및 타이머 작동 시작")

    def stop_stream(self):
        """타이머와 웹캠 스레드를 안전하게 종료합니다."""
        if self.game_timer.isActive():
            self.game_timer.stop()
            
        if self.video_thread and self.video_thread.isRunning():
            try:
                self.video_thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
            except Exception:
                pass 
            
            self.video_thread.stop()
            self.video_thread.wait() 
            self.video_thread = None
            
        print("타임어택 스트리밍 및 타이머 작동 종료")
    # 게임 화면이 다시 나타날 때 상태를 초기화
    def showEvent(self, event):
        """위젯이 화면에 표시될 때 호출됩니다."""
        super().showEvent(event)
        # 게임이 종료된 상태에서 다시 돌아왔을 때만 초기화
        if not self.game_started:
            self.reset_game_state()
            
    def reset_game_state(self):
        """게임을 시작 전 상태로 되돌립니다."""
        self.game_started = False
        
        self.start_button.show()
        self.emotion_label.hide()

        self.score_label.setText(f"SCORE: {0}점")
        self.current_accuracy.setText(f'현재 유사도: {0.00: .2f}%')
        self.video_label.setText(f"웹캠 피드 ({flag['VIDEO_WIDTH']}x{flag['VIDEO_HEIGHT']})")
        self.video_label.setPixmap(QPixmap()) # 웹캠 피드 이미지 초기화

    def go_to_result_screen(self):
        self.stacked_widget.setCurrentIndex(5)
        
    def go_to_main_menu(self):
        self.stop_stream()
        self.reset_game_state()
        
        self.stacked_widget.setCurrentIndex(0)