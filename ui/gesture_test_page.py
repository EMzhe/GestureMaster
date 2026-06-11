"""
手势测试页面 - 改进版
实时摄像头识别 + 测试绑定动作
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QFont
import numpy as np


class CameraView(QLabel):
    """摄像头画面显示"""

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
        self.setText("📷\n摄像头画面\n等待启动识别...")
        self._current_pixmap = None

    def update_frame(self, cv_image):
        """更新摄像头画面"""
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
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        if self._current_pixmap is None:
            painter.fillRect(rect, QColor("#181825"))
            painter.setPen(QColor("#6c7086"))
            painter.setFont(QFont("Microsoft YaHei", 14))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
            painter.end()
            return

        scaled = self._current_pixmap.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x = (rect.width() - scaled.width()) // 2
        y = (rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()


class ResultPanel(QFrame):
    """识别结果面板"""

    test_action_clicked = pyqtSignal(str, dict)  # action_type, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
            }
        """)
        self._current_gesture = ""
        self._current_action = ""
        self._current_params = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = QLabel("📊 识别结果")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(title)

        # 手势显示
        self._gesture_label = QLabel("等待识别...")
        self._gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gesture_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #89b4fa; border: none;")
        layout.addWidget(self._gesture_label)

        # 置信度
        conf_label = QLabel("置信度")
        conf_label.setStyleSheet("font-size: 12px; color: #a6adc8; border: none;")
        layout.addWidget(conf_label)

        self._confidence_bar = QProgressBar()
        self._confidence_bar.setRange(0, 100)
        self._confidence_bar.setValue(0)
        self._confidence_bar.setFixedHeight(20)
        self._confidence_bar.setTextVisible(True)
        self._confidence_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._confidence_bar)

        # 稳定性
        stability_label = QLabel("稳定性")
        stability_label.setStyleSheet("font-size: 12px; color: #a6adc8; border: none;")
        layout.addWidget(stability_label)

        self._stability_bar = QProgressBar()
        self._stability_bar.setRange(0, 100)
        self._stability_bar.setValue(0)
        self._stability_bar.setFixedHeight(20)
        self._stability_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._stability_bar)

        layout.addSpacing(10)

        # 绑定动作
        action_title = QLabel("⚡ 绑定动作")
        action_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(action_title)

        self._action_label = QLabel("无")
        self._action_label.setStyleSheet("font-size: 14px; color: #a6e3a1; border: none;")
        self._action_label.setWordWrap(True)
        layout.addWidget(self._action_label)

        # 测试按钮
        self._test_btn = QPushButton("🧪 测试动作")
        self._test_btn.setFixedHeight(36)
        self._test_btn.setStyleSheet("""
            QPushButton {
                background: #f9e2af; color: #1e1e2e;
                font-weight: bold; border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background: #f5c2e7; }
            QPushButton:disabled {
                background: #45475a; color: #6c7086;
            }
        """)
        self._test_btn.setEnabled(False)
        self._test_btn.clicked.connect(self._test_action)
        layout.addWidget(self._test_btn)

        layout.addStretch()

    def update_result(self, gesture_key: str, gesture_name: str, emoji: str,
                      confidence: float, stability: float, action: str, params: dict):
        """更新识别结果"""
        self._gesture_label.setText(f"{emoji} {gesture_name}")
        self._confidence_bar.setValue(int(confidence * 100))
        self._stability_bar.setValue(int(stability * 100))
        self._action_label.setText(action if action else "无")

        self._current_gesture = gesture_key
        self._current_action = action
        self._current_params = params

        # 只有识别稳定时才启用测试按钮
        self._test_btn.setEnabled(stability > 0.8 and action != "")

    def _test_action(self):
        """测试绑定的动作"""
        if self._current_action:
            self.test_action_clicked.emit(self._current_action, self._current_params)

    def reset(self):
        """重置显示"""
        self._gesture_label.setText("等待识别...")
        self._confidence_bar.setValue(0)
        self._stability_bar.setValue(0)
        self._action_label.setText("无")
        self._test_btn.setEnabled(False)


class HistoryTable(QTableWidget):
    """识别历史表格"""

    def __init__(self, parent=None):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(["时间", "手势", "置信度", "动作"])
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                gridline-color: #313244;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        self._max_rows = 30

    def add_entry(self, gesture: str, confidence: float, action: str):
        """添加历史记录"""
        if self.rowCount() >= self._max_rows:
            self.removeRow(0)

        row = self.rowCount()
        self.insertRow(row)

        # 时间
        time_item = QTableWidgetItem(datetime.now().strftime("%H:%M:%S"))
        self.setItem(row, 0, time_item)

        # 手势
        gesture_item = QTableWidgetItem(gesture)
        self.setItem(row, 1, gesture_item)

        # 置信度
        conf_pct = f"{confidence * 100:.0f}%"
        conf_item = QTableWidgetItem(conf_pct)
        if confidence >= 0.8:
            conf_item.setForeground(QColor("#a6e3a1"))
        elif confidence >= 0.5:
            conf_item.setForeground(QColor("#f9e2af"))
        else:
            conf_item.setForeground(QColor("#f38ba8"))
        self.setItem(row, 2, conf_item)

        # 动作
        action_item = QTableWidgetItem(action if action else "无")
        self.setItem(row, 3, action_item)

        self.scrollToBottom()

    def clear_history(self):
        """清空历史"""
        self.setRowCount(0)


class GestureTestPageImproved(QWidget):
    """
    手势测试页面 - 改进版
    实时摄像头识别 + 测试绑定动作
    """

    # 信号
    test_action_requested = pyqtSignal(str, dict)  # action_type, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 左侧：摄像头画面
        left_panel = QVBoxLayout()

        self._camera_view = CameraView()
        left_panel.addWidget(self._camera_view)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self._clear_btn = QPushButton("🧹 清除历史")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: #f38ba8; color: #1e1e2e;
                font-weight: bold; border: none;
                border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background: #eba0ac; }
        """)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()
        left_panel.addLayout(btn_layout)

        # 右侧：结果 + 历史
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # 识别结果面板
        self._result_panel = ResultPanel()
        self._result_panel.test_action_clicked.connect(self.test_action_requested.emit)
        right_splitter.addWidget(self._result_panel)

        # 历史记录
        history_frame = QFrame()
        history_frame.setFrameShape(QFrame.Shape.StyledPanel)
        history_frame.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
            }
        """)
        history_layout = QVBoxLayout(history_frame)
        history_layout.setContentsMargins(8, 8, 8, 8)

        history_title = QLabel("📜 识别历史")
        history_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4; border: none;")
        history_layout.addWidget(history_title)

        self._history_table = HistoryTable()
        history_layout.addWidget(self._history_table)

        # 清除按钮连接
        self._clear_btn.clicked.connect(self._history_table.clear_history)

        right_splitter.addWidget(history_frame)
        right_splitter.setSizes([300, 200])

        # 主布局
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(QWidget())  # 占位
        main_splitter.widget(0).setLayout(left_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([500, 300])

        main_layout.addWidget(main_splitter)

    def update_camera_frame(self, cv_image):
        """更新摄像头画面"""
        self._camera_view.update_frame(cv_image)

    def update_recognition(self, gesture_key: str, gesture_name: str, emoji: str,
                          confidence: float, stability: float, action: str, params: dict):
        """更新识别结果"""
        self._result_panel.update_result(
            gesture_key, gesture_name, emoji,
            confidence, stability, action, params
        )

        # 稳定时添加到历史
        if stability > 0.8:
            self._history_table.add_entry(
                f"{emoji} {gesture_name}",
                confidence,
                action
            )

    def reset(self):
        """重置页面"""
        self._result_panel.reset()
        self._history_table.clear_history()
