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

        # Emoji
        emoji_label = QLabel(self.gesture["emoji"])
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_label.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        layout.addWidget(emoji_label)

        # 名称
        name_label = QLabel(self.gesture["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {'#cdd6f4' if self._enabled else '#6c7086'}; background: transparent; border: none;")
        layout.addWidget(name_label)

        # 描述
        desc_label = QLabel(self.gesture.get("desc", ""))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 10px; color: #a6adc8; background: transparent; border: none;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 启用开关
        self._checkbox = QCheckBox()
        self._checkbox.setChecked(self._enabled)
        self._checkbox.setStyleSheet("""
            QCheckBox { background: transparent; border: none; }
        """)
        self._checkbox.stateChanged.connect(self._on_toggled)
        cb_layout = QHBoxLayout()
        cb_layout.addStretch()
        cb_layout.addWidget(self._checkbox)
        cb_layout.addStretch()
        layout.addLayout(cb_layout)

    def _on_toggled(self, state):
        self._enabled = bool(state)
        self._update_style()
        self.toggled.emit(self.gesture["key"], self._enabled)

    def _update_style(self):
        if self._enabled:
            self.setStyleSheet("""
                GestureCard {
                    background-color: #313244;
                    border: 2px solid #89b4fa;
                    border-radius: 10px;
                }
                GestureCard:hover {
                    border-color: #cba6f7;
                    background-color: #45475a;
                }
            """)
        else:
            self.setStyleSheet("""
                GestureCard {
                    background-color: #181825;
                    border: 2px solid #313244;
                    border-radius: 10px;
                }
                GestureCard:hover {
                    border-color: #45475a;
                }
            """)

    def is_enabled(self) -> bool:
        return self._enabled


# ---------------------------------------------------------------------------
# 手势详情对话框
# ---------------------------------------------------------------------------

class GestureDetailDialog(QDialog):
    """手势详情对话框，显示识别要点。"""

    def __init__(self, gesture: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"手势详情 - {gesture['emoji']} {gesture['name']}")
        self.setMinimumSize(350, 250)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; background: transparent; border: none; }
        """)

        layout = QVBoxLayout(self)

        # Emoji 大图
        emoji_label = QLabel(gesture["emoji"])
        emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_label.setStyleSheet("font-size: 64px;")
        layout.addWidget(emoji_label)

        # 名称
        name_label = QLabel(gesture["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(name_label)

        # 描述
        desc_label = QLabel(gesture.get("desc", ""))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 14px; color: #a6adc8;")
        layout.addWidget(desc_label)

        # 识别提示
        tips_group = QGroupBox("识别要点")
        tips_group.setStyleSheet(
            "QGroupBox { color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        tips_layout = QVBoxLayout(tips_group)
        tips_label = QLabel(f"• 保持手势稳定，置信度会更高\n• 确保手部在摄像头画面中央\n• 光线充足有助于识别精度\n• 距离摄像头约 30-50cm 最佳")
        tips_label.setStyleSheet("font-size: 12px; color: #a6adc8;")
        tips_layout.addWidget(tips_label)
        layout.addWidget(tips_group)

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)


# ---------------------------------------------------------------------------
# 序列编辑器对话框
# ---------------------------------------------------------------------------

class SequenceEditorDialog(QDialog):
    """手势序列编辑器对话框。"""

    def __init__(self, parent=None, sequence: dict = None):
        super().__init__(parent)
        self.setWindowTitle("编辑手势序列" if sequence else "新建手势序列")
        self.setMinimumSize(400, 350)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; background: transparent; border: none; }
            QLineEdit, QSpinBox { background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QPushButton { background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background: #45475a; }
        """)
        self._sequence = sequence or {}
        self._gesture_keys: List[str] = sequence.get("gestures", []) if sequence else []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 序列名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("序列名称:"))
        self._name_input = QLineEdit(self._sequence.get("name", ""))
        self._name_input.setPlaceholderText("例如: 锁屏序列")
        name_layout.addWidget(self._name_input)
        layout.addLayout(name_layout)

        # 超时设置
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("超时时间:"))
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 10)
        self._timeout_spin.setValue(int(self._sequence.get("timeout", 2)))
        self._timeout_spin.setSuffix(" 秒")
        timeout_layout.addWidget(self._timeout_spin)
        layout.addLayout(timeout_layout)

        # 手势序列
        layout.addWidget(QLabel("手势序列（按顺序选择）:"))

        self._sequence_list = QVBoxLayout()
        self._gesture_widgets: List[QComboBox] = []
        layout.addLayout(self._sequence_list)

        # 添加/删除手势按钮
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ 添加手势")
        btn_add.clicked.connect(self._add_gesture_selector)
        btn_layout.addWidget(btn_add)

        btn_remove = QPushButton("－ 删除最后一个")
        btn_remove.clicked.connect(self._remove_last_gesture)
        btn_layout.addWidget(btn_remove)
        layout.addLayout(btn_layout)

        # 预览
        self._preview_label = QLabel("")
        self._preview_label.setStyleSheet("font-size: 14px; color: #89b4fa;")
        layout.addWidget(self._preview_label)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 恢复已有序列
        if self._gesture_keys:
            for key in self._gesture_keys:
                self._add_gesture_selector(key)
        else:
            self._add_gesture_selector()
            self._add_gesture_selector()

        self._update_preview()

    def _add_gesture_selector(self, selected_key: str = ""):
        """添加一个手势选择下拉框。"""
        combo = QComboBox()
        all_gestures = STATIC_GESTURES + DYNAMIC_GESTURES
        for g in all_gestures:
            combo.addItem(f"{g['emoji']} {g['name']}", g["key"])
        if selected_key:
            idx = next((i for i, g in enumerate(all_gestures) if g["key"] == selected_key), 0)
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda: self._update_preview())
        self._gesture_widgets.append(combo)
        self._sequence_list.addWidget(combo)

    def _remove_last_gesture(self):
        if self._gesture_widgets:
            widget = self._gesture_widgets.pop()
            self._sequence_list.removeWidget(widget)
            widget.deleteLater()
            self._update_preview()

    def _update_preview(self):
        gestures = []
        all_gestures = STATIC_GESTURES + DYNAMIC_GESTURES
        for combo in self._gesture_widgets:
            key = combo.currentData()
            g = next((x for x in all_gestures if x["key"] == key), None)
            if g:
                gestures.append(g["emoji"])
        self._preview_label.setText(" → ".join(gestures) if gestures else "")

    def _on_accept(self):
        if len(self._gesture_widgets) < 2:
            QMessageBox.warning(self, "提示", "至少需要 2 个手势组成序列。")
            return
        self.accept()

    def get_data(self) -> dict:
        """返回序列数据。"""
        gestures = [combo.currentData() for combo in self._gesture_widgets]
        return {
            "name": self._name_input.text() or "未命名序列",
            "gestures": gestures,
            "timeout": self._timeout_spin.value(),
        }


# ---------------------------------------------------------------------------
# 手势设置主页面
# ---------------------------------------------------------------------------

class GestureSettingsPage(QWidget):
    """
    手势设置页面。
    展示所有手势卡片，支持启用/禁用、灵敏度调整和序列管理。
    """

    gesture_toggled = pyqtSignal(str, bool)       # (gesture_key, enabled)
    sensitivity_changed = pyqtSignal(str, float)   # (gesture_key, sensitivity)
    sequence_added = pyqtSignal(dict)
    sequence_removed = pyqtSignal(str)
    sequence_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gesture_states: Dict[str, bool] = {}
        self._sequences: List[dict] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 标题 + 搜索
        header = QHBoxLayout()
        title = QLabel("✋ 手势管理")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #cdd6f4;")
        header.addWidget(title)
        header.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 搜索手势...")
        self._search_input.setFixedWidth(200)
        self._search_input.setStyleSheet(
            "background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; padding: 6px 12px;"
        )
        self._search_input.textChanged.connect(self._filter_gestures)
        header.addWidget(self._search_input)
        main_layout.addLayout(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)

        # 静态手势区
        self._static_section = self._create_section("静态手势", STATIC_GESTURES)
        scroll_layout.addWidget(self._static_section)

        # 动态手势区
        self._dynamic_section = self._create_section("动态手势", DYNAMIC_GESTURES, is_dynamic=True)
        scroll_layout.addWidget(self._dynamic_section)

        # 手势序列区
        self._sequence_section = self._create_sequence_section()
        scroll_layout.addWidget(self._sequence_section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, 1)

    def _create_section(self, title: str, gestures: list, is_dynamic: bool = False) -> QFrame:
        """创建一个手势分区。"""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(section)

        # 标题
        label = QLabel(title)
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4; border: none;")
        layout.addWidget(label)

        # 卡片网格
        grid = QGridLayout()
        grid.setSpacing(10)
        cards = []
        for i, gesture in enumerate(gestures):
            enabled = self._gesture_states.get(gesture["key"], True)
            card = GestureCard(gesture, enabled)
            card.toggled.connect(self.gesture_toggled.emit)
            card.mousePressEvent = lambda e, g=gesture: self._show_detail(g)
            cards.append(card)
            grid.addWidget(card, i // 5, i % 5)

        layout.addLayout(grid)

        # 动态手势灵敏度
        if is_dynamic:
            sens_layout = QHBoxLayout()
            sens_label = QLabel("灵敏度:")
            sens_label.setStyleSheet("color: #a6adc8; font-size: 12px; border: none;")
            sens_layout.addWidget(sens_label)

            sens_slider = QSlider(Qt.Orientation.Horizontal)
            sens_slider.setRange(1, 10)
            sens_slider.setValue(5)
            sens_slider.setFixedWidth(200)
            sens_layout.addWidget(sens_slider)

            sens_value = QLabel("中等")
            sens_value.setStyleSheet("color: #cdd6f4; font-size: 12px; border: none;")
            sens_slider.valueChanged.connect(
                lambda v: sens_value.setText(["极低", "很低", "低", "较低", "中等", "较高", "高", "很高", "极高", "最高"][v - 1])
            )
            sens_layout.addWidget(sens_value)
            sens_layout.addStretch()
            layout.addLayout(sens_layout)

        # 存储卡片引用
        section._cards = cards
        return section

    def _create_sequence_section(self) -> QFrame:
        """创建手势序列区域。"""
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(section)

        header = QHBoxLayout()
        label = QLabel("🔗 手势序列")
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4; border: none;")
        header.addWidget(label)
        header.addStretch()

        btn_add = QPushButton("＋ 添加序列")
        btn_add.setStyleSheet(
            "background: #89b4fa; color: #1e1e2e; font-weight: bold; border: none; border-radius: 6px; padding: 6px 16px;"
        )
        btn_add.clicked.connect(self._add_sequence)
        header.addWidget(btn_add)
        layout.addLayout(header)

        self._sequence_list_layout = QVBoxLayout()
        layout.addLayout(self._sequence_list_layout)

        section._sequence_widgets = []
        self._sequence_section = section
        return section

    def _show_detail(self, gesture: dict):
        """显示手势详情对话框。"""
        dialog = GestureDetailDialog(gesture, self)
        dialog.exec()

    def _add_sequence(self):
        """添加新手势序列。"""
        dialog = SequenceEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            data["id"] = f"seq_{len(self._sequences)}"
            self._sequences.append(data)
            self._refresh_sequence_list()
            self.sequence_added.emit(data)

    def _edit_sequence(self, index: int):
        """编辑手势序列。"""
        if 0 <= index < len(self._sequences):
            dialog = SequenceEditorDialog(self, self._sequences[index])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                data["id"] = self._sequences[index]["id"]
                self._sequences[index] = data
                self._refresh_sequence_list()
                self.sequence_updated.emit(data)

    def _delete_sequence(self, index: int):
        """删除手势序列。"""
        if 0 <= index < len(self._sequences):
            seq_id = self._sequences[index]["id"]
            self._sequences.pop(index)
            self._refresh_sequence_list()
            self.sequence_removed.emit(seq_id)

    def _refresh_sequence_list(self):
        """刷新序列列表显示。"""
        # 清除旧的
        layout = self._sequence_section._sequence_list_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_gestures = STATIC_GESTURES + DYNAMIC_GESTURES
        for i, seq in enumerate(self._sequences):
            row = QFrame()
            row.setStyleSheet("QFrame { background: #313244; border-radius: 6px; border: none; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)

            # 序列描述
            gesture_emojis = []
            for key in seq.get("gestures", []):
                g = next((x for x in all_gestures if x["key"] == key), None)
                gesture_emojis.append(g["emoji"] if g else "?")
            seq_text = f"{seq.get('name', '未命名')}: {' → '.join(gesture_emojis)} (超时: {seq.get('timeout', 2)}s)"
            text_label = QLabel(seq_text)
            text_label.setStyleSheet("color: #cdd6f4; font-size: 13px; border: none;")
            row_layout.addWidget(text_label, 1)

            # 编辑按钮
            btn_edit = QPushButton("编辑")
            btn_edit.setFixedSize(50, 28)
            btn_edit.setStyleSheet("background: #89b4fa; color: #1e1e2e; border: none; border-radius: 4px; font-size: 11px;")
            btn_edit.clicked.connect(lambda _, idx=i: self._edit_sequence(idx))
            row_layout.addWidget(btn_edit)

            # 删除按钮
            btn_del = QPushButton("删除")
            btn_del.setFixedSize(50, 28)
            btn_del.setStyleSheet("background: #f38ba8; color: #1e1e2e; border: none; border-radius: 4px; font-size: 11px;")
            btn_del.clicked.connect(lambda _, idx=i: self._delete_sequence(idx))
            row_layout.addWidget(btn_del)

            layout.addWidget(row)

    def _filter_gestures(self, text: str):
        """根据搜索文本过滤手势卡片。"""
        text = text.lower()
        for section in [self._static_section, self._dynamic_section]:
            if hasattr(section, '_cards'):
                for card in section._cards:
                    match = (
                        text in card.gesture["name"].lower()
                        or text in card.gesture["key"].lower()
                        or text in card.gesture["emoji"]
                    )
                    card.setVisible(match)

    def get_gesture_states(self) -> Dict[str, bool]:
        """获取所有手势的启用状态。"""
        return self._gesture_states.copy()

    def set_gesture_states(self, states: Dict[str, bool]):
        """设置手势启用状态。"""
        self._gesture_states = states

    def get_sequences(self) -> List[dict]:
        """获取所有手势序列。"""
        return self._sequences.copy()

    def set_sequences(self, sequences: List[dict]):
        """设置手势序列。"""
        self._sequences = sequences
        self._refresh_sequence_list()
