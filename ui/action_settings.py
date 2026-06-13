"""
动作设置页面
提供动作的分类查看、参数配置和测试功能。
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QGroupBox, QComboBox, QFileDialog,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


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


# ---------------------------------------------------------------------------
# 动作卡片组件
# ---------------------------------------------------------------------------

class ActionCard(QFrame):
    """单个动作的卡片展示组件。"""
    clicked = pyqtSignal(str)  # action_type

    def __init__(self, action_type: str, icon: str, name: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(120, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 1px solid #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 11px; color: #cdd6f4; background: transparent; border: none;")
        layout.addWidget(name_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self.action_type)


# ---------------------------------------------------------------------------
# 动作设置主页面
# ---------------------------------------------------------------------------

class ActionSettingsPage(QWidget):
    """动作设置页面。"""
    action_selected = pyqtSignal(str, dict)  # action_type, params
    action_test = pyqtSignal(str, dict)      # action_type, params

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
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

        for cat_name, actions in ACTION_CATEGORIES:
            group = QGroupBox(cat_name)
            group.setStyleSheet(
                "QGroupBox { color: #cdd6f4; font-weight: bold; border: 1px solid #45475a; border-radius: 8px; margin-top: 10px; padding-top: 14px; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
            )
            grid = QGridLayout(group)
            for i, (action_type, icon, name) in enumerate(actions):
                card = ActionCard(action_type, icon, name)
                card.clicked.connect(self._on_action_clicked)
                grid.addWidget(card, i // 5, i % 5)
            layout.addWidget(group)

        # 当前配置
        config_group = QGroupBox("当前配置")
        config_group.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-weight: bold; border: 1px solid #45475a; border-radius: 8px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        config_layout = QVBoxLayout(config_group)
        self._config_label = QLabel("选择一个动作查看配置")
        self._config_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self._config_label.setWordWrap(True)
        config_layout.addWidget(self._config_label)
        layout.addWidget(config_group)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_action_clicked(self, action_type: str):
        """动作卡片被点击。"""
        from core.action_executor import ActionExecutor
        info = ActionExecutor.AVAILABLE_ACTIONS.get(action_type, {})
        name = info.get("name", action_type)
        params = info.get("params", [])
        icon = info.get("icon", "")

        self._config_label.setText(
            f"{icon} {name}\n"
            f"类型: {action_type}\n"
            f"参数: {', '.join(params) if params else '无'}"
        )
        self.action_selected.emit(action_type, {})

    def _setup_demo_data(self):
        """设置演示数据。"""
        pass
