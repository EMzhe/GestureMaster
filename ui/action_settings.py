"""
手势动作绑定设置页面
允许用户将手势映射到系统/媒体/应用/窗口/自定义等动作。
支持多动作组合、参数动态配置、冷却时间调整、拖拽排序等功能。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from PyQt6.QtCore import Qt, QMimeData, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import QDrag, QFont, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSpinBox, QSplitter, QTextEdit, QToolButton,
    QVBoxLayout, QWidget, QInputDialog,
)


# ---------------------------------------------------------------------------
# 动作分类定义
# ---------------------------------------------------------------------------

ACTION_CATEGORIES: list = [
    ("系统", [
        ("lock_screen",   "🔒", "锁屏"),
        ("shutdown",      "⏻",  "关机"),
        ("restart",       "🔄", "重启"),
        ("hibernate",     "💤", "休眠"),
        ("mute",          "🔇", "静音"),
        ("unmute",        "🔊", "取消静音"),
    ]),
    ("媒体", [
        ("play_pause",    "▶",  "播放/暂停"),
        ("next_track",    "⏭",  "下一曲"),
        ("prev_track",    "⏮",  "上一曲"),
        ("volume_up",     "🔊", "音量+"),
        ("volume_down",   "🔉", "音量-"),
    ]),
    ("应用", [
        ("open_url",      "🌐", "打开网址"),
        ("open_app",      "📁", "打开程序"),
        ("open_folder",   "📂", "打开目录"),
    ]),
    ("窗口", [
        ("minimize_window", "📌", "最小化"),
        ("maximize_window", "📌", "最大化"),
        ("close_window",    "❌", "关闭窗口"),
        ("alt_tab",         "🔄", "切换窗口"),
    ]),
    ("自定义", [
        ("send_keys",     "⌨", "快捷键"),
        ("run_command",   "💻", "运行命令"),
        ("run_script",    "📜", "脚本"),
    ]),
]

NO_PARAM_ACTIONS: set = {
    "lock_screen", "shutdown", "restart", "hibernate", "mute", "unmute",
    "play_pause", "next_track", "prev_track",
    "minimize_window", "maximize_window", "close_window", "alt_tab",
}


@dataclass
class ActionItem:
    """单个动作项"""
    action_type: str
    params: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class GestureBinding:
    """手势绑定配置"""
    binding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    gesture_name: str = ""
    gesture_icon: str = ""
    description: str = ""
    actions: list = field(default_factory=list)
    cooldown: float = 1.0
    enabled: bool = True


# ---------------------------------------------------------------------------
# 快捷键录制控件
# ---------------------------------------------------------------------------

class ShortcutRecorder(QLineEdit):
    """点击后进入录制模式，按下键盘快捷键后自动捕获并显示。"""
    shortcut_recorded = pyqtSignal(str)
    _PLACEHOLDER = "点击后按下快捷键..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(self._PLACEHOLDER)
        self.setReadOnly(True)
        self._recording = False

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._recording = True
        self.setText("")
        self.setPlaceholderText("请按下快捷键组合...")
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self._recording:
            super().keyPressEvent(event)
            return
        key = event.key()
        mods = event.modifiers()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
        seq = QKeySequence(mods | key)
        text = seq.toString(QKeySequence.SequenceFormat.PortableText)
        self.setText(text)
        self._recording = False
        self.releaseKeyboard()
        self.setPlaceholderText(self._PLACEHOLDER)
        self.shortcut_recorded.emit(text)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._recording:
            self._recording = False
            self.releaseKeyboard()
            self.setPlaceholderText(self._PLACEHOLDER)


# ---------------------------------------------------------------------------
# 可拖拽排序的动作列表
# ---------------------------------------------------------------------------

class DraggableActionList(QListWidget):
    """支持拖拽排序的动作列表。"""
    action_removed = pyqtSignal(int)
    action_moved = pyqtSignal(int, int)
    action_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setSpacing(2)
        self._items_data: list = []

    def set_actions(self, actions: list):
        """用动作列表刷新显示"""
        self.clear()
        self._items_data = []
        for idx, act in enumerate(actions):
            self._add_action_widget(idx, act)

    def _add_action_widget(self, index: int, action: ActionItem):
        """为单个动作创建自定义 widget"""
        item = QListWidgetItem(self)
        item.setSizeHint(QSize(0, 44))
        item.setData(Qt.ItemDataRole.UserRole, index)

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 2, 6, 2)

        num_label = QLabel(f"{index + 1}.")
        num_label.setFixedWidth(24)
        num_label.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(num_label)

        icon, name = self._action_display(action.action_type)
        type_label = QLabel(f"{icon} {name}")
        type_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(type_label, 1)

        if not action.enabled:
            disabled_tag = QLabel("(禁用)")
            disabled_tag.setStyleSheet("color: #f38ba8; font-size: 11px;")
            layout.addWidget(disabled_tag)

        btn_del = QToolButton()
        btn_del.setText("×")
        btn_del.setToolTip("删除此动作")
        btn_del.setFixedSize(28, 28)
        btn_del.setStyleSheet(
            "QToolButton { color: #f38ba8; font-weight: bold; border: none; }"
            "QToolButton:hover { background: #45475a; border-radius: 4px; }"
        )
        btn_del.clicked.connect(lambda _, i=index: self.action_removed.emit(i))
        layout.addWidget(btn_del)

        btn_up = QToolButton()
        btn_up.setText("↑")
        btn_up.setToolTip("上移")
        btn_up.setFixedSize(28, 28)
        btn_up.clicked.connect(lambda _, i=index: self._emit_move(i, i - 1))
        layout.addWidget(btn_up)

        btn_down = QToolButton()
        btn_down.setText("↓")
        btn_down.setToolTip("下移")
        btn_down.setFixedSize(28, 28)
        btn_down.clicked.connect(lambda _, i=index: self._emit_move(i, i + 1))
        layout.addWidget(btn_down)

        self.setItemWidget(item, widget)

    def _emit_move(self, from_idx: int, to_idx: int):
        if 0 <= to_idx < self.count():
            self.action_moved.emit(from_idx, to_idx)

    @staticmethod
    def _action_display(action_type: str):
        for _cat_name, items in ACTION_CATEGORIES:
            for aid, icon, name in items:
                if aid == action_type:
                    return icon, name
        return "❓", action_type


# ---------------------------------------------------------------------------
# 动作类型选择按钮面板
# ---------------------------------------------------------------------------

class ActionCategoryPanel(QWidget):
    """按分类显示动作类型按钮。"""
    action_type_picked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        group_box = QGroupBox("动作类型选择")
        group_box.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; color: #cdd6f4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        grid = QGridLayout(group_box)
        grid.setSpacing(6)

        for row, (cat_name, items) in enumerate(ACTION_CATEGORIES):
            cat_label = QLabel(f"{cat_name}:")
            cat_label.setStyleSheet("font-weight: bold; color: #a6adc8;")
            grid.addWidget(cat_label, row, 0, Qt.AlignmentFlag.AlignTop)

            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(4)
            for action_id, icon, display_name in items:
                btn = QPushButton(f"{icon} {display_name}")
                btn.setToolTip(action_id)
                btn.setFixedHeight(30)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    "QPushButton { padding: 2px 8px; border: 1px solid #45475a; "
                    "border-radius: 4px; background: #313244; color: #cdd6f4; }"
                    "QPushButton:hover { background: #45475a; border-color: #89b4fa; }"
                )
                btn.clicked.connect(
                    lambda checked, aid=action_id: self.action_type_picked.emit(aid)
                )
                btn_layout.addWidget(btn)
            btn_layout.addStretch()

            btn_container = QWidget()
            btn_container.setLayout(btn_layout)
            grid.addWidget(btn_container, row, 1)

        outer.addWidget(group_box)


# ---------------------------------------------------------------------------
# 动态参数配置面板
# ---------------------------------------------------------------------------

class DynamicParamPanel(QWidget):
    """根据当前选中的动作类型显示不同的参数输入控件。"""
    params_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_action_type: str = ""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._group_box = QGroupBox("参数配置")
        self._group_box.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; color: #cdd6f4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        self._group_layout = QVBoxLayout(self._group_box)
        self._layout.addWidget(self._group_box)

        self._no_param_label = QLabel("此动作无需额外参数")
        self._no_param_label.setStyleSheet("color: #6c7086; font-style: italic;")
        self._group_layout.addWidget(self._no_param_label)

        # open_url 参数
        self._url_widget = QWidget()
        url_layout = QHBoxLayout(self._url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.addWidget(QLabel("URL:"))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://")
        self._url_input.textChanged.connect(self.params_changed.emit)
        url_layout.addWidget(self._url_input, 1)
        self._group_layout.addWidget(self._url_widget)

        # open_app / open_folder / run_script 参数
        self._path_widget = QWidget()
        path_layout = QHBoxLayout(self._path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        self._path_label = QLabel("路径:")
        path_layout.addWidget(self._path_label)
        self._path_input = QLineEdit()
        self._path_input.textChanged.connect(self.params_changed.emit)
        path_layout.addWidget(self._path_input, 1)
        self._btn_browse_path = QPushButton("浏览")
        self._btn_browse_path.setFixedWidth(50)
        self._btn_browse_path.clicked.connect(self._browse_path)
        path_layout.addWidget(self._btn_browse_path)
        self._group_layout.addWidget(self._path_widget)

        # send_keys 参数
        self._keys_widget = QWidget()
        keys_layout = QHBoxLayout(self._keys_widget)
        keys_layout.setContentsMargins(0, 0, 0, 0)
        keys_layout.addWidget(QLabel("快捷键:"))
        self._shortcut_recorder = ShortcutRecorder()
        self._shortcut_recorder.shortcut_recorded.connect(self.params_changed.emit)
        keys_layout.addWidget(self._shortcut_recorder, 1)
        self._group_layout.addWidget(self._keys_widget)

        # run_command 参数
        self._cmd_widget = QWidget()
        cmd_layout = QVBoxLayout(self._cmd_widget)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.addWidget(QLabel("命令:"))
        self._cmd_input = QTextEdit()
        self._cmd_input.setPlaceholderText("输入要执行的命令...")
        self._cmd_input.setMaximumHeight(80)
        self._cmd_input.textChanged.connect(self.params_changed.emit)
        cmd_layout.addWidget(self._cmd_input)
        self._group_layout.addWidget(self._cmd_widget)

        # volume 参数
        self._volume_widget = QWidget()
        vol_layout = QHBoxLayout(self._volume_widget)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.addWidget(QLabel("音量步长:"))
        self._volume_spin = QSpinBox()
        self._volume_spin.setRange(1, 50)
        self._volume_spin.setValue(5)
        self._volume_spin.setSuffix(" %")
        self._volume_spin.valueChanged.connect(self.params_changed.emit)
        vol_layout.addWidget(self._volume_spin)
        vol_layout.addStretch()
        self._group_layout.addWidget(self._volume_widget)

        self._hide_all_param_widgets()

    def set_action_type(self, action_type: str):
        self._current_action_type = action_type
        self._hide_all_param_widgets()
        if action_type in NO_PARAM_ACTIONS and action_type not in ("volume_up", "volume_down"):
            self._no_param_label.show()
            return
        self._no_param_label.hide()
        if action_type == "open_url":
            self._url_widget.show()
        elif action_type in ("open_app", "open_folder", "run_script"):
            self._path_widget.show()
            labels = {"open_app": "程序路径:", "open_folder": "目录路径:", "run_script": "脚本路径:"}
            self._path_label.setText(labels.get(action_type, "路径:"))
        elif action_type == "send_keys":
            self._keys_widget.show()
        elif action_type == "run_command":
            self._cmd_widget.show()
        elif action_type in ("volume_up", "volume_down"):
            self._volume_widget.show()

    def get_params(self) -> dict:
        atype = self._current_action_type
        if atype == "open_url":
            return {"url": self._url_input.text().strip()}
        elif atype in ("open_app", "open_folder", "run_script"):
            return {"path": self._path_input.text().strip()}
        elif atype == "send_keys":
            return {"shortcut": self._shortcut_recorder.text().strip()}
        elif atype == "run_command":
            return {"cmd": self._cmd_input.toPlainText().strip()}
        elif atype in ("volume_up", "volume_down"):
            return {"step": self._volume_spin.value()}
        return {}

    def set_params(self, params: dict):
        if "url" in params:
            self._url_input.setText(params["url"])
        if "path" in params:
            self._path_input.setText(params["path"])
        if "shortcut" in params:
            self._shortcut_recorder.setText(params["shortcut"])
        if "cmd" in params:
            self._cmd_input.setPlainText(params["cmd"])
        if "step" in params:
            self._volume_spin.setValue(int(params["step"]))

    def clear_params(self):
        self._url_input.clear()
        self._path_input.clear()
        self._shortcut_recorder.clear()
        self._cmd_input.clear()
        self._volume_spin.setValue(5)

    def _hide_all_param_widgets(self):
        self._no_param_label.hide()
        self._url_widget.hide()
        self._path_widget.hide()
        self._keys_widget.hide()
        self._cmd_widget.hide()
        self._volume_widget.hide()

    def _browse_path(self):
        atype = self._current_action_type
        if atype in ("open_app", "run_script"):
            path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self._path_input.setText(path)


# ---------------------------------------------------------------------------
# 手势列表条目 Widget
# ---------------------------------------------------------------------------

class GestureListWidgetItem(QWidget):
    """左侧手势列表中的单个条目。"""

    def __init__(self, binding: GestureBinding, parent=None):
        super().__init__(parent)
        self.binding = binding
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        top = QHBoxLayout()
        icon_label = QLabel(binding.gesture_icon or "✋")
        icon_label.setStyleSheet("font-size: 20px;")
        top.addWidget(icon_label)

        name_label = QLabel(binding.gesture_name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        top.addWidget(name_label, 1)

        if not binding.enabled:
            dis_tag = QLabel("(禁用)")
            dis_tag.setStyleSheet("color: #f38ba8; font-size: 11px;")
            top.addWidget(dis_tag)

        layout.addLayout(top)

        desc = self._brief_description(binding)
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        layout.addWidget(desc_label)

    @staticmethod
    def _brief_description(binding: GestureBinding) -> str:
        if not binding.actions:
            return "→ (未绑定)"
        names = []
        for act in binding.actions:
            for _cat, items in ACTION_CATEGORIES:
                for aid, icon, name in items:
                    if aid == act.action_type:
                        names.append(f"{icon} {name}")
                        break
        return "→ " + " + ".join(names) if names else "→ (未绑定)"


# ---------------------------------------------------------------------------
# 主页面：ActionSettingsPage
# ---------------------------------------------------------------------------

class ActionSettingsPage(QWidget):
    """
    手势动作绑定设置页面。
    """
    binding_selected = pyqtSignal(str)
    binding_saved = pyqtSignal(dict)
    binding_deleted = pyqtSignal(str)
    action_test_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bindings: list = []
        self._current_index: int = -1
        self._current_action_index: int = -1
        self._setup_demo_data()
        self._init_ui()
        self._refresh_gesture_list()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        title = QLabel("⚡ 手势绑定")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        root_layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # ---- 左侧面板 ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QLabel("手势列表")
        left_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #cdd6f4;")
        left_layout.addWidget(left_header)

        self._gesture_list_widget = QListWidget()
        self._gesture_list_widget.setSpacing(4)
        self._gesture_list_widget.currentRowChanged.connect(self._on_gesture_selected)
        self._gesture_list_widget.setStyleSheet(
            "QListWidget { border: 1px solid #45475a; border-radius: 6px; background: #1e1e2e; }"
            "QListWidget::item { border-bottom: 1px solid #313244; color: #cdd6f4; }"
            "QListWidget::item:selected { background: #313244; }"
        )
        left_layout.addWidget(self._gesture_list_widget, 1)

        btn_new = QPushButton("＋ 新建绑定")
        btn_new.setFixedHeight(36)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; font-weight: bold; "
            "border: none; border-radius: 6px; font-size: 14px; }"
            "QPushButton:hover { background: #74c7ec; }"
        )
        btn_new.clicked.connect(self._on_new_binding)
        left_layout.addWidget(btn_new)

        splitter.addWidget(left_panel)

        # ---- 右侧面板 ----
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_container = QWidget()
        self._right_layout = QVBoxLayout(right_container)
        self._right_layout.setContentsMargins(8, 0, 0, 0)
        self._right_layout.setSpacing(10)

        self._placeholder_label = QLabel("← 请从左侧选择一个手势绑定进行配置")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet("color: #6c7086; font-size: 14px;")
        self._right_layout.addWidget(self._placeholder_label)

        self._config_widget = QWidget()
        config_layout = QVBoxLayout(self._config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(10)

        # 手势信息区
        info_group = QGroupBox("绑定配置")
        info_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; color: #cdd6f4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("当前手势:"), 0, 0)
        self._gesture_icon_label = QLabel()
        self._gesture_icon_label.setStyleSheet("font-size: 24px;")
        info_layout.addWidget(self._gesture_icon_label, 0, 1)

        self._gesture_name_label = QLabel()
        self._gesture_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4;")
        info_layout.addWidget(self._gesture_name_label, 0, 2)

        info_layout.addWidget(QLabel("描述:"), 1, 0)
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText("输入绑定描述...")
        self._desc_input.setStyleSheet("background: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px;")
        info_layout.addWidget(self._desc_input, 1, 1, 1, 2)

        config_layout.addWidget(info_group)

        # 动作列表区
        action_list_group = QGroupBox("动作列表")
        action_list_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; color: #cdd6f4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        action_list_layout = QVBoxLayout(action_list_group)

        self._action_list = DraggableActionList()
        self._action_list.action_removed.connect(self._on_action_removed)
        self._action_list.action_moved.connect(self._on_action_moved)
        self._action_list.currentRowChanged.connect(self._on_action_item_selected)
        self._action_list.setMaximumHeight(180)
        action_list_layout.addWidget(self._action_list)

        btn_add_action = QPushButton("＋ 添加动作")
        btn_add_action.setFixedHeight(30)
        btn_add_action.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_action.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #1e1e2e; font-weight: bold; "
            "border: none; border-radius: 4px; }"
            "QPushButton:hover { background: #94e2d5; }"
        )
        btn_add_action.clicked.connect(self._on_add_action)
        action_list_layout.addWidget(btn_add_action)

        config_layout.addWidget(action_list_group)

        # 动作类型选择面板
        self._action_category_panel = ActionCategoryPanel()
        self._action_category_panel.action_type_picked.connect(self._on_action_type_picked)
        config_layout.addWidget(self._action_category_panel)

        # 动态参数面板
        self._param_panel = DynamicParamPanel()
        config_layout.addWidget(self._param_panel)

        # 冷却时间
        cooldown_group = QGroupBox("冷却时间")
        cooldown_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #45475a; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; color: #cdd6f4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        cooldown_layout = QHBoxLayout(cooldown_group)
        self._cooldown_slider = QSlider(Qt.Orientation.Horizontal)
        self._cooldown_slider.setRange(5, 50)
        self._cooldown_slider.setValue(10)
        self._cooldown_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._cooldown_slider.setTickInterval(5)
        self._cooldown_slider.valueChanged.connect(self._on_cooldown_changed)
        cooldown_layout.addWidget(self._cooldown_slider, 1)

        self._cooldown_label = QLabel("1.0 秒")
        self._cooldown_label.setFixedWidth(60)
        self._cooldown_label.setStyleSheet("font-size: 13px; color: #cdd6f4;")
        cooldown_layout.addWidget(self._cooldown_label)

        config_layout.addWidget(cooldown_group)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_test = QPushButton("🧪 测试动作")
        self._btn_test.setFixedSize(120, 38)
        self._btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_test.setStyleSheet(
            "QPushButton { background: #f9e2af; color: #1e1e2e; font-weight: bold; "
            "border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #f5c2e7; }"
        )
        self._btn_test.clicked.connect(self._on_test_action)
        btn_row.addWidget(self._btn_test)

        self._btn_save = QPushButton("💾 保存绑定")
        self._btn_save.setFixedSize(120, 38)
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #1e1e2e; font-weight: bold; "
            "border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #94e2d5; }"
        )
        self._btn_save.clicked.connect(self._on_save_binding)
        btn_row.addWidget(self._btn_save)

        self._btn_delete = QPushButton("🗑 删除绑定")
        self._btn_delete.setFixedSize(120, 38)
        self._btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_delete.setStyleSheet(
            "QPushButton { background: #f38ba8; color: #1e1e2e; font-weight: bold; "
            "border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #eba0ac; }"
        )
        self._btn_delete.clicked.connect(self._on_delete_binding)
        btn_row.addWidget(self._btn_delete)

        config_layout.addLayout(btn_row)
        config_layout.addStretch()

        self._config_widget.hide()
        self._right_layout.addWidget(self._config_widget, 1)

        right_scroll.setWidget(right_container)
        splitter.addWidget(right_scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter, 1)

    def _setup_demo_data(self):
        self._bindings = [
            GestureBinding(
                binding_id="demo_001", gesture_name="握拳", gesture_icon="✊",
                description="握拳锁屏", actions=[ActionItem("lock_screen")], cooldown=1.0,
            ),
            GestureBinding(
                binding_id="demo_002", gesture_name="大拇指", gesture_icon="👍",
                description="打开B站", actions=[ActionItem("open_url", {"url": "https://www.bilibili.com"})], cooldown=1.5,
            ),
            GestureBinding(
                binding_id="demo_003", gesture_name="比耶", gesture_icon="✌",
                description="", actions=[], cooldown=1.0,
            ),
            GestureBinding(
                binding_id="demo_004", gesture_name="挥手", gesture_icon="👋",
                description="下一曲", actions=[ActionItem("next_track")], cooldown=0.8,
            ),
            GestureBinding(
                binding_id="demo_005", gesture_name="食指指天", gesture_icon="☝",
                description="音量增大", actions=[ActionItem("volume_up", {"step": 5})], cooldown=0.5,
            ),
        ]

    def _refresh_gesture_list(self):
        self._gesture_list_widget.clear()
        for binding in self._bindings:
            item_widget = GestureListWidgetItem(binding)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint() + QSize(0, 8))
            list_item.setData(Qt.ItemDataRole.UserRole, binding.binding_id)
            self._gesture_list_widget.addItem(list_item)
            self._gesture_list_widget.setItemWidget(list_item, item_widget)
        if self._bindings:
            self._gesture_list_widget.setCurrentRow(0)

    def _update_right_panel(self, index: int):
        self._current_index = index
        if index < 0 or index >= len(self._bindings):
            self._placeholder_label.show()
            self._config_widget.hide()
            return
        self._placeholder_label.hide()
        self._config_widget.show()

        binding = self._bindings[index]
        self._gesture_icon_label.setText(binding.gesture_icon)
        self._gesture_name_label.setText(binding.gesture_name)
        self._desc_input.setText(binding.description)
        self._cooldown_slider.setValue(int(binding.cooldown * 10))
        self._cooldown_label.setText(f"{binding.cooldown:.1f} 秒")
        self._action_list.set_actions(binding.actions)
        self._param_panel.clear_params()
        self._param_panel.set_action_type("")
        self.binding_selected.emit(binding.binding_id)

    def _on_gesture_selected(self, row: int):
        self._update_right_panel(row)

    def _on_action_item_selected(self, row: int):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        if 0 <= row < len(binding.actions):
            self._current_action_index = row
            act = binding.actions[row]
            self._param_panel.set_action_type(act.action_type)
            self._param_panel.set_params(act.params)

    def _on_action_type_picked(self, action_type: str):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        new_action = ActionItem(action_type=action_type)
        binding.actions.append(new_action)
        self._action_list.set_actions(binding.actions)
        new_idx = len(binding.actions) - 1
        self._action_list.setCurrentRow(new_idx)
        self._current_action_index = new_idx
        self._param_panel.set_action_type(action_type)
        self._param_panel.clear_params()

    def _on_add_action(self):
        if self._current_index < 0:
            return
        self._action_category_panel.setFocus()

    def _on_action_removed(self, index: int):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        if 0 <= index < len(binding.actions):
            binding.actions.pop(index)
            self._action_list.set_actions(binding.actions)
            self._param_panel.clear_params()
            self._param_panel.set_action_type("")

    def _on_action_moved(self, from_idx: int, to_idx: int):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        actions = binding.actions
        if 0 <= from_idx < len(actions) and 0 <= to_idx < len(actions):
            actions.insert(to_idx, actions.pop(from_idx))
            self._action_list.set_actions(actions)

    def _on_cooldown_changed(self, value: int):
        seconds = value / 10.0
        self._cooldown_label.setText(f"{seconds:.1f} 秒")
        if self._current_index >= 0:
            self._bindings[self._current_index].cooldown = seconds

    def _on_test_action(self):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        if not binding.actions:
            QMessageBox.information(self, "提示", "当前绑定没有可测试的动作。")
            return
        idx = self._current_action_index
        if idx < 0 or idx >= len(binding.actions):
            idx = 0
        act = binding.actions[idx]
        if act.action_type not in NO_PARAM_ACTIONS or act.action_type in ("volume_up", "volume_down"):
            act.params = self._param_panel.get_params()
        self.action_test_requested.emit(act.action_type, act.params)

    def _on_save_binding(self):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        binding.description = self._desc_input.text().strip()
        if 0 <= self._current_action_index < len(binding.actions):
            act = binding.actions[self._current_action_index]
            if act.action_type not in NO_PARAM_ACTIONS or act.action_type in ("volume_up", "volume_down"):
                act.params = self._param_panel.get_params()

        binding_dict = {
            "binding_id": binding.binding_id,
            "gesture_name": binding.gesture_name,
            "gesture_icon": binding.gesture_icon,
            "description": binding.description,
            "cooldown": binding.cooldown,
            "enabled": binding.enabled,
            "actions": [
                {"action_type": a.action_type, "params": a.params, "enabled": a.enabled}
                for a in binding.actions
            ],
        }
        self.binding_saved.emit(binding_dict)
        self._refresh_gesture_list()
        QMessageBox.information(self, "保存成功", f"绑定「{binding.gesture_name}」已保存。")

    def _on_delete_binding(self):
        if self._current_index < 0:
            return
        binding = self._bindings[self._current_index]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除手势「{binding.gesture_name}」的绑定吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            bid = binding.binding_id
            self._bindings.pop(self._current_index)
            self._current_index = -1
            self._refresh_gesture_list()
            self.binding_deleted.emit(bid)

    def _on_new_binding(self):
        icon, ok1 = QInputDialog.getText(self, "新建绑定", "手势图标 (emoji):", text="✋")
        if not ok1 or not icon.strip():
            return
        name, ok2 = QInputDialog.getText(self, "新建绑定", "手势名称:")
        if not ok2 or not name.strip():
            return
        new_binding = GestureBinding(
            gesture_name=name.strip(), gesture_icon=icon.strip(),
            description="", actions=[], cooldown=1.0,
        )
        self._bindings.append(new_binding)
        self._refresh_gesture_list()
        self._gesture_list_widget.setCurrentRow(len(self._bindings) - 1)

    def load_bindings(self, bindings_data: list):
        self._bindings.clear()
        for bd in bindings_data:
            actions = [
                ActionItem(
                    action_type=a.get("action_type", ""),
                    params=a.get("params", {}),
                    enabled=a.get("enabled", True),
                )
                for a in bd.get("actions", [])
            ]
            self._bindings.append(GestureBinding(
                binding_id=bd.get("binding_id", uuid.uuid4().hex[:8]),
                gesture_name=bd.get("gesture_name", ""),
                gesture_icon=bd.get("gesture_icon", "✋"),
                description=bd.get("description", ""),
                actions=actions,
                cooldown=bd.get("cooldown", 1.0),
                enabled=bd.get("enabled", True),
            ))
        self._refresh_gesture_list()

    def get_all_bindings(self) -> list:
        result = []
        for b in self._bindings:
            result.append({
                "binding_id": b.binding_id,
                "gesture_name": b.gesture_name,
                "gesture_icon": b.gesture_icon,
                "description": b.description,
                "cooldown": b.cooldown,
                "enabled": b.enabled,
                "actions": [
                    {"action_type": a.action_type, "params": a.params, "enabled": a.enabled}
                    for a in b.actions
                ],
            })
        return result
