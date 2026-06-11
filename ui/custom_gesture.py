"""
Custom Gesture Capture Page
Allow users to create custom gestures by capturing hand poses
"""
import time
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QGroupBox,
    QScrollArea, QMessageBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont

import numpy as np


class CapturePreview(QLabel):
    """Camera preview for gesture capture"""
    frame_captured = pyqtSignal(np.ndarray, list)  # frame, landmarks

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 2px solid #313244;
                border-radius: 10px;
                color: #6c7086;
                font-size: 16px;
            }
        """)
        self.setText("📷\n摄像头预览\n等待捕捉...")
        self._current_pixmap: Optional[QPixmap] = None
        self._capturing = False
        self._countdown = 0

    def update_frame(self, cv_image, landmarks=None):
        """Update camera frame"""
        if cv_image is None:
            return

        try:
            h, w, ch = cv_image.shape
            bytes_per_line = ch * w

            if not cv_image.flags['C_CONTIGUOUS']:
                cv_image = np.ascontiguousarray(cv_image)

            qt_image = QImage(cv_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            qt_image = qt_image.copy()

            self._current_pixmap = QPixmap.fromImage(qt_image)
            self.update()

            # Store landmarks for capture
            if landmarks and self._capturing:
                self._current_landmarks = landmarks

        except Exception as e:
            pass

    def start_capture(self, countdown: int = 3):
        """Start capture countdown"""
        self._capturing = True
        self._countdown = countdown
        self._current_landmarks = None

    def paintEvent(self, event):
        """Custom painting"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        if self._current_pixmap is None:
            painter.fillRect(rect, QColor("#181825"))
            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
            painter.end()
            return

        # Scale and draw pixmap
        scaled = self._current_pixmap.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x = (rect.width() - scaled.width()) // 2
        y = (rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Draw countdown overlay
        if self._capturing and self._countdown > 0:
            overlay_color = QColor(0, 0, 0, 150)
            painter.fillRect(rect, overlay_color)

            painter.setPen(QColor("#89b4fa"))
            painter.setFont(QFont("Arial", 72, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self._countdown))

        # Draw capture frame border
        if self._capturing:
            painter.setPen(QColor("#a6e3a1") if self._countdown == 0 else QColor("#f9e2af"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)

        painter.end()

    def get_captured_landmarks(self):
        """Get captured landmarks"""
        return getattr(self, '_current_landmarks', None)


class GestureCardPreview(QFrame):
    """Preview of a captured gesture"""

    def __init__(self, gesture_name: str, emoji: str, parent=None):
        super().__init__(parent)
        self.gesture_name = gesture_name
        self.emoji = emoji
        self.landmarks = None
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(150, 130)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: #89b4fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Emoji
        self._emoji_label = QLabel(self.emoji)
        self._emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._emoji_label.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        layout.addWidget(self._emoji_label)

        # Name
        self._name_label = QLabel(self.gesture_name)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #cdd6f4; background: transparent; border: none;")
        layout.addWidget(self._name_label)

        # Status
        self._status_label = QLabel("未捕捉")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 10px; color: #6c7086; background: transparent; border: none;")
        layout.addWidget(self._status_label)

    def set_captured(self, captured: bool):
        """Update capture status"""
        if captured:
            self._status_label.setText("已捕捉")
            self._status_label.setStyleSheet("font-size: 10px; color: #a6e3a1; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame {
                    background-color: #313244;
                    border: 2px solid #a6e3a1;
                    border-radius: 10px;
                }
            """)
        else:
            self._status_label.setText("未捕捉")
            self._status_label.setStyleSheet("font-size: 10px; color: #6c7086; background: transparent; border: none;")


class CustomGesturePage(QWidget):
    """
    Custom Gesture Capture Page
    Allow users to create custom gestures
    """

    # Signals
    gesture_captured = pyqtSignal(str, list)  # gesture_name, landmarks
    gesture_saved = pyqtSignal(dict)  # gesture_data

    # Predefined gesture templates
    GESTURE_TEMPLATES = [
        {"name": "自定义 1", "emoji": "👋", "key": "custom_1"},
        {"name": "自定义 2", "emoji": "🤚", "key": "custom_2"},
        {"name": "自定义 3", "emoji": "🖐️", "key": "custom_3"},
        {"name": "自定义 4", "emoji": "✋", "key": "custom_4"},
        {"name": "自定义 5", "emoji": "🖖", "key": "custom_5"},
        {"name": "自定义 6", "emoji": "👌", "key": "custom_6"},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._captured_gestures: Dict[str, list] = {}
        self._current_capture_index = -1
        self._capture_timer = QTimer()
        self._capture_timer.timeout.connect(self._on_capture_tick)
        self._countdown = 0
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left: Camera preview and controls
        left_panel = QVBoxLayout()

        # Camera preview
        self._preview = CapturePreview()
        left_panel.addWidget(self._preview)

        # Capture controls
        controls_group = QGroupBox("捕捉控制")
        controls_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
            }
        """)
        controls_layout = QVBoxLayout(controls_group)

        # Countdown setting
        countdown_layout = QHBoxLayout()
        countdown_layout.addWidget(QLabel("倒计时:"))
        self._countdown_spin = QSpinBox()
        self._countdown_spin.setRange(1, 10)
        self._countdown_spin.setValue(3)
        self._countdown_spin.setSuffix(" 秒")
        countdown_layout.addWidget(self._countdown_spin)
        countdown_layout.addStretch()
        controls_layout.addLayout(countdown_layout)

        # Capture button
        self._capture_btn = QPushButton("开始捕捉")
        self._capture_btn.setFixedHeight(40)
        self._capture_btn.setStyleSheet("""
            QPushButton {
                background: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #94e2d5;
            }
            QPushButton:disabled {
                background: #45475a;
                color: #6c7086;
            }
        """)
        self._capture_btn.clicked.connect(self._start_capture)
        controls_layout.addWidget(self._capture_btn)

        # Status
        self._status_label = QLabel("准备捕捉")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        controls_layout.addWidget(self._status_label)

        left_panel.addWidget(controls_group)

        # Right: Gesture list
        right_panel = QVBoxLayout()

        title = QLabel("自定义手势")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #cdd6f4;")
        right_panel.addWidget(title)

        # Gesture cards grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        self._grid_layout = QGridLayout(scroll_widget)
        self._grid_layout.setSpacing(10)

        # Create gesture cards
        self._gesture_cards = []
        for i, template in enumerate(self.GESTURE_TEMPLATES):
            card = GestureCardPreview(template["name"], template["emoji"])
            card.mousePressEvent = lambda e, idx=i: self._select_gesture(idx)
            self._gesture_cards.append(card)
            self._grid_layout.addWidget(card, i // 2, i % 2)

        scroll.setWidget(scroll_widget)
        right_panel.addWidget(scroll, 1)

        # Save button
        self._save_btn = QPushButton("保存所有手势")
        self._save_btn.setFixedHeight(36)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #74c7ec;
            }
        """)
        self._save_btn.clicked.connect(self._save_gestures)
        right_panel.addWidget(self._save_btn)

        # Add panels to main layout
        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 2)

    def _select_gesture(self, index: int):
        """Select a gesture card for capture"""
        self._current_capture_index = index
        template = self.GESTURE_TEMPLATES[index]
        self._status_label.setText(f"Selected: {template['emoji']} {template['name']}")
        self._capture_btn.setEnabled(True)

    def _start_capture(self):
        """Start capture process"""
        if self._current_capture_index < 0:
            QMessageBox.warning(self, "警告", "请先选择一个手势！")
            return

        self._countdown = self._countdown_spin.value()
        self._capture_btn.setEnabled(False)
        self._preview.start_capture(self._countdown)

        # Start countdown timer
        self._capture_timer.start(1000)
        self._status_label.setText(f"正在捕捉 {self._countdown}...")

    def _on_capture_tick(self):
        """Handle countdown tick"""
        self._countdown -= 1

        if self._countdown > 0:
            self._status_label.setText(f"正在捕捉 {self._countdown}...")
            self._preview._countdown = self._countdown
            self._preview.update()
        else:
            # Capture complete
            self._capture_timer.stop()
            self._capture_gesture()

    def _capture_gesture(self):
        """Capture the current gesture"""
        landmarks = self._preview.get_captured_landmarks()

        if landmarks is None:
            self._status_label.setText("捕捉失败！未检测到手部。")
            self._capture_btn.setEnabled(True)
            return

        # Save captured gesture
        template = self.GESTURE_TEMPLATES[self._current_capture_index]
        gesture_key = template["key"]

        self._captured_gestures[gesture_key] = landmarks

        # Update card
        card = self._gesture_cards[self._current_capture_index]
        card.set_captured(True)

        # Emit signal
        self.gesture_captured.emit(gesture_key, landmarks)

        self._status_label.setText(f"已捕捉: {template['emoji']} {template['name']}")
        self._capture_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "成功",
            f"手势「{template['name']}」捕捉成功！"
        )

    def _save_gestures(self):
        """Save all captured gestures"""
        if not self._captured_gestures:
            QMessageBox.warning(self, "警告", "还没有捕捉任何手势！")
            return

        gesture_data = {
            "gestures": self._captured_gestures,
            "templates": self.GESTURE_TEMPLATES
        }

        self.gesture_saved.emit(gesture_data)

        QMessageBox.information(
            self,
            "已保存",
            f"已保存 {len(self._captured_gestures)} 个自定义手势！"
        )

    def update_camera_frame(self, cv_image, landmarks=None):
        """Update camera preview"""
        self._preview.update_frame(cv_image, landmarks)
