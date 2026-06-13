"""
手势设置页面
提供手势的查看、启用/禁用、灵敏度调整和手势序列编辑功能。
"""

from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QSlider, QCheckBox, QGroupBox,
    QSplitter, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QSpinBox, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


# ---------------------------------------------------------------------------
# 手势定义数据
# ---------------------------------------------------------------------------

STATIC_GESTURES = [
    {"key": "fist", "name": "握拳", "emoji": "✊", "desc": "所有手指弯曲握紧"},
    {"key": "open_palm", "name": "张开手掌", "emoji": "🖐", "desc": "所有手指伸展张开"},
    {"key": "thumbs_up", "name": "竖大拇指", "emoji": "👍", "desc": "仅拇指伸展朝上"},
    {"key": "thumbs_down", "name": "大拇指朝下", "emoji": "👎", "desc": "仅拇指伸展朝下"},
    {"key": "peace", "name": "比耶", "emoji": "✌", "desc": "食指和中指伸展"},
    {"key": "ok", "name": "OK手势", "emoji": "👌", "desc": "拇指和食指形成圆圈"},
    {"key": "pointing_up", "name": "食指朝上", "emoji": "☝", "desc": "仅食指伸展朝上"},
    {"key": "three_fingers", "name": "三指", "emoji": "🤟", "desc": "拇指+食指+中指伸展"},
    {"key": "rock", "name": "摇滚手势", "emoji": "🤘", "desc": "食指和小指伸展"},
    {"key": "pinch", "name": "捏合", "emoji": "🤏", "desc": "拇指和食指捏在一起"},
    {"key": "pointing_left", "name": "指向左", "emoji": "👈", "desc": "食指指向左侧"},
    {"key": "pointing_right", "name": "指向右", "emoji": "👉", "desc": "食指指向右侧"},
]

DYNAMIC_GESTURES = [
    {"key": "wave", "name": "挥手", "emoji": "👋", "desc": "手掌左右摆动"},
    {"key": "circle", "name": "画圈", "emoji": "⭕", "desc": "手掌画圆圈"},
    {"key": "swipe_left", "name": "左滑", "emoji": "⬅", "desc": "快速向左滑动"},
    {"key": "swipe_right", "name": "右滑", "emoji": "➡", "desc": "快速向右滑动"},
    {"key": "swipe_up", "name": "上滑", "emoji": "⬆", "desc": "快速向上滑动"},
    {"key": "swipe_down", "name": "下滑", "emoji": "⬇", "desc": "快速向下滑动"},
]


# ---------------------------------------------------------------------------
# 手势卡片组件
# ---------------------------------------------------------------------------

class GestureCard(QFrame):
    """单个手势的卡片展示组件。"""
    toggled = pyqtSignal(str, bool)  # (gesture_key, enabled)

    def __init__(self, gesture: dict, enabled: bool = True, parent=None):
        super().__init__(parent)
        self.gesture = gesture
        self._enabled = enabled
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(140, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        emoji = QLabel(self.gesture.get("emoji", ""))
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        layout.addWidget(emoji)

        name = QLabel(self.gesture.get("name", ""))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-size: 12px; font-weight: bold; color: #cdd6f4; background: transparent; border: none;")
        layout.addWidget(name)

        desc = QLabel(self.gesture.get("desc", ""))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 10px; color: #6c7086; background: transparent; border: none;")
        layout.addWidget(desc)

        self._check = QCheckBox()
        self._check.setChecked(self._enabled)
        self._check.setText("启用")
        self._check.setStyleSheet("font-size: 11px; color: #a6adc8; background: transparent; border: none;")
        self._check.stateChanged.connect(self._on_toggled)
        layout.addWidget(self._check, alignment=Qt.AlignmentFlag.AlignCenter)

    def _update_style(self):
        if self._enabled:
            self.setStyleSheet("""
                QFrame {
                    background-color: #181825;
                    border: 1px solid #313244;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border: 1px solid #89b4fa;
                    background-color: #1e1e2e;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #11111b;
                    border: 1px solid #313244;
                    border-radius: 10px;
                }
            """)

    def _on_toggled(self, state):
        self._enabled = bool(state)
        self._update_style()
        self.toggled.emit(self.gesture["key"], self._enabled)

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._check.setChecked(enabled)
        self._update_style()


# ---------------------------------------------------------------------------
# 序列编辑器对话框
# ---------------------------------------------------------------------------

class SequenceEditorDialog(QDialog):
    """手势序列编辑器。"""
    sequence_saved = pyqtSignal(dict)

    def __init__(self, sequence: dict = None, parent=None):
        super().__init__(parent)
        self._sequence = sequence or {}
        self._gestures = self._sequence.get("gestures", [])
        self.setWindowTitle("编辑手势序列")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("序列名称:"))
        self._name_edit = QLineEdit()
        self._name_edit.setText(self._sequence.get("name", ""))
        name_row.addWidget(self._name_edit)
        layout.addLayout(name_row)

        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("超时(秒):"))
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 10)
        self._timeout_spin.setValue(int(self._sequence.get("timeout", 2.0)))
        timeout_row.addWidget(self._timeout_spin)
        layout.addLayout(timeout_row)

        layout.addWidget(QLabel("手势序列:"))
        self._gesture_list = QVBoxLayout()
        layout.addLayout(self._gesture_list)

        for g in self._gestures:
            self._add_gesture_row(g)

        add_btn = QPushButton("+ 添加手势")
        add_btn.clicked.connect(lambda: self._add_gesture_row(""))
        layout.addWidget(add_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_gesture_row(self, selected: str = ""):
        combo = QComboBox()
        all_gestures = STATIC_GESTURES + DYNAMIC_GESTURES
        for g in all_gestures:
            combo.addItem(f"{g['emoji']} {g['name']}", g["key"])
        if selected:
            for i in range(combo.count()):
                if combo.itemData(i) == selected:
                    combo.setCurrentIndex(i)
                    break
        row = QHBoxLayout()
        row.addWidget(combo)
        del_btn = QPushButton("×")
        del_btn.setFixedSize(30, 30)
        del_btn.clicked.connect(lambda: self._remove_gesture_row(row, combo))
        row.addWidget(del_btn)
        self._gesture_list.addLayout(row)

    def _remove_gesture_row(self, row, combo):
        for i in range(row.count()):
            w = row.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._gesture_list.removeItem(row)

    def _save(self):
        gestures = []
        for i in range(self._gesture_list.count()):
            row = self._gesture_list.itemAt(i)
            if row:
                for j in range(row.count()):
                    w = row.itemAt(j).widget()
                    if isinstance(w, QComboBox):
                        gestures.append(w.currentData())
        result = {
            "name": self._name_edit.text(),
            "timeout": self._timeout_spin.value(),
            "gestures": gestures,
        }
        self.sequence_saved.emit(result)
        self.accept()


# ---------------------------------------------------------------------------
# 手势设置主页面
# ---------------------------------------------------------------------------

class GestureSettingsPage(QWidget):
    """手势设置页面。"""
    gesture_toggled = pyqtSignal(str, bool)
    settings_changed = pyqtSignal(dict)

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._gesture_cards: Dict[str, GestureCard] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 静态手势
        static_group = QGroupBox("静态手势")
        static_group.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-weight: bold; border: 1px solid #45475a; border-radius: 8px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        static_grid = QGridLayout(static_group)
        for i, g in enumerate(STATIC_GESTURES):
            card = GestureCard(g)
            card.toggled.connect(self.gesture_toggled.emit)
            self._gesture_cards[g["key"]] = card
            static_grid.addWidget(card, i // 4, i % 4)
        layout.addWidget(static_group)

        # 动态手势
        dynamic_group = QGroupBox("动态手势")
        dynamic_group.setStyleSheet(static_group.styleSheet())
        dynamic_grid = QGridLayout(dynamic_group)
        for i, g in enumerate(DYNAMIC_GESTURES):
            card = GestureCard(g)
            card.toggled.connect(self.gesture_toggled.emit)
            self._gesture_cards[g["key"]] = card
            dynamic_grid.addWidget(card, i // 4, i % 4)
        layout.addWidget(dynamic_group)

        # 灵敏度设置
        sens_group = QGroupBox("灵敏度设置")
        sens_group.setStyleSheet(static_group.styleSheet())
        sens_layout = QVBoxLayout(sens_group)

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("检测置信度:"))
        self._conf_slider = QSlider(Qt.Orientation.Horizontal)
        self._conf_slider.setRange(30, 95)
        self._conf_slider.setValue(70)
        conf_row.addWidget(self._conf_slider)
        self._conf_label = QLabel("0.70")
        self._conf_slider.valueChanged.connect(lambda v: self._conf_label.setText(f"{v/100:.2f}"))
        conf_row.addWidget(self._conf_label)
        sens_layout.addLayout(conf_row)

        cool_row = QHBoxLayout()
        cool_row.addWidget(QLabel("动作冷却(秒):"))
        self._cool_slider = QSlider(Qt.Orientation.Horizontal)
        self._cool_slider.setRange(5, 50)
        self._cool_slider.setValue(15)
        cool_row.addWidget(self._cool_slider)
        self._cool_label = QLabel("1.5")
        self._cool_slider.valueChanged.connect(lambda v: self._cool_label.setText(f"{v/10:.1f}"))
        cool_row.addWidget(self._cool_label)
        sens_layout.addLayout(cool_row)

        layout.addWidget(sens_group)

        # 手势序列
        seq_group = QGroupBox("手势序列")
        seq_group.setStyleSheet(static_group.styleSheet())
        seq_layout = QVBoxLayout(seq_group)

        self._seq_list = QVBoxLayout()
        seq_layout.addLayout(self._seq_list)

        add_seq_btn = QPushButton("+ 添加序列")
        add_seq_btn.clicked.connect(self._add_sequence)
        seq_layout.addWidget(add_seq_btn)

        layout.addWidget(seq_group)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _add_sequence(self):
        dialog = SequenceEditorDialog(parent=self)
        dialog.sequence_saved.connect(self._on_sequence_saved)
        dialog.exec()

    def _on_sequence_saved(self, seq: dict):
        label = QLabel(f"  {seq.get('name', '未命名')}: {' → '.join(seq.get('gestures', []))}")
        label.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self._seq_list.addWidget(label)

    def get_settings(self) -> dict:
        return {
            "confidence": self._conf_slider.value() / 100,
            "cooldown": self._cool_slider.value() / 10,
        }
