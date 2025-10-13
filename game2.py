import sys
import cv2
import time
import os
#import mediapipe as mp
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPointF
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QPainter, QPainterPath, QPen, QBrush, QColor, QCursor, QMouseEvent
from game1 import Game1Screen,Resultscreen
from mainmenu import MainMenu
from game1 import VideoThread
from compare import calc_similarity
from mainmenu import flag

# ClickableLabel 클래스 재사용
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
        
# 텍스트 테두리 기능을 위한 사용자 정의 QLabel 클래스
class OutlinedLabel(QLabel):
    def __init__(self, text, font, fill_color, outline_color, outline_width, parent=None):
        super().__init__(text, parent)
        self.setFont(font)
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 부드러운 렌더링

        text = self.text()
        font = self.font()
        
        path = QPainterPath()
        
        rect = self.contentsRect()
        
        fm = painter.fontMetrics()
        text_height = fm.height()
        
        # Y 위치: (높이 - 텍스트 높이) / 2 + 폰트 높이의 80% 정도 (기준선 위치)
        y = rect.top() + (rect.height() - text_height) // 2 + fm.ascent()
        
        # X 위치: 스타일시트의 padding-left: 20px를 수동으로 적용
        x = rect.left() + 20 

        # QPainterPath에 텍스트를 폰트와 함께 추가합니다.
        path.addText(QPointF(x, y), font, text)

        # 테두리 설정 (QPen)
        outline_pen = QPen(self.outline_color, self.outline_width)
        outline_pen.setJoinStyle(Qt.RoundJoin) # 테두리 모서리를 둥글게 처리
        painter.setPen(outline_pen)

        # 채우기 설정 (QBrush)
        fill_brush = QBrush(self.fill_color)
        painter.setBrush(fill_brush)

        # 경로 그리기 (테두리와 채우기 모두 적용)
        painter.drawPath(path)

# 웹캠 연결 Thread
class EmojiMatchThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)

    def __init__(self, camera_index, all_emotion_files, width=flag['VIDEO_WIDTH'], height=flag['VIDEO_HEIGHT']):
        super().__init__()
        self.camera_index = camera_index
        self.all_emotion_files = all_emotion_files
        self.width = width
        self.height = height
        self.running = True

        # current_frame_rgb를 OpenCV/NumPy 포맷으로 저장
        self.current_frame_rgb = None

    def stop(self):
        self.running = False

    def run(self):
        # 카메라 인덱스 0이 아닌 경우를 대비해 DSHOW 백엔드 사용
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
                self.current_frame_rgb = rgb_image
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w

                # 웹캠 화면 업데이트를 위한 QImage 변환
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                p = convert_to_Qt_format.scaled(self.width, self.height, Qt.KeepAspectRatio)

                # 웹캠 화면 업데이트 시그널 전송
                self.change_pixmap_signal.emit(p)

            self.msleep(50)

        if cap.isOpened():
              cap.release()
        print(f"Camera {self.camera_index} released and EmojiMatchThread terminated.")

# Game 2 GUI
class Game2Screen(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.video_thread = None

        EMOJI_DIR = "img/emoji"
        try:
            self.emotion_files = [
                f for f in os.listdir(EMOJI_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')
            ]
        except FileNotFoundError:
            print(f"Error: 이모지 디렉토리 ({EMOJI_DIR})를 찾을 수 없습니다. 테스트 이모지 사용.")
            self.emotion_files = ["0_placeholder.png"]

        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 상단 Mode 바
        font = QFont('ARCO', 30, QFont.Bold)
        fill_color = QColor("#FF5CA7")      
        outline_color = QColor("#FFF0FA")
        outline_width = 3.5             
        
        mode_bar = OutlinedLabel(
            "MODE2", 
            font, 
            fill_color, 
            outline_color, 
            outline_width,
            self
        )
        # styleSheet에서 color와 padding-left를 제거하고 background-color만 남깁니다.
        mode_bar.setStyleSheet("background-color: #FFE10A;") 
        mode_bar.setFixedHeight(85)
        mode_bar.setFixedWidth(1920)
        main_layout.addWidget(mode_bar)

        # 상단 레이아웃
        top_h_layout = QHBoxLayout()
        title = QLabel("카메라 버튼을 누르시면 본인과 닮은 이모지를 추천해드립니다!")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        main_layout.addLayout(top_h_layout)

        # 수직 중앙 정렬을 위한 상단 간격
        main_layout.addSpacing(165)
        
        # ClickableLabel 기능(커서 변경)을 구현할 임시 클래스 정의
        class ClickableButton(QPushButton):
            def enterEvent(self, event):
                # 마우스 포인터를 '손가락' 모양으로 설정
                self.setCursor(QCursor(Qt.PointingHandCursor))
                super().enterEvent(event)

            def leaveEvent(self, event):
                # 마우스 포인터를 기본 모양(화살표)으로 되돌림
                self.unsetCursor() 
                super().leaveEvent(event)
        
        # 웹캠/이모지 그룹과 유사도 레이블/다시하기 버튼을 묶는 컨테이너 (QVBoxLayout)
        center_v_container_layout = QVBoxLayout()
        center_v_container_layout.setAlignment(Qt.AlignCenter) 

        # 중앙 콘텐츠 레이아웃 (웹캠, 이모지/버튼 그룹) (QHBoxLayout)
        center_h_layout = QHBoxLayout()
        center_h_layout.setAlignment(Qt.AlignCenter) 

        # 웹캠 피드 QLabel
        self.video_label = QLabel(f'웹캠 피드 ({flag["VIDEO_WIDTH"]}x{flag["VIDEO_HEIGHT"]})')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.video_label.setStyleSheet("background-color: black; color: white;")
        
        # QStackedWidget 설정: 버튼과 이모지를 같은 위치에 전환
        self.emoji_stack = QStackedWidget()
        stack_size = QSize(240, 240) 
        self.emoji_stack.setFixedSize(stack_size)
        self.emoji_stack.setStyleSheet("background-color: transparent;")

        # 1. 캡처 버튼 설정 (ClickableButton으로 교체)
        self.capture_btn = ClickableButton("")
        self.capture_btn.setFixedSize(stack_size) 
        
        icon_path = "design/capture.png"
        capture_icon = QPixmap(icon_path)
        
        if not capture_icon.isNull():
            icon = QIcon(capture_icon)
            self.capture_btn.setIcon(icon)
            self.capture_btn.setIconSize(QSize(200, 200)) 
            self.capture_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: transparent; 
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 50); 
                }
            """)
        else:
            self.capture_btn.setText("이모지 추천/캡쳐")
            print(f"Error: 캡처 이미지 ({icon_path})를 로드할 수 없습니다. 텍스트 버튼으로 대체합니다.")
            
        self.capture_btn.clicked.connect(self.capture_and_match)

        # 추천 이모지 라벨 설정
        self.emoji_image = QLabel('이모지 준비 중...')
        self.emoji_image.setAlignment(Qt.AlignCenter)
        self.emoji_image.setFixedSize(stack_size) 
        self.emoji_image.setFont(QFont('Jalnan Gothic', 20))

        # StackedWidget에 위젯 추가 
        self.emoji_stack.addWidget(self.capture_btn) # 인덱스 0: 캡처 버튼 (초기 화면)
        self.emoji_stack.addWidget(self.emoji_image) # 인덱스 1: 이모지 결과
        
        # 유사도 라벨
        self.similarity_label = QLabel('📷 카메라 버튼을 눌러주세요! 찰칵~ 📷')
        self.similarity_label.setFont(QFont('Jalnan 2', 30))
        self.similarity_label.setStyleSheet("color: #323232;")
        self.similarity_label.setAlignment(Qt.AlignCenter)
        
        # 다시하기 버튼
        self.retry_btn = QPushButton("다시하기")
        self.retry_btn.setFont(QFont('Jalnan 2', 24, QFont.Bold))
        self.retry_btn.setFixedSize(200, 70)
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5CA7; 
                color: white; 
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #FF77BB;
            }
        """)
        self.retry_btn.clicked.connect(self.reset_game)
        self.retry_btn.hide() # 초기에는 숨김

        
        # 웹캠 위젯과 StackedWidget 배치
        center_h_layout.addWidget(self.video_label) # 웹캠 QLabel을 직접 추가
        center_h_layout.addSpacing(100)
        center_h_layout.addWidget(self.emoji_stack) 
        
        # 중앙 수직 컨테이너에 수평 레이아웃, 유사도 레이블, 다시하기 버튼 추가
        center_v_container_layout.addLayout(center_h_layout)
        center_v_container_layout.addSpacing(40) 
        center_v_container_layout.addWidget(self.similarity_label)
        
        # 유사도 라벨과 다시하기 버튼 사이의 간격
        center_v_container_layout.addSpacing(32) 
        
        center_v_container_layout.addWidget(self.retry_btn, alignment=Qt.AlignCenter) 

        main_layout.addLayout(center_v_container_layout)
        
        # 중앙 컨테이너를 상단으로 밀어 올리기 위한 Stretch
        # 이 stretch가 중앙 컨테이너와 하단 버튼 사이의 모든 수직 공간을 차지합니다.
        main_layout.addStretch(1) 


        # 6. 메인 메뉴로 돌아가기 (이미지 아이콘) 버튼 생성
        self.back_btn = ClickableButton("", self)
        # Geometry 대신 고정 크기 사용
        self.back_btn.setFixedSize(flag['BUTTON_EXIT_WIDTH'], flag['BUTTON_EXIT_HEIGHT']) 
        # *** 우측 하단 버튼 스타일 분리를 위한 고유 이름 설정 ***
        self.back_btn.setObjectName("BottomRightIcon")
        
        # 아이콘 이미지 설정 및 크기 조정
        icon_path = flag['MAIN_BUTTON_IMAGE']
        icon_pixmap = QPixmap(icon_path)
        
        icon_size = QSize(
            flag['BUTTON_EXIT_WIDTH'] - flag['BUTTON_EXIT_MARGIN'], 
            flag['BUTTON_EXIT_HEIGHT'] - flag['BUTTON_EXIT_MARGIN']
        )
        scaled_icon = icon_pixmap.scaled(
            icon_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.back_btn.setIcon(QIcon(scaled_icon))
        self.back_btn.setIconSize(scaled_icon.size())
        
        # 버튼 클릭 이벤트 연결
        self.back_btn.clicked.connect(self.go_to_main_menu)
        
        # 우측 하단 버튼에 대한 고유 스타일시트 적용
        unique_style = """
            QPushButton#BottomRightIcon {
                background-color: transparent; /* 기본 상태: 투명 유지 */
                border-radius: 20px;
                border: none;
                color: transparent; /* 텍스트는 없으므로 투명하게 설정 */
            }
            QPushButton#BottomRightIcon:hover {
                background-color: rgba(255, 255, 255, 0.2); /* 마우스 오버 시: 약간의 투명한 흰색 배경 */
            }
            QPushButton#BottomRightIcon:pressed {
                background-color: rgba(255, 255, 255, 0.4); /* 클릭 시: 더 진한 투명한 흰색 배경 */
            }
        """
        self.back_btn.setStyleSheet(unique_style)

        # 우측 하단 배치를 위한 하단 레이아웃
        bottom_h_layout = QHBoxLayout()
        bottom_h_layout.addStretch(1)
        bottom_h_layout.addWidget(self.back_btn)
        # 하단 버튼의 위치를 화면 끝에서 띄워줍니다.
        bottom_h_layout.setContentsMargins(0, 0, 20, 20) 
        
        main_layout.addLayout(bottom_h_layout)

        self.setLayout(main_layout)

    def update_match(self, image):
        """스레드에서 받은 웹캠 이미지를 업데이트합니다."""
        # 이 함수는 스트리밍 중에만 호출됩니다.
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)

    def get_available_camera_index(self):
        """사용 가능한 가장 낮은 인덱스의 웹캠 번호를 반환합니다."""
        # 0부터 9까지 시도하며, 먼저 열리는 카메라의 인덱스를 반환
        for index in range(10): 
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                print(f"camera {index} available")
                return index
        return 0 # 찾지 못하면 기본값 0 반환

    def start_stream(self):
        self.stop_stream()

        self.video_thread = EmojiMatchThread(
            camera_index=self.get_available_camera_index(),
            all_emotion_files=self.emotion_files,
            width=flag['VIDEO_WIDTH'],
            height=flag['VIDEO_HEIGHT']
        )
        self.video_thread.change_pixmap_signal.connect(self.update_match)
        self.video_thread.start()
        print("이모지 매칭 스트리밍 시작")
        
        # QStackedWidget 설정: 캡처 버튼 보이기 (인덱스 0)
        self.emoji_stack.setCurrentIndex(0)
        # 다시하기 버튼 숨기기
        self.retry_btn.hide()


    def stop_stream(self):
        if self.video_thread and self.video_thread.isRunning():
            try:
                # 시그널 연결 해제
                self.video_thread.change_pixmap_signal.disconnect(self.update_match)
            except Exception:
                pass

            self.video_thread.stop()
            self.video_thread.wait() # 스레드가 완전히 종료될 때까지 대기
            self.video_thread = None
            print("이모지 매칭 스트리밍 종료")
            
    # 다시하기 버튼 클릭 시 호출될 메서드
    def reset_game(self):
        """이모티콘을 숨기고, 캡처 버튼을 다시 표시하며, 유사도 텍스트를 초기화한 후 스트리밍을 시작합니다."""
        print("게임 재시작 (다시하기) 요청")
        # 유사도 텍스트 초기화
        self.similarity_label.setText('📷 카메라 버튼을 눌러주세요! 찰칵~ 📷')
        
        # 스트리밍 다시 시작 (내부적으로 stop_stream 호출 후 start_stream 호출)
        self.start_stream() 


    def go_to_main_menu(self):
        self.stop_stream()
        self.similarity_label.setText('📷 카메라 버튼을 눌러주세요! 찰칵~ 📷')
        self.stacked_widget.setCurrentIndex(0)

    def capture_and_match(self):
        """버튼 클릭 시 스트리밍을 멈추고 최종 프레임으로 유사도 계산을 수행합니다."""
        if self.video_thread and self.video_thread.isRunning():
            # 현재 스레드의 프레임 데이터 (OpenCV/NumPy) 가져오기
            frame_to_process = self.video_thread.current_frame_rgb

            # 스레드 멈추기
            self.stop_stream()
            # 가져온 프레임이 유효하면 이모지 매칭 실행
            if frame_to_process is not None:
                self.get_best_emoji(frame_to_process)
            else:
                print("Warning: No frame captured to process.")
        else:
            self.start_stream()

    def get_best_emoji(self, rgb_image):
        try:
            from compare import extract_blendshape_scores, compare_blendshape_scores
            from person_in_frame import person_in_frame
            import pandas as pd
            import re
            """캡처된 OpenCV 이미지로 유사도를 계산하고 GUI를 업데이트합니다."""
            best_similarity = 0.0
            best_match_emoji = self.emotion_files[0] if self.emotion_files else "0_angry.png"
            bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            # 현재 frame의 blendshape값 계산
            person = cv2.cvtColor(person_in_frame(bgr_image), cv2.COLOR_BGR2RGB)
            blend1 = extract_blendshape_scores(person)

            # 미리 저장된 blendshape 값 불러오기
            features = pd.read_csv('faces.csv')
            
            # 유사도 계산 로직
            for emoji_file in self.emotion_files:
                try:
                    label = int(re.sub(r'(\_)(\w+)(\.\w+)?$', '', emoji_file))
                    feature = features[features["labels"] == label].values[0]
                    blend2 = {features.keys()[i]: feature[i] for i in range(len(features.keys()))}
                    similarity = compare_blendshape_scores(blend1, blend2)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_emoji = emoji_file
                except Exception as e:
                    print(f"Similarity calculation failed for {emoji_file}: {e}")
                    continue
        except:
            print("유사도 검색 실패!")

        # GUI 업데이트
        
        # 웹캠 레이블에 캡처된 정지 프레임 표시 (OpenCV -> QPixmap 변환)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # 비디오 레이블 크기에 맞게 조정
        p = q_img.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(QPixmap.fromImage(p))

        # 추천 이모지 이미지 업데이트
        file_path = os.path.join("img/emoji", best_match_emoji)
        pixmap_emoji = QPixmap(file_path)
        if not pixmap_emoji.isNull():
            scaled_pixmap = pixmap_emoji.scaled(
                self.emoji_image.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.emoji_image.setPixmap(scaled_pixmap)
            
            # QStackedWidget 설정: 이모지 보이기 (인덱스 1)
            self.emoji_stack.setCurrentIndex(1)
            # 다시하기 버튼 보이기
            self.retry_btn.show()

        # 유사도 텍스트 업데이트
        self.similarity_label.setText(f'🎉 얼굴 분석 결과... 추천해드린 이모지와 {best_similarity: .2f}% 닮으셨네요! 🎉')