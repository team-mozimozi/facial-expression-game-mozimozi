import cv2
import random
import os
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPointF
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor, QIcon, QPainterPath, QBrush, QCursor, QMouseEvent
from compare import calc_similarity
import numpy as np
from mainmenu import flag

# ======================================================================
# ⭐ 1. 텍스트 테두리 기능을 위한 사용자 정의 QLabel 클래스 ⭐
# ======================================================================
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
# ======================================================================


# ----------------------------------------------------------------------
# ClickableLabel 도우미 클래스 (수정)
# ----------------------------------------------------------------------
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
        
    # ⭐ [추가] 마우스가 위젯 영역에 들어올 때 호출
    def enterEvent(self, event: QMouseEvent):
        # 마우스 포인터를 '손가락' 모양으로 설정
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    # ⭐ [추가] 마우스가 위젯 영역을 벗어날 때 호출
    def leaveEvent(self, event: QMouseEvent):
        # 마우스 포인터를 기본 모양(화살표)으로 되돌림
        self.unsetCursor() 
        super().leaveEvent(event)

# ----------------------------------------------------------------------
# 1. 웹캠 스트림 처리를 위한 별도의 QThread
# ----------------------------------------------------------------------
class VideoThread(QThread):
    change_pixmap_score_signal = pyqtSignal(QImage, float, int)
                                            
    # emoji_filename과 player_index를 추가로 받습니다.
    def __init__(self, camera_index, emotion_file, player_index, width=320, height=240):
        super().__init__()
        self.camera_index = camera_index 
        self.running = True
        self.width = 610
        self.height = 370
        # ✨ 2. 비교할 이모지 파일 이름과 플레이어 인덱스 저장
        self.emotion_file = emotion_file
        self.player_index = player_index

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}. Check index or availability.")
            self.running = False
            return
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        while self.running:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                similarity = calc_similarity(rgb_image, self.emotion_file)
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)
                self.change_pixmap_score_signal.emit(p, similarity, self.player_index)
            self.msleep(50)
        
        cap.release()
        
    def stop(self):
        self.running = False
        self.wait()

# ----------------------------------------------------------------------
# 2. 게임 결과 화면 (Resultscreen)
# ----------------------------------------------------------------------
class Resultscreen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()
        self.winner_text = ""
        
    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.addSpacing(30) 
        
        self.result_title = QLabel("게임 종료!")
        self.result_title.setFont(QFont('Jalnan 2', 60, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        
        self.winner_label = QLabel("결과 계산 중...")
        self.winner_label.setFont(QFont('Jalnan 2', 60))
        self.winner_label.setAlignment(Qt.AlignCenter)
        
        # "메인 메뉴로 돌아가기" 버튼을 이미지로 변경 및 위치 조정
        back_to_menu_button = ClickableLabel()
        back_to_menu_button.clicked.connect(self.main_menu_button)
        
        exit_pixmap = QPixmap(flag['MAIN_BUTTON_IMAGE'])
        if not exit_pixmap.isNull():
            back_to_menu_button.setPixmap(exit_pixmap)
            back_to_menu_button.setFixedSize(exit_pixmap.size()) # 이미지 크기에 맞게 설정
            back_to_menu_button.setFixedSize(250, 60)
        else:
            back_to_menu_button.setText("메인 메뉴로 돌아가기")
            back_to_menu_button.setFixedSize(250, 60) # 기본 크기
            back_to_menu_button.setStyleSheet("background-color: #0AB9FF; color: white; border-radius: 10px;")
            print("경고: 'design/exit.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        h_layout = QHBoxLayout()
        h_layout.addSpacing(1) # 좌측에 공간을 추가하여 버튼을 오른쪽으로 밈
        h_layout.addWidget(back_to_menu_button)
        h_layout.addSpacing(1) # 우측 여백
        
        self.layout.addWidget(self.result_title)
        self.layout.addStretch(1)
        self.layout.addWidget(self.winner_label)
        self.layout.addStretch(2)
        self.layout.addLayout(h_layout) # 하단 레이아웃 추가
        self.layout.addSpacing(20) # 하단 여백 추가

        self.setLayout(self.layout)

    def set_results(self, p1_score, p2_score):
        if p1_score > p2_score:
            self.winner_text = f"🎉 PLAYER 1 승리! 🎉 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: blue;")
        elif p2_score > p1_score:
            self.winner_text = f"🎉 PLAYER 2 승리! 🎉 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: blue;")
        else:
            self.winner_text = f"🤝 무승부입니다! 🤝 \n P1: {p1_score:.0f}점 / P2: {p2_score:.0f}점"
            self.winner_label.setFont(QFont('Jalnan 2', 50))
            self.winner_label.setStyleSheet("color: black;")
            
        self.winner_label.setText(self.winner_text)

    def main_menu_button(self):
        self.stacked_widget.setCurrentIndex(0)
        return

# ----------------------------------------------------------------------
# 3. 게임 화면 (Game1Screen) - 간격 조절 반영 및 스코어보드 추가
# ----------------------------------------------------------------------
class Game1Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_threads = []
        
        if os.path.isdir("img/emoji"):
            self.emotion_ids = os.listdir("img/emoji")
        else:
            self.emotion_ids = ["default.png"]
            print("경고: 'img/emoji' 폴더를 찾을 수 없습니다. 기본값 사용.")

        self.p1_score = 0
        self.p2_score = 0
        self.p1_max_similarity = 0.0
        self.p2_max_similarity = 0.0
        self.round = 0 
        
        # ✨ 새로운 이미지 스코어보드 레이블 리스트 초기화
        self.p1_score_images = []
        self.p2_score_images = []
        # ✨ 최대 라운드 수 (점수 이미지 개수) 정의
        self.MAX_ROUNDS = 3 # 3점 선취승을 의미
        
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_timer)
        self.total_game_time = 1
        self.time_left = self.total_game_time
        self.is_game_active = False
        
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 
        
        # 상단 Mode1 바 (유지)
        # ⭐ [수정] QLabel -> OutlinedLabel 적용 ⭐
        # 이전 스타일: background-color: #FFE10A; color: #FF5CA7; padding-left: 20px;
        mode1_bar_font = QFont('ARCO', 30, QFont.Bold)
        mode1_bar_fill = QColor("#FF5CA7")
        mode1_bar_outline = QColor("#FFF0FA")
        mode1_bar_width = 3.5
        
        mode1_bar = OutlinedLabel(
            "MODE1", 
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
        # ⭐ [수정] 끝 ⭐
        
        # 타이틀/메뉴 버튼 레이아웃
        top_h_layout = QHBoxLayout()
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 타이머 레이블은 여전히 여기서 인스턴스화
        # ⭐ [수정] QLabel -> OutlinedLabel 적용 ⭐
        timer_font = QFont('Jalnan 2', 45)
        timer_fill = QColor('#0AB9FF') # 초기 색상은 검정
        timer_outline = QColor('#00A4F3')
        timer_width = 3.0
        
        self.timer_label = OutlinedLabel(
            f"{self.total_game_time}", 
            timer_font, 
            timer_fill, 
            timer_outline, 
            timer_width,
            alignment=Qt.AlignCenter,
            parent=self
        )
        # 이 레이블에는 배경색이나 텍스트 색상을 설정하지 않고 OutlinedLabel에서 처리
        # self.timer_label.setStyleSheet("color: black;") 
        # ✨ [수정] 초기에는 타이머를 숨깁니다.
        self.timer_label.hide() 

        self.back_btn = QPushButton("", self)
        self.back_btn.setGeometry(flag['BUTTON_EXIT_X'], flag['BUTTON_EXIT_Y'],
                                 flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT'])

        # 버튼 색상 및 스타일 설정 (유지)
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
        # 🟢 "메뉴로 돌아가기" 버튼을 이미지로 변경
        self.back_btn.clicked.connect(self.go_to_main_menu)

        # *** 우측 하단 버튼 스타일 분리를 위한 고유 이름 설정 ***
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

        # *** 우측 하단 버튼에 대한 고유 스타일시트 적용 *** (유지)
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
        self.back_btn.setStyleSheet(self.back_btn.styleSheet() + unique_style)
        
        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        # 🟢 top_h_layout에서 back_btn을 제거하고, 별도의 하단 레이아웃으로 옮기기 위해 잠시 주석 처리
        # top_h_layout.addWidget(self.back_btn, 0) 
        main_layout.addLayout(top_h_layout)
        
        main_layout.addSpacing(130) 

        # ------------------------------------------------------------------
        # 이모지 레이블 및 오버레이 버튼 설정 (유지)
        # ------------------------------------------------------------------
        # 1. 이모지 레이블 설정
        self.emotion_label = QLabel() 
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setFixedSize(240, 240)
        self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;")
        self.emotion_label.hide() # 💡 초기에는 이모지 레이블 숨김

        # 2. 게임 시작 오버레이 버튼 (ClickableLabel 사용)
        self.start_overlay_button = ClickableLabel() # ClickableLabel 인스턴스 생성
        self.start_overlay_button.setFixedSize(240, 240)
        self.start_overlay_button.setAlignment(Qt.AlignCenter)

        start_game_pixmap = QPixmap("design/start_game.png")
        if not start_game_pixmap.isNull():
            scaled_pixmap = start_game_pixmap.scaled(
                self.start_overlay_button.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.start_overlay_button.setPixmap(scaled_pixmap)
            # 이미지 버튼일 경우의 스타일시트:
            # ⭐ [수정] 'cursor: pointinghand;' QSS 속성 제거 ⭐
            self.start_overlay_button.setStyleSheet("""
                /* ClickableLabel 클래스에서 enterEvent/leaveEvent로 커서 설정 */
            """)
        else:
            self.start_overlay_button.setText("게임 시작 (이미지 없음)")
            # 텍스트 버튼일 경우의 대체 스타일 및 커서 변경 적용
            # ⭐ [수정] 'cursor: pointinghand;' QSS 속성 제거 ⭐
            self.start_overlay_button.setStyleSheet("""
                ClickableLabel {
                    background-color: #0AB9FF; 
                    color: white; 
                    border-radius: 10px;
                }
                ClickableLabel:hover {
                    /* 커서 변경은 enterEvent/leaveEvent에서 처리 */
                    background-color: #0088CC; /* 호버 시 배경색을 약간 어둡게 변경 (선택 사항) */
                }
            """) 
            print("경고: 'design/start_game.png' 이미지를 찾을 수 없습니다. 텍스트 버튼으로 대체.")

        self.start_overlay_button.clicked.connect(self.start_game_clicked) # 슬롯 연결
        # 3. 이모지와 오버레이 버튼을 담을 위젯 (Stack)
        self.center_widget = QWidget()
        center_stack_layout = QStackedWidget(self.center_widget) # QStackedWidget을 사용하여 겹치게 처리
        center_stack_layout.addWidget(self.emotion_label) 
        center_stack_layout.addWidget(self.start_overlay_button)
        center_stack_layout.setCurrentWidget(self.start_overlay_button) # 처음에는 버튼이 보이도록 설정
        self.center_widget.setFixedSize(240, 240) # 크기를 맞춰줌
        
        # 하단 레이아웃 (웹캠 1 - 중앙 컨테이너 - 웹캠 2)
        bottom_h_layout = QHBoxLayout()
        
        # P1 웹캠 및 정확도 
        player1_v_layout = QVBoxLayout()
        # ⭐ [수정] QLabel -> OutlinedLabel 적용 ⭐
        player_title_font = QFont('ARCO', 50)
        player_title_fill = QColor("#FFD50A")
        player_title_outline = QColor(0, 0, 0)
        player_title_width = 3.0
        
        self.player1_webcam_title = OutlinedLabel(
            'PLAYER 1',
            player_title_font,
            player_title_fill,
            player_title_outline,
            player_title_width,
            alignment=Qt.AlignCenter,
            parent=self
        )
        self.player1_webcam_title.setStyleSheet("""
            background-color: transparent;  
            padding-bottom: 8px;
        """)
        player1_v_layout.addWidget(self.player1_webcam_title) 
        # ⭐ [수정] 끝 ⭐
        
        self.player1_video = QLabel('웹캠 1 피드')
        self.player1_video.setAlignment(Qt.AlignCenter)
        self.player1_video.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.player1_video.setStyleSheet("background-color: black; color: white;")
        player1_v_layout.addWidget(self.player1_video)
        
        self.player1_accuracy = QLabel(f'P1 정확도: {self.p1_score: .2f}%')
        self.player1_accuracy.setFont(QFont('Jalnan 2', 25))
        self.player1_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player1_accuracy.setAlignment(Qt.AlignCenter)
        player1_v_layout.addWidget(self.player1_accuracy)
        player1_v_layout.addSpacing(15) 
        
        p1_score_h_layout = QHBoxLayout()
        p1_score_h_layout.addStretch(1) 
        self._setup_score_images(p1_score_h_layout, self.p1_score_images)
        p1_score_h_layout.addStretch(1) 
        player1_v_layout.addLayout(p1_score_h_layout)

        player1_v_layout.addStretch(1) 

        # P2 웹캠 및 정확도 (코드 유지)
        player2_v_layout = QVBoxLayout()
        # ⭐ [수정] QLabel -> OutlinedLabel 적용 ⭐
        self.player2_webcam_title = OutlinedLabel(
            'PLAYER 2',
            player_title_font,
            player_title_fill,
            player_title_outline,
            player_title_width,
            alignment=Qt.AlignCenter,
            parent=self
        )
        self.player2_webcam_title.setStyleSheet("""
            background-color: transparent; 
            padding-bottom: 8px;
        """)
        player2_v_layout.addWidget(self.player2_webcam_title) 
        # ⭐ [수정] 끝 ⭐

        self.player2_video = QLabel('웹캠 2 피드')
        self.player2_video.setAlignment(Qt.AlignCenter)
        self.player2_video.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.player2_video.setStyleSheet("background-color: black; color: white;")
        player2_v_layout.addWidget(self.player2_video)

        self.player2_accuracy = QLabel(f'P2 정확도: {self.p2_score: .2f}%')
        self.player2_accuracy.setFont(QFont('Jalnan 2', 25))
        self.player2_accuracy.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-top: 20px;")
        self.player2_accuracy.setAlignment(Qt.AlignCenter)
        player2_v_layout.addWidget(self.player2_accuracy)
        player2_v_layout.addSpacing(15) 
        
        p2_score_h_layout = QHBoxLayout()
        p2_score_h_layout.addStretch(1) 
        self._setup_score_images(p2_score_h_layout, self.p2_score_images)
        p2_score_h_layout.addStretch(1) 
        player2_v_layout.addLayout(p2_score_h_layout)

        player2_v_layout.addStretch(1) 
        
        # ------------------------------------------------------------------
        # 중앙 수직 컨테이너: 타이머 + 이모지/버튼 + 간격
        # ------------------------------------------------------------------
        center_v_layout = QVBoxLayout()
        center_v_layout.addSpacing(90) # 남는 공간을 이 위쪽에 할당
        center_v_layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        center_v_layout.addSpacing(20)
        center_v_layout.addWidget(self.center_widget, alignment=Qt.AlignCenter)
        center_v_layout.addSpacing(80) # 예시: 50 픽셀 간격
        center_v_layout.addStretch(1) 
        # ------------------------------------------------------------------
        bottom_h_layout.addStretch(1) 
        bottom_h_layout.addLayout(player1_v_layout)
        bottom_h_layout.addSpacing(100) 
        bottom_h_layout.addLayout(center_v_layout) 
        bottom_h_layout.addSpacing(100) 
        
        bottom_h_layout.addLayout(player2_v_layout)
        bottom_h_layout.addStretch(1)
        main_layout.addLayout(bottom_h_layout)
        
        # 🟢 종료 버튼을 위한 새로운 하단 레이아웃 추가
        bottom_exit_layout = QHBoxLayout()
        bottom_exit_layout.addStretch(0) # 좌측에 공간 추가
        bottom_exit_layout.addWidget(self.back_btn) # 종료 버튼 추가
        bottom_exit_layout.addSpacing(30)

        main_layout.addLayout(bottom_exit_layout)
        main_layout.addSpacing(20) # 최하단 여백 추가
        
        self.setLayout(main_layout)
        
        self.update_score_display()


    # 새로운 슬롯: 게임 시작 버튼 클릭 시 (유지)
    def start_game_clicked(self):
        # 1. 게임 시작 오버레이 버튼 숨기기
        self.start_overlay_button.hide()
        # 2. 이모지 레이블 표시
        self.emotion_label.show() 
        
        self.timer_label.setText(f"{self.total_game_time}")
        # ⭐ [수정] OutlinedLabel의 텍스트와 스타일 업데이트
        # self._update_outlined_label_color(self.timer_label, QColor(10, 185, 255), QColor(255, 255, 255))
        self.timer_label.show() 
        
        # 3. 게임 상태 초기화
        self.p1_score = 0
        self.p2_score = 0
        self.round = 0
        self.update_score_display() # 점수 이미지 초기화

        # 4. 첫 라운드 시작
        self.start_next_round()
    
    # OutlinedLabel의 색상을 변경하는 헬퍼 함수
    def _update_outlined_label_color(self, label, fill_color, outline_color):
        if isinstance(label, OutlinedLabel):
            label.fill_color = fill_color
            label.outline_color = outline_color
            label.repaint() # 변경 사항을 즉시 반영
    
    # 스코어 이미지 레이블을 생성하고 레이아웃에 추가하는 헬퍼 함수 (유지)
    def _setup_score_images(self, h_layout, score_image_list):
        for _ in range(self.MAX_ROUNDS):
            score_label = QLabel()
            score_label.setFixedSize(flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'])
            score_label.setAlignment(Qt.AlignCenter)
            h_layout.addSpacing(5) 
            score_image_list.append(score_label)
            h_layout.addWidget(score_label)
            h_layout.addSpacing(5) 
            
    # ✨ P1, P2 점수에 따라 이미지(하트)를 업데이트하는 함수 (유지)
    def update_score_display(self):
        # P1 점수 표시 업데이트
        for i in range(self.MAX_ROUNDS):
            pixmap = QPixmap(flag['FILLED_SCORE_IMAGE'] if i < self.p1_score else flag['EMPTY_SCORE_IMAGE'])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'], Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.p1_score_images[i].setPixmap(scaled_pixmap)
            else:
                self.p1_score_images[i].setText("?") 

        # P2 점수 표시 업데이트
        for i in range(self.MAX_ROUNDS):
            pixmap = QPixmap(flag['FILLED_SCORE_IMAGE'] if i < self.p2_score else flag['EMPTY_SCORE_IMAGE'])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    flag['SCORE_IMAGE_SIZE'], flag['SCORE_IMAGE_SIZE'], Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.p2_score_images[i].setPixmap(scaled_pixmap)
            else:
                self.p2_score_images[i].setText("?") 
        
    # 랜덤으로 선택된 이모지 파일명을 받아 QLabel에 표시하는 함수 (유지)
    def set_required_emotion(self, emotion_file):
        self.current_emotion_file = emotion_file
        file_path = os.path.join("img/emoji", emotion_file)

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.emotion_label.setText(f"이미지 없음: {emotion_file}")
            print(f"[Error] Emoji image not found at {file_path}")
            self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0; color: red;")
        else:
            scaled_pixmap = pixmap.scaled(
                self.emotion_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emotion_label.setPixmap(scaled_pixmap)
            self.emotion_label.setStyleSheet("border: 0px solid #ccc; background-color: #f0f0f0;") 
        
    # update_timer 함수 (유지)
    def update_timer(self):
        # 1. 게임 시간 카운트 다운
        if self.time_left > 0:
            self.time_left -= 1
            
            # 남은 시간 표시 업데이트
            self.timer_label.setText(f"{self.time_left}")
            # ⭐ [수정] OutlinedLabel의 텍스트와 스타일 업데이트
            # self._update_outlined_label_color(self.timer_label, QColor(10, 185, 255), QColor(255, 255, 255))
                
            # time_left == 0이 되는 순간 UI 업데이트를 멈춥니다.
            if self.time_left == 0:
                self.game_timer.stop()
                self.is_game_active = False
                
                # --- 라운드 승패 판정 ---
                if self.p1_max_similarity == self.p2_max_similarity:
                    self.timer_label.setText("무승부! 재도전")
                    QTimer.singleShot(2000, self.start_next_round) 
                else:
                    if self.p1_max_similarity > self.p2_max_similarity: # 플레이어1 승리
                        self.timer_label.setText("P1 승리!")
                        self.p1_score += 1
                        if self.p1_score < self.MAX_ROUNDS:
                            QTimer.singleShot(2000, self.start_next_round)


                    else: # 플레이어2 승리
                        self.timer_label.setText("P2 승리!")
                        self.p2_score += 1
                        if self.p2_score < self.MAX_ROUNDS:
                            QTimer.singleShot(2000, self.start_next_round)
                    self.update_score_display()

                # --- 게임 종료 결정 (3점 선취승) ---
                if self.p1_score >= self.MAX_ROUNDS or self.p2_score >= self.MAX_ROUNDS:
                    self.timer_label.setText("게임 종료!")
                    self.stop_video_streams()
                    
                    self.start_overlay_button.show()
                    self.emotion_label.hide()
                    self.timer_label.hide()
                    
                    result_screen = self.stacked_widget.findChild(Resultscreen)
                    if result_screen:
                        final_p1_score = self.p1_score
                        final_p2_score = self.p2_score
                        result_screen.set_results(final_p1_score, final_p2_score)

                    self.stacked_widget.setCurrentIndex(2)
                    self.p1_score = 0
                    self.p2_score = 0
                    self.p1_max_similarity = 0
                    self.p2_max_similarity = 0
                    self.player1_accuracy.setText(f'P1 정확도: {self.p1_score: .2f}%')
                    self.player2_accuracy.setText(f'P1 정확도: {self.p2_score: .2f}%')
                    self.player1_video.clear()
                    self.player2_video.clear()
                    self.update_score_display()

    # start_next_round 함수 (유지)
    def start_next_round(self):
        if self.p1_score >= self.MAX_ROUNDS or self.p2_score >= self.MAX_ROUNDS:
            return 
            
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        
        self.player1_accuracy.setText(f'P1 정확도: 0.00%')
        self.player2_accuracy.setText(f'P2 정확도: 0.00%')
        
        print(f"새 라운드 시작 (P1 승리: {self.p1_score} / P2 승리: {self.p2_score})")

        self.start_video_streams() 

    # update_image_and_score 함수 (유지)
    def update_image_and_score(self, image, score, player_index):
        if self.is_game_active:
            pixmap = QPixmap.fromImage(image)
            
            if player_index == 0:
                self.player1_video.setPixmap(pixmap)
                self.p1_max_similarity = max(self.p1_max_similarity, score)
                self.player1_accuracy.setText(f'P1 정확도: {self.p1_max_similarity: .2f}%')
                
            elif player_index == 1:
                self.player2_video.setPixmap(pixmap)
                self.p2_max_similarity = max(self.p2_max_similarity, score)
                self.player2_accuracy.setText(f'P2 정확도: {self.p2_max_similarity: .2f}%')
                        
    # start_video_streams 함수 (유지)
    def start_video_streams(self):
        # 기존 스레드가 실행 중일 수 있으므로 안전하게 중지 및 정리
        self.stop_video_streams()
        self.video_threads = []
        self.p1_max_similarity = 0
        self.p2_max_similarity = 0
        self.is_game_active = True

        if self.emotion_ids:
            random_emotion_id = random.choice(self.emotion_ids)
            self.set_required_emotion(random_emotion_id)
        
        # 첫 번째 웹캠 스레드
        thread1 = VideoThread(
            camera_index = 0,
            emotion_file = self.current_emotion_file,
            player_index = 0
            )
        thread1.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread1.start()
        self.video_threads.append(thread1)

        # 두 번째 웹캠 스레드
        thread2 = VideoThread(
            camera_index = 1,
            emotion_file = self.current_emotion_file,
            player_index = 1
            )
        thread2.change_pixmap_score_signal.connect(self.update_image_and_score)
        thread2.start()
        self.video_threads.append(thread2)
        
        self.time_left = self.total_game_time
        # ✨ [수정] start_game_clicked에서 타이머를 보이게 했으므로, 여기서는 시간만 설정합니다.
        self.timer_label.setText(f"{self.total_game_time}")
        # ⭐ [수정] OutlinedLabel의 텍스트와 스타일 업데이트
        # self._update_outlined_label_color(self.timer_label, QColor(10, 185, 255), QColor(255, 255, 255))
        
        self.game_timer.start(1000)
        
        print(f"웹캠 스트리밍 및 타이머 작동 시작")
    

    # stop_video_streams 함수 (유지)
    def stop_video_streams(self):
        if self.game_timer.isActive():
            self.game_timer.stop()
        
        self.is_game_active = False
            
        for thread in self.video_threads:
            if thread.isRunning():
                try:
                    thread.change_pixmap_score_signal.disconnect(self.update_image_and_score)
                except Exception:
                    pass
                thread.stop()
        self.video_threads = []
        print("웹캠 스트리밍 및 타이머 작동 종료")

    # go_to_main_menu 함수 (수정: 오버레이 버튼 표시)
    def go_to_main_menu(self):
        self.stop_video_streams()
        
        # 💡 메뉴로 돌아갈 때 오버레이 버튼 다시 표시
        self.start_overlay_button.show()
        self.emotion_label.hide() # 이모지 레이블 숨김
        self.timer_label.hide() 
        
        self.timer_label.setText(f"{self.total_game_time}")
        # ⭐ [수정] OutlinedLabel의 텍스트와 스타일 업데이트
        # self._update_outlined_label_color(self.timer_label, QColor(0, 0, 0), QColor(255, 255, 255))
        self.player1_video.setText('웹캠 1 피드')
        self.player2_video.setText('웹캠 2 피드')
        self.player1_video.setPixmap(QPixmap())
        self.player2_video.setPixmap(QPixmap())
        self.player1_accuracy.setText(f'P1 정확도: 0.00%')
        self.player2_accuracy.setText(f'P2 정확도: 0.00%')
        self.p1_score = 0
        self.p2_score = 0
        self.round = 0
        self.update_score_display()
        self.stacked_widget.setCurrentIndex(0)