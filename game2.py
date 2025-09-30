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
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QPainter, QPainterPath, QPen, QBrush, QColor
from game1 import Game1Screen,Resultscreen
from mainmenu import MainMenu
from game1 import VideoThread
from compare import calc_similarity
from mainmenu import flag

# ======================================================================
# ⭐ 1. 텍스트 테두리 기능을 위한 사용자 정의 QLabel 클래스 (추가된 부분) ⭐
# ======================================================================
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

        # 1. 테두리 설정 (QPen)
        outline_pen = QPen(self.outline_color, self.outline_width)
        outline_pen.setJoinStyle(Qt.RoundJoin) # 테두리 모서리를 둥글게 처리
        painter.setPen(outline_pen)

        # 2. 채우기 설정 (QBrush)
        fill_brush = QBrush(self.fill_color)
        painter.setBrush(fill_brush)

        # 3. 경로 그리기 (테두리와 채우기 모두 적용)
        painter.drawPath(path)
# ======================================================================


class EmojiMatchThread(QThread): # VideoThread가 QThread를 상속한다고 가정
    # QImage만 전송합니다.
    change_pixmap_signal = pyqtSignal(QImage)

    def __init__(self, camera_index, all_emotion_files, width=400, height=300):
        super().__init__()
        self.camera_index = camera_index
        self.all_emotion_files = all_emotion_files
        self.width = width
        self.height = height
        self.running = True

        # ✨ 수정: current_frame_rgb를 OpenCV/NumPy 포맷으로 저장
        self.current_frame_rgb = None

    def stop(self):
        self.running = False

    def run(self):
        # cap = cv2.VideoCapture(self.camera_index)
        # 윈도우 환경에서 카메라 인덱스 0이 아닌 경우를 대비해 DSHOW 백엔드 사용
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

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

                # ✨ 업데이트: QImage가 아닌 NumPy 배열(OpenCV RGB 프레임)을 저장
                self.current_frame_rgb = rgb_image.copy()

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

# ----------------------------------------------------------------------
# 7. 이모지 매칭 화면 (Game2Screen)
# ----------------------------------------------------------------------
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
        # ⭐ 수정된 부분: QLabel 대신 OutlinedLabel 사용 ⭐
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
        # ⭐ 수정된 부분 끝 ⭐

        # 상단 레이아웃 (제목만 포함, 이전 back_btn은 제거)
        top_h_layout = QHBoxLayout()
        title = QLabel("설명설명설명설 명설명설명설명 설명설명설명설 명설명설명설명")
        title.setFont(QFont('Jalnan Gothic', 20))
        title.setStyleSheet("background-color: 'transparent'; color: #292E32; padding-left: 20px; padding-top: 20px;")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 기존 텍스트 back_btn을 제거했습니다.
        # back_btn = QPushButton("메인 메뉴로 돌아가기") # 제거

        top_h_layout.addWidget(title, 1)
        top_h_layout.addStretch(1)
        main_layout.addLayout(top_h_layout)

        # 수직 중앙 정렬을 위한 상단 간격
        main_layout.addSpacing(165)
        
        # ====================================================================
        # 웹캠/이모지 그룹과 유사도 레이블/다시하기 버튼을 묶는 컨테이너 (QVBoxLayout)
        # ====================================================================
        center_v_container_layout = QVBoxLayout()
        center_v_container_layout.setAlignment(Qt.AlignCenter) 

        # 중앙 콘텐츠 레이아웃 (웹캠, 이모지/버튼 그룹) (QHBoxLayout)
        center_h_layout = QHBoxLayout()
        center_h_layout.setAlignment(Qt.AlignCenter) 

        # ----------------------------------------------------------------------
        # 웹캠 영역 (QLabel)
        # ----------------------------------------------------------------------
        # 웹캠 피드 QLabel
        self.video_label = QLabel('웹캠 피드 (400x300)')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(flag['VIDEO_WIDTH'], flag['VIDEO_HEIGHT'])
        self.video_label.setStyleSheet("background-color: black; color: white;")
        
        # ----------------------------------------------------------------------
        # QStackedWidget 설정: 버튼과 이모지를 같은 위치에 전환
        # ----------------------------------------------------------------------
        self.emoji_stack = QStackedWidget()
        stack_size = QSize(240, 240) 
        self.emoji_stack.setFixedSize(stack_size)
        self.emoji_stack.setStyleSheet("background-color: transparent;")

        # 1. 캡처 버튼 설정
        self.capture_btn = QPushButton("") 
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

        # 2. 추천 이모지 라벨 설정
        self.emoji_image = QLabel('이모지 준비 중...')
        self.emoji_image.setAlignment(Qt.AlignCenter)
        self.emoji_image.setFixedSize(stack_size) 
        self.emoji_image.setFont(QFont('Jalnan Gothic', 20))

        # 3. StackedWidget에 위젯 추가 
        self.emoji_stack.addWidget(self.capture_btn) # 인덱스 0: 캡처 버튼 (초기 화면)
        self.emoji_stack.addWidget(self.emoji_image) # 인덱스 1: 이모지 결과
        
        # ----------------------------------------------------------------------
        
        # 유사도 라벨
        self.similarity_label = QLabel('📸 찰칵! 버튼을 눌러주세요 📸')
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
        
        # 유사도 라벨과 다시하기 버튼 사이의 간격 (35픽셀)
        center_v_container_layout.addSpacing(32) 
        
        center_v_container_layout.addWidget(self.retry_btn, alignment=Qt.AlignCenter) 

        main_layout.addLayout(center_v_container_layout)
        # ====================================================================
        
        # 5. 중앙 컨테이너를 상단으로 밀어 올리기 위한 Stretch
        # 이 stretch가 중앙 컨테이너와 하단 버튼 사이의 모든 수직 공간을 차지합니다.
        main_layout.addStretch(1) 


        # 6. 메인 메뉴로 돌아가기 (이미지 아이콘) 버튼 생성
        self.back_btn = QPushButton("", self)
        
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
        
        # *** 우측 하단 버튼에 대한 고유 스타일시트 적용 ***
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

        # 7. 우측 하단 배치를 위한 하단 레이아웃
        bottom_h_layout = QHBoxLayout()
        bottom_h_layout.addStretch(1) # 버튼을 오른쪽 끝으로 밀어냅니다.
        bottom_h_layout.addWidget(self.back_btn)
        # 하단 버튼의 위치를 화면 끝에서 띄워줍니다.
        bottom_h_layout.setContentsMargins(0, 0, 30, 30) 
        
        main_layout.addLayout(bottom_h_layout)

        self.setLayout(main_layout)

    def update_match(self, image):
        """스레드에서 받은 웹캠 이미지를 업데이트합니다."""
        # 이 함수는 스트리밍 중에만 호출됩니다.
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)

    def start_stream(self):
        self.stop_stream()

        self.video_thread = EmojiMatchThread(
            camera_index=0,
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
        # 1. 유사도 텍스트 초기화
        self.similarity_label.setText('📸 찰칵! 버튼을 눌러주세요 📸')
        
        # 2. 스트리밍 다시 시작 (내부적으로 stop_stream 호출 후 start_stream 호출)
        # start_stream에서 캡처 버튼을 보이고, 다시하기 버튼을 숨깁니다.
        self.start_stream() 


    def go_to_main_menu(self):
        self.stop_stream()
        self.similarity_label.setText('📸 찰칵! 버튼을 눌러주세요 📸')
        self.stacked_widget.setCurrentIndex(0)

    def capture_and_match(self):
        """버튼 클릭 시 스트리밍을 멈추고 최종 프레임으로 유사도 계산을 수행합니다."""
        if self.video_thread and self.video_thread.isRunning():
            # 1. 현재 스레드의 프레임 데이터 (OpenCV/NumPy) 가져오기
            frame_to_process = self.video_thread.current_frame_rgb

            # 2. 스레드 멈추기
            self.stop_stream()
            
            # 3. 가져온 프레임이 유효하면 이모지 매칭 실행
            if frame_to_process is not None:
                self.get_best_emoji(frame_to_process)
            else:
                print("Warning: No frame captured to process.")
        else:
            self.start_stream()

    def get_best_emoji(self, rgb_image):
        # NOTE: 이 함수를 실행하려면 'compare' 모듈과 'faces.csv' 파일이 필요합니다.
        try:
            from compare import extract_blendshape_scores, compare_blendshape_scores
            import pandas as pd
            import re
        except ImportError as e:
            print(f"Error: Required modules (pandas, re, compare.py functions) not found. Cannot perform emoji matching logic. {e}")
            # GUI만 업데이트하고 로직은 생략
            best_similarity = 0.0
            best_match_emoji = self.emotion_files[0] if self.emotion_files else "0_placeholder.png"
            # return # 실제 환경에서는 여기서 return

        """캡처된 OpenCV 이미지로 유사도를 계산하고 GUI를 업데이트합니다."""
        best_similarity = 0.0
        best_match_emoji = self.emotion_files[0] if self.emotion_files else "0_placeholder.png"

        # 임시 로직 (실제 모듈이 없을 경우)
        try:
            features = pd.read_csv('faces.csv')
            blend1 = extract_blendshape_scores(rgb_image)
            # 유사도 계산 로직
            for emoji_file in self.emotion_files:
                try:
                    # 파일 이름에서 숫자 레이블 추출
                    match = re.search(r'^(\d+)_', emoji_file)
                    if match:
                        label = int(match.group(1))
                    else:
                        continue # 레이블을 찾을 수 없는 파일은 건너뛰기

                    feature_row = features[features["labels"] == label]
                    if feature_row.empty:
                        continue
                    
                    feature = feature_row.iloc[0].to_dict() # Series를 dict로 변환
                    
                    # blend2 = {k: feature[k] for k in feature if k != 'labels'} 
                    blend2 = feature # compare_blendshape_scores 함수가 처리할 수 있도록 전체 dict 전달

                    similarity = compare_blendshape_scores(blend1, blend2)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_emoji = emoji_file
                except Exception as e:
                    # print(f"Similarity calculation failed for {emoji_file}: {e}")
                    continue
        except NameError:
            print("Skipping actual matching due to missing imports/files.")
        except FileNotFoundError:
            print("Skipping actual matching: faces.csv not found.")
        except Exception as e:
            print(f"An error occurred during matching logic: {e}")


        # GUI 업데이트
        
        # 1. 웹캠 레이블에 캡처된 정지 프레임 표시 (OpenCV -> QPixmap 변환)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # 비디오 레이블 크기에 맞게 조정
        p = q_img.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(QPixmap.fromImage(p))

        # 2. 추천 이모지 이미지 업데이트
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

        # 3. 유사도 텍스트 업데이트
        self.similarity_label.setText(f'🎉 얼굴 분석 결과... 추천해드린 이모지와 {best_similarity: .2f}% 닮으셨네요! 🎉')