"""
手势测试页面 - 提供实时手势识别测试和调试功能
包括摄像头预览、识别结果展示、手势历史记录和快速测试按钮。
"""

import time
from datetime import datetime
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QFrame, QSplitter,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter


# ---------------------------------------------------------------------------
# 置信度进度条（自定义颜色）
# ---------------------------------------------------------------------------

class ConfidenceBar(QProgressBar):
    """根据置信度值变色的进度条：红(低) -> 黄(中) -> 绿(高)。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setFixedHeight(20)
        self.setTextVisible(True)
        self.setFormat("%p%")

    def set_confidence(self, value: float):
        """设置置信度 (0.0 ~ 1.0)。"""
        pct = int(value * 100)
        self.setValue(pct)
        # 根据置信度设置颜色
        if pct >= 80:
            color = "#a6e3a1"  # 绿色
        elif pct >= 50:
            color = "#f9e2af"  # 黄色
        else:
            color = "#f38ba8"  # 红色
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                text-align: center;
                color: #cdd6f4;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)


# ---------------------------------------------------------------------------
# 摄像头预览组件
# ---------------------------------------------------------------------------

class CameraPreview(QLabel):
    """摄像头画面预览，支持占位符和缩放显示。"""

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
        self.setText("📷\n摄像头预览\n等待启动...")
        self._current_pixmap: Optional[QPixmap] = None

    def update_frame(self, cv_image):
        """接收 RGB numpy array 并显示。"""
        import numpy as np
        h, w, ch = cv_image.shape
        bytes_per_line = ch * w
        if not cv_image.flags['C_CONTIGUOUS']:
            cv_image = np.ascontiguousarray(cv_image)
        qt_image = QImage(cv_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        qt_image = qt_image.copy()  # 确保内存独立
        pixmap = QPixmap.fromImage(qt_image)
        self._current_pixmap = pixmap
        # 缩放到控件大小，保持宽高比
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def set_placeholder(self, text: str):
        """显示占位文本。"""
        self.clear()
        self._current_pixmap = None
        self.setText(text)


# ---------------------------------------------------------------------------
# 识别结果面板
# ---------------------------------------------------------------------------

class RecognitionResultPanel(QFrame):
    """右侧识别结果展示面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel("📊 识别结果")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(title)

        # 当前手势
        self._gesture_label = QLabel("等待识别...")
        self._gesture_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa; border: none;")
        self._gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._gesture_label)

        # 置信度
        conf_label = QLabel("置信度")
        conf_label.setStyleSheet("font-size: 13px; color: #a6adc8; border: none;")
        layout.addWidget(conf_label)
        self._confidence_bar = ConfidenceBar()
        layout.addWidget(self._confidence_bar)

        layout.addSpacing(10)

        # 手部信息
        info_title = QLabel("🤚 手部信息")
        info_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(info_title)

        self._hand_info_labels = {}
        info_items = [
            ("hand", "检测到"),
            ("fingers", "伸展手指"),
            ("landmarks", "关键点数"),
            ("fps", "识别帧率"),
        ]
        for key, label_text in info_items:
            row = QHBoxLayout()
            lbl = QLabel(f"  • {label_text}:")
            lbl.setStyleSheet("font-size: 13px; color: #a6adc8; border: none;")
            val = QLabel("--")
            val.setStyleSheet("font-size: 13px; color: #cdd6f4; font-weight: bold; border: none;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            layout.addLayout(row)
            self._hand_info_labels[key] = val

        layout.addSpacing(10)

        # 绑定动作
        action_title = QLabel("⚡ 绑定动作")
        action_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(action_title)

        self._action_label = QLabel("无绑定动作")
        self._action_label.setStyleSheet("font-size: 14px; color: #a6e3a1; border: none;")
        self._action_label.setWordWrap(True)
        layout.addWidget(self._action_label)

        layout.addStretch()

    def update_gesture(self, gesture_name: str, emoji: str, confidence: float):
        """更新当前识别的手势。"""
        self._gesture_label.setText(f"{emoji} {gesture_name}")
        self._confidence_bar.set_confidence(confidence)

    def update_hand_info(self, handedness: str, fingers: int, landmark_count: int, fps: float):
        """更新手部信息。"""
        self._hand_info_labels["hand"].setText(handedness)
        self._hand_info_labels["fingers"].setText(f"{fingers}/5")
        self._hand_info_labels["landmarks"].setText(str(landmark_count))
        self._hand_info_labels["fps"].setText(f"{fps:.1f}")

    def update_action(self, action_text: str):
        """更新绑定动作显示。"""
        self._action_label.setText(action_text if action_text else "无绑定动作")

    def reset(self):
        """重置所有显示。"""
        self._gesture_label.setText("等待识别...")
        self._confidence_bar.set_confidence(0)
        for lbl in self._hand_info_labels.values():
            lbl.setText("--")
        self._action_label.setText("无绑定动作")


# ---------------------------------------------------------------------------
# 手势历史表格
# ---------------------------------------------------------------------------

class GestureHistoryTable(QTableWidget):
    """手势识别历史记录表格，最多保存 50 条，自动滚动。"""

    MAX_ROWS = 50

    HEADERS = ["时间", "手势", "置信度", "动作"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
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
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        self._paused = False

    def add_entry(self, timestamp: str, gesture: str, confidence: float, action: str):
        """添加一条历史记录。"""
        if self._paused:
            return

        # 超过上限时删除最旧的行
        if self.rowCount() >= self.MAX_ROWS:
            self.removeRow(0)

        row = self.rowCount()
        self.insertRow(row)

        # 时间
        time_item = QTableWidgetItem(timestamp)
        self.setItem(row, 0, time_item)

        # 手势
        gesture_item = QTableWidgetItem(gesture)
        self.setItem(row, 1, gesture_item)

        # 置信度（带颜色）
        conf_pct = f"{confidence * 100:.1f}%"
        conf_item = QTableWidgetItem(conf_pct)
        if confidence >= 0.8:
            conf_item.setForeground(QColor("#a6e3a1"))
        elif confidence >= 0.5:
            conf_item.setForeground(QColor("#f9e2af"))
        else:
            conf_item.setForeground(QColor("#f38ba8"))
        self.setItem(row, 2, conf_item)

        # 动作
        action_item = QTableWidgetItem(action)
        self.setItem(row, 3, action_item)

        # 自动滚动到底部
        self.scrollToBottom()

    def clear_history(self):
        """清空所有历史记录。"""
        self.setRowCount(0)

    def set_paused(self, paused: bool):
        """设置暂停状态。"""
        self._paused = paused


# ---------------------------------------------------------------------------
# 快速测试按钮面板
# ---------------------------------------------------------------------------

class QuickTestPanel(QFrame):
    """快速测试按钮面板，支持模拟手势触发。"""

    # 信号：(gesture_key, gesture_name)
    test_gesture_triggered = pyqtSignal(str, str)
    clear_history_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)

    # 手势定义：(key, emoji, name)
    GESTURES = [
        ("fist", "✊", "握拳"),
        ("open_palm", "🖐", "张开手掌"),
        ("thumbs_up", "👍", "竖大拇指"),
        ("peace", "✌", "比耶"),
        ("wave", "👋", "挥手"),
        ("circle", "⭕", "画圈"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self._paused = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("🧪 快速测试")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(title)

        # 手势测试按钮网格
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, emoji, name) in enumerate(self.GESTURES):
            btn = QPushButton(f"{emoji}\n{name}")
            btn.setMinimumSize(80, 60)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 8px;
                    font-size: 13px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #45475a;
                    border-color: #89b4fa;
                }
                QPushButton:pressed {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                }
            """)
            btn.clicked.connect(lambda checked, k=key, n=name: self.test_gesture_triggered.emit(k, n))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)

        layout.addSpacing(8)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self._clear_btn = QPushButton("🧹 清除历史")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
        """)
        self._clear_btn.clicked.connect(self.clear_history_requested.emit)
        btn_layout.addWidget(self._clear_btn)

        self._pause_btn = QPushButton("⏸ 暂停识别")
        self._pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #f9e2af;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #f5c2e7; }
        """)
        self._pause_btn.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self._pause_btn)

        layout.addLayout(btn_layout)

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.setText("▶ 恢复识别")
            self._pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a6e3a1;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #94e2d5; }
            """)
        else:
            self._pause_btn.setText("⏸ 暂停识别")
            self._pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f9e2af;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #f5c2e7; }
            """)
        self.pause_toggled.emit(self._paused)


# ---------------------------------------------------------------------------
# 手势测试主页面
# ---------------------------------------------------------------------------

class GestureTestPage(QWidget):
    """
    手势测试/调试主页面。
    整合摄像头预览、识别结果、历史记录和快速测试面板。
    """

    # 对外信号
    test_gesture_triggered = pyqtSignal(str, str)   # (gesture_key, gesture_name)
    clear_history_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)

    # 手势 key -> (中文名, emoji) 映射
    GESTURE_INFO: Dict[str, tuple] = {
        "fist": ("握拳", "✊"),
        "open_palm": ("张开手掌", "🖐"),
        "thumbs_up": ("竖大拇指", "👍"),
        "thumbs_down": ("大拇指朝下", "👎"),
        "peace": ("比耶", "✌"),
        "ok": ("OK手势", "👌"),
        "pointing_up": ("食指朝上", "☝"),
        "three_fingers": ("三指", "🤟"),
        "rock": ("摇滚手势", "🤘"),
        "pinch": ("捏合", "🤏"),
        "pointing_left": ("指向左", "👈"),
        "pointing_right": ("指向右", "👉"),
        "wave": ("挥手", "👋"),
        "circle": ("画圈", "⭕"),
        "swipe_left": ("左滑", "⬅"),
        "swipe_right": ("右滑", "➡"),
        "swipe_up": ("上滑", "⬆"),
        "swipe_down": ("下滑", "⬇"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_paused = False
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 左侧：摄像头 + 快速测试
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # 摄像头预览
        self._camera_preview = CameraPreview()
        left_splitter.addWidget(self._camera_preview)

        # 快速测试面板
        self._quick_test = QuickTestPanel()
        left_splitter.addWidget(self._quick_test)

        left_splitter.setSizes([400, 200])
        left_splitter.setStretchFactor(0, 3)
        left_splitter.setStretchFactor(1, 1)

        # 右侧：识别结果 + 历史记录
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # 识别结果面板
        self._result_panel = RecognitionResultPanel()
        right_splitter.addWidget(self._result_panel)

        # 历史记录
        history_container = QFrame()
        history_container.setFrameShape(QFrame.Shape.StyledPanel)
        history_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)
        history_layout = QVBoxLayout(history_container)
        history_title = QLabel("📜 识别历史")
        history_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4; border: none; padding: 6px;")
        history_layout.addWidget(history_title)
        self._history_table = GestureHistoryTable()
        history_layout.addWidget(self._history_table)
        right_splitter.addWidget(history_container)

        right_splitter.setSizes([300, 300])
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)

        # 主布局
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([500, 500])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(main_splitter)

    def _connect_signals(self):
        """连接内部信号到对外信号。"""
        self._quick_test.test_gesture_triggered.connect(self.test_gesture_triggered.emit)
        self._quick_test.clear_history_requested.connect(self.clear_history_requested.emit)
        self._quick_test.pause_toggled.connect(self.pause_toggled.emit)
        self._quick_test.pause_toggled.connect(self._on_pause_toggled)

    def _on_pause_toggled(self, paused: bool):
        self._is_paused = paused
        self._history_table.set_paused(paused)

    # ------------------------------------------------------------------
    # 公共 API - 供外部识别引擎调用
    # ------------------------------------------------------------------

    def update_camera_frame(self, cv_image):
        """更新摄像头预览画面。"""
        self._camera_preview.update_frame(cv_image)

    def update_recognition(
        self,
        gesture_key: str,
        confidence: float,
        handedness: str = "--",
        fingers: int = 0,
        landmark_count: int = 0,
        fps: float = 0.0,
        bound_action: str = "",
    ):
        """
        更新识别结果。
        Parameters:
            gesture_key: 手势标识 (如 "fist", "thumbs_up")
            confidence: 置信度 0.0~1.0
            handedness: 手性 "Left"/"Right"
            fingers: 伸展手指数
            landmark_count: 关键点数量
            fps: 识别帧率
            bound_action: 绑定的动作描述
        """
        if self._is_paused:
            return

        info = self.GESTURE_INFO.get(gesture_key, ("未知", "❓"))
        name, emoji = info

        # 更新识别结果面板
        self._result_panel.update_gesture(name, emoji, confidence)
        self._result_panel.update_hand_info(handedness, fingers, landmark_count, fps)
        self._result_panel.update_action(bound_action)

        # 添加历史记录
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._history_table.add_entry(
            timestamp,
            f"{emoji} {name}",
            confidence,
            bound_action or "无",
        )

    def add_test_history(self, gesture_key: str, action: str = "测试"):
        """快速测试按钮触发时添加历史记录。"""
        info = self.GESTURE_INFO.get(gesture_key, ("未知", "❓"))
        name, emoji = info
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._history_table.add_entry(timestamp, f"{emoji} {name}", 1.0, action)

        # 同时更新识别结果面板
        self._result_panel.update_gesture(name, emoji, 1.0)

    def reset(self):
        """重置页面所有状态。"""
        self._result_panel.reset()
        self._history_table.clear_history()
        self._camera_preview.set_placeholder("📷\n摄像头预览\n等待启动...")

    def get_paused_state(self) -> bool:
        """获取当前暂停状态。"""
        return self._is_paused


# ---------------------------------------------------------------------------
# 独立运行演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import random
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e2e;
            color: #cdd6f4;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }
    """)

    page = GestureTestPage()
    page.resize(1000, 700)
    page.setWindowTitle("GestureMaster - 手势测试")
    page.show()

    # 演示：每 2 秒模拟一次手势识别
    demo_gestures = ["fist", "thumbs_up", "peace", "open_palm", "wave", "ok"]
    demo_actions = {
        "fist": "锁屏",
        "thumbs_up": "打开B站",
        "peace": "静音",
        "open_palm": "暂停播放",
        "wave": "下一曲",
        "ok": "打开浏览器",
    }

    demo_timer = QTimer()
    demo_idx = [0]

    def simulate_gesture():
        gesture = demo_gestures[demo_idx[0] % len(demo_gestures)]
        confidence = random.uniform(0.75, 0.99)
        page.update_recognition(
            gesture_key=gesture,
            confidence=confidence,
            handedness=random.choice(["Left", "Right"]),
            fingers=random.randint(0, 5),
            landmark_count=21,
            fps=30.0,
            bound_action=demo_actions.get(gesture, ""),
        )
        demo_idx[0] += 1

    demo_timer.timeout.connect(simulate_gesture)
    demo_timer.start(2000)

    sys.exit(app.exec())
