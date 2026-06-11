"""
摄像头预览组件
显示实时摄像头画面，叠加手部骨架和手势识别结果。
"""

from typing import Optional
import numpy as np
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QFont, QColor


class CameraWidget(QWidget):
    """
    摄像头预览组件。

    Signals:
        gesture_detected(str, float): 手势变化时发射
    """

    gesture_detected = pyqtSignal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self._current_pixmap: Optional[QPixmap] = None
        self._gesture_name: str = ""
        self._gesture_emoji: str = ""
        self._confidence: float = 0.0
        self._fps: float = 0.0
        self._last_gesture: str = ""
        self._placeholder = "摄像头预览\n等待启动..."

    def set_frame(self, cv_image: np.ndarray):
        """
        接收 RGB numpy 数组并更新显示。
        【修复】确保 QImage 引用的内存有效。
        """
        if cv_image is None:
            return

        try:
            h, w, ch = cv_image.shape
            bytes_per_line = ch * w

            # 【修复】确保数据连续且保持引用
            if not cv_image.flags['C_CONTIGUOUS']:
                cv_image = np.ascontiguousarray(cv_image)

            # 创建 QImage（使用 copy 确保内存独立）
            qt_image = QImage(cv_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            # 【修复】copy() 使 QImage 拥有自己的内存，避免悬空引用
            qt_image = qt_image.copy()

            self._current_pixmap = QPixmap.fromImage(qt_image)
            self.update()
        except Exception as e:
            pass  # 静默忽略帧处理异常

    def set_gesture_info(self, gesture_name: str, confidence: float, emoji: str = ""):
        """设置当前识别的手势信息。"""
        self._gesture_name = gesture_name
        self._confidence = confidence
        self._gesture_emoji = emoji

        if gesture_name != self._last_gesture and gesture_name:
            self._last_gesture = gesture_name
            self.gesture_detected.emit(gesture_name, confidence)

    def set_fps(self, fps: float):
        """设置 FPS 显示。"""
        self._fps = fps

    def paintEvent(self, event):
        """自定义绘制：摄像头画面 + 叠加信息。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        if self._current_pixmap is None:
            painter.fillRect(rect, QColor("#181825"))
            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._placeholder)
            painter.end()
            return

        # 缩放保持宽高比
        scaled = self._current_pixmap.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 居中绘制
        x = (rect.width() - scaled.width()) // 2
        y = (rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # 叠加手势信息
        if self._gesture_name:
            self._draw_overlay(painter)

        # FPS 显示
        if self._fps > 0:
            painter.setPen(QColor("#a6e3a1"))
            painter.setFont(QFont("Consolas", 10))
            painter.drawText(rect.right() - 80, rect.top() + 20, f"FPS: {self._fps:.0f}")

        painter.end()

    def _draw_overlay(self, painter: QPainter):
        """绘制手势信息叠加层。"""
        rect = self.rect()

        # 顶部半透明背景条
        overlay_rect = rect.adjusted(0, 0, 0, -(rect.height() - 40))
        painter.fillRect(overlay_rect, QColor(0, 0, 0, 150))

        # 手势名称
        painter.setPen(QColor("#89b4fa"))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        label = f"{self._gesture_emoji} {self._gesture_name}" if self._gesture_emoji else self._gesture_name
        painter.drawText(10, 28, label)

        # 置信度条
        bar_x = 250
        bar_y = 12
        bar_w = 200
        bar_h = 16

        painter.setBrush(QColor("#313244"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 4, 4)

        fill_w = int(bar_w * self._confidence)
        if self._confidence >= 0.8:
            color = QColor("#a6e3a1")
        elif self._confidence >= 0.5:
            color = QColor("#f9e2af")
        else:
            color = QColor("#f38ba8")
        painter.setBrush(color)
        painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 4, 4)

        painter.setPen(QColor("#cdd6f4"))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(bar_x + bar_w + 8, bar_y + 13, f"{self._confidence:.0%}")

    def clear(self):
        """清除画面。"""
        self._current_pixmap = None
        self._gesture_name = ""
        self._confidence = 0.0
        self.update()
