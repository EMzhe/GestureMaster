"""
手势管理页面 - 简化版
显示所有手势及其绑定状态，支持快速编辑
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QComboBox, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent


class ShortcutRecorder(QLineEdit):
    """快捷键录制控件"""
    shortcut_recorded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("点击后按下键盘按键...")
        self.setReadOnly(True)
        self._recording = False
        self._pressed_keys = set()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._recording = True
        self._pressed_keys.clear()
        self.setText("")
        self.setPlaceholderText("请按下按键...")
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self._recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        text = event.text()

        # 记录修饰键
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            self._pressed_keys.add(key)
            self._update_display()
            return

        # 记录普通按键
        self._pressed_keys.add(key)

        # 生成快捷键字符串
        combo = self._build_combo_string(key, text)
        self.setText(combo)
        self._recording = False
        self.releaseKeyboard()
        self.setPlaceholderText("点击后按下键盘按键...")
        self.shortcut_recorded.emit(combo)

    def _build_combo_string(self, main_key, text):
        """构建快捷键字符串"""
        parts = []

        # 修饰键
        if Qt.Key.Key_Control in self._pressed_keys:
            parts.append("ctrl")
        if Qt.Key.Key_Alt in self._pressed_keys:
            parts.append("alt")
        if Qt.Key.Key_Shift in self._pressed_keys:
            parts.append("shift")
        if Qt.Key.Key_Meta in self._pressed_keys:
            parts.append("win")

        # 主按键
        key_map = {
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Escape: "escape",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
        }

        if main_key in key_map:
            parts.append(key_map[main_key])
        elif text and len(text) == 1:
            parts.append(text.lower())
        else:
            parts.append(f"key_{main_key}")

        return "+".join(parts)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._recording:
            self._recording = False
            self._pressed_keys.clear()
            self.releaseKeyboard()
            self.setPlaceholderText("点击后按下键盘按键...")

    def _update_display(self):
        """更新显示当前按下的修饰键"""
        parts = []
        if Qt.Key.Key_Control in self._pressed_keys:
            parts.append("Ctrl")
        if Qt.Key.Key_Alt in self._pressed_keys:
            parts.append("Alt")
        if Qt.Key.Key_Shift in self._pressed_keys:
            parts.append("Shift")
        if Qt.Key.Key_Meta in self._pressed_keys:
            parts.append("Win")
        self.setText(" + ".join(parts) + " + ...")


class QuickBindDialog(QDialog):
    """快速绑定对话框 - 支持快捷键录制"""

    def __init__(self, gesture_name: str, gesture_emoji: str,
                 current_action: str = "", current_params: dict = None, parent=None):
        super().__init__(parent)
        self.gesture_name = gesture_name
        self.gesture_emoji = gesture_emoji
        self.setWindowTitle(f"绑定手势 - {gesture_emoji} {gesture_name}")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; background: transparent; border: none; }
            QComboBox, QLineEdit {
                background: #313244; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 4px;
                padding: 8px; font-size: 13px;
            }
            QComboBox:hover, QLineEdit:hover { border-color: #89b4fa; }
        """)

        self._init_ui(current_action, current_params or {})

    def _init_ui(self, current_action: str, current_params: dict):
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel(f"{self.gesture_emoji} {self.gesture_name}")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        # 动作类型
        form = QFormLayout()

        self._action_combo = QComboBox()
        actions = [
            ("", "无动作"),
            ("lock_screen", "🔒 锁屏"),
            ("mute", "🔇 静音"),
            ("unmute", "🔊 取消静音"),
            ("play_pause", "▶ 播放/暂停"),
            ("next_track", "⏭ 下一曲"),
            ("prev_track", "⏮ 上一曲"),
            ("volume_up", "🔊 音量+"),
            ("volume_down", "🔉 音量-"),
            ("open_url", "🌐 打开网址"),
            ("open_app", "📁 打开程序"),
            ("open_folder", "📂 打开目录"),
            ("minimize_window", "📌 最小化窗口"),
            ("close_window", "❌ 关闭窗口"),
            ("alt_tab", "🔄 切换窗口"),
            ("send_key", "⌨ 发送按键"),
            ("send_combo", "⌨ 发送组合键"),
        ]
        for action_id, name in actions:
            self._action_combo.addItem(name, action_id)

        # 设置当前值
        for i, (action_id, _) in enumerate(actions):
            if action_id == current_action:
                self._action_combo.setCurrentIndex(i)
                break

        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        form.addRow("动作类型:", self._action_combo)

        # URL 输入
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("例如: https://www.bilibili.com")
        self._url_input.setVisible(False)
        if current_action == "open_url":
            self._url_input.setText(current_params.get("url", ""))
        form.addRow("网址:", self._url_input)

        # 路径输入
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("例如: C:\\Program Files\\app.exe")
        self._path_input.setVisible(False)
        if current_action in ("open_app", "open_folder"):
            self._path_input.setText(current_params.get("path", ""))
        form.addRow("路径:", self._path_input)

        # 快捷键录制（单个按键）
        self._key_recorder = ShortcutRecorder()
        self._key_recorder.setVisible(False)
        if current_action == "send_key":
            self._key_recorder.setText(current_params.get("key", ""))
        form.addRow("按键:", self._key_recorder)

        # 组合键输入
        self._combo_recorder = ShortcutRecorder()
        self._combo_recorder.setVisible(False)
        if current_action == "send_combo":
            self._combo_recorder.setText(current_params.get("combo", ""))
        form.addRow("组合键:", self._combo_recorder)

        # 快捷提示
        self._hint_label = QLabel()
        self._hint_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        self._hint_label.setWordWrap(True)
        self._hint_label.setVisible(False)
        form.addRow("", self._hint_label)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 初始显示
        self._on_action_changed()

    def _on_action_changed(self):
        action = self._action_combo.currentData()

        # 隐藏所有输入
        self._url_input.setVisible(False)
        self._path_input.setVisible(False)
        self._key_recorder.setVisible(False)
        self._combo_recorder.setVisible(False)
        self._hint_label.setVisible(False)

        # 显示对应的输入
        if action == "open_url":
            self._url_input.setVisible(True)
        elif action in ("open_app", "open_folder"):
            self._path_input.setVisible(True)
        elif action == "send_key":
            self._key_recorder.setVisible(True)
            self._hint_label.setVisible(True)
            self._hint_label.setText("点击输入框，然后按下键盘上的任意键（如 Enter、Space、F1 等）")
        elif action == "send_combo":
            self._combo_recorder.setVisible(True)
            self._hint_label.setVisible(True)
            self._hint_label.setText("点击输入框，然后按下组合键（如 Ctrl+C、Alt+Tab、Ctrl+Shift+S 等）")

    def get_result(self) -> dict:
        """获取绑定结果"""
        action = self._action_combo.currentData()

        params = {}
        if action == "open_url":
            params["url"] = self._url_input.text().strip()
        elif action == "open_app":
            params["path"] = self._path_input.text().strip()
        elif action == "open_folder":
            params["path"] = self._path_input.text().strip()
        elif action == "send_key":
            params["key"] = self._key_recorder.text().strip()
        elif action == "send_combo":
            params["combo"] = self._combo_recorder.text().strip()

        return {
            "action": action,
            "params": params
        }


class GestureItemCard(QFrame):
    """手势项目卡片"""

    # 信号
    binding_changed = pyqtSignal(str, dict)  # gesture_key, binding_data
    toggle_changed = pyqtSignal(str, bool)  # gesture_key, enabled

    def __init__(self, gesture_key: str, gesture_name: str, gesture_emoji: str,
                 gesture_desc: str, action: str = "", params: dict = None,
                 enabled: bool = True, parent=None):
        super().__init__(parent)
        self.gesture_key = gesture_key
        self.gesture_name = gesture_name
        self.gesture_emoji = gesture_emoji
        self.action = action
        self.params = params or {}
        self.enabled = enabled

        self._init_ui(gesture_desc)

    def _init_ui(self, desc: str):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # 左侧：手势信息
        left = QVBoxLayout()
        left.setSpacing(4)

        # Emoji + 名称
        header = QHBoxLayout()
        emoji_label = QLabel(self.gesture_emoji)
        emoji_label.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        header.addWidget(emoji_label)

        name_label = QLabel(self.gesture_name)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #cdd6f4; background: transparent; border: none;")
        header.addWidget(name_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 11px; color: #6c7086; background: transparent; border: none;")
        header.addWidget(desc_label)

        header.addStretch()
        left.addLayout(header)

        # 当前绑定
        action_text = self._get_action_display()
        self._action_label = QLabel(f"→ {action_text}")
        self._action_label.setStyleSheet("font-size: 13px; color: #a6e3a1; background: transparent; border: none;")
        left.addWidget(self._action_label)

        layout.addLayout(left, 1)

        # 右侧：操作按钮
        right = QVBoxLayout()
        right.setSpacing(6)

        # 启用开关
        self._enable_check = QCheckBox("启用")
        self._enable_check.setChecked(self.enabled)
        self._enable_check.setStyleSheet("""
            QCheckBox { color: #cdd6f4; background: transparent; border: none; }
            QCheckBox::indicator { width: 16px; height: 16px; }
        """)
        self._enable_check.stateChanged.connect(self._on_toggle)
        right.addWidget(self._enable_check)

        # 编辑按钮
        edit_btn = QPushButton("编辑绑定")
        edit_btn.setFixedSize(80, 28)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #89b4fa; color: #1e1e2e;
                border: none; border-radius: 4px;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #74c7ec; }
        """)
        edit_btn.clicked.connect(self._edit_binding)
        right.addWidget(edit_btn)

        layout.addLayout(right)

    def _get_action_display(self) -> str:
        """获取动作显示文本"""
        action_names = {
            "lock_screen": "🔒 锁屏",
            "mute": "🔇 静音",
            "unmute": "🔊 取消静音",
            "play_pause": "▶ 播放/暂停",
            "next_track": "⏭ 下一曲",
            "prev_track": "⏮ 上一曲",
            "volume_up": "🔊 音量+",
            "volume_down": "🔉 音量-",
            "open_url": f"🌐 打开: {self.params.get('url', '')}",
            "open_app": f"📁 打开: {self.params.get('path', '')}",
            "open_folder": f"📂 打开: {self.params.get('path', '')}",
            "minimize_window": "📌 最小化",
            "close_window": "❌ 关闭窗口",
            "alt_tab": "🔄 切换窗口",
            "send_key": f"⌨ 按键: {self.params.get('key', '')}",
            "send_combo": f"⌨ 组合键: {self.params.get('combo', '')}",
        }
        return action_names.get(self.action, "未绑定")

    def _update_style(self):
        if self.enabled:
            self.setStyleSheet("""
                QFrame {
                    background-color: #181825;
                    border: 1px solid #313244;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #89b4fa;
                    background-color: #1e1e2e;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #11111b;
                    border: 1px solid #313244;
                    border-radius: 8px;
                }
            """)

    def _on_toggle(self, state):
        self.enabled = bool(state)
        self._update_style()
        self.toggle_changed.emit(self.gesture_key, self.enabled)

    def _edit_binding(self):
        """打开编辑绑定对话框"""
        dialog = QuickBindDialog(
            self.gesture_name,
            self.gesture_emoji,
            self.action,
            self.params,
            self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            self.action = result["action"]
            self.params = result["params"]

            # 更新显示
            self._action_label.setText(f"→ {self._get_action_display()}")

            # 发送信号
            self.binding_changed.emit(self.gesture_key, {
                "action": self.action,
                "params": self.params
            })

    def update_binding(self, action: str, params: dict = None):
        """更新绑定（外部调用）"""
        self.action = action
        self.params = params or {}
        self._action_label.setText(f"→ {self._get_action_display()}")


class GestureManagerPage(QWidget):
    """
    手势管理页面
    显示所有手势及其绑定状态
    """

    # 信号
    binding_changed = pyqtSignal(str, dict)  # gesture_key, binding_data
    toggle_changed = pyqtSignal(str, bool)  # gesture_key, enabled
    save_requested = pyqtSignal()  # 请求保存配置

    # 手势定义
    GESTURES = [
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
        {"key": "wave", "name": "挥手", "emoji": "👋", "desc": "手掌左右摆动"},
        {"key": "circle", "name": "画圈", "emoji": "⭕", "desc": "手掌画圆圈"},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gesture_cards = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 标题栏
        header = QHBoxLayout()

        title = QLabel("✋ 手势管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        header.addWidget(title)

        header.addStretch()

        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #a6e3a1; color: #1e1e2e;
                font-weight: bold; border: none;
                border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background: #94e2d5; }
        """)
        save_btn.clicked.connect(self.save_requested.emit)
        header.addWidget(save_btn)

        main_layout.addLayout(header)

        # 说明
        info = QLabel("点击「编辑绑定」为手势设置动作，启用/禁用手势，完成后点击「保存配置」")
        info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        main_layout.addWidget(info)

        # 手势列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        self._list_layout = QVBoxLayout(scroll_widget)
        self._list_layout.setSpacing(8)

        # 创建手势卡片
        for gesture in self.GESTURES:
            card = GestureItemCard(
                gesture_key=gesture["key"],
                gesture_name=gesture["name"],
                gesture_emoji=gesture["emoji"],
                gesture_desc=gesture["desc"],
                parent=self
            )
            card.binding_changed.connect(self.binding_changed.emit)
            card.toggle_changed.connect(self.toggle_changed.emit)

            self._gesture_cards[gesture["key"]] = card
            self._list_layout.addWidget(card)

        self._list_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, 1)

    def load_bindings(self, bindings: list):
        """加载绑定配置"""
        for binding in bindings:
            gesture_key = binding.get("gesture", "")
            if gesture_key in self._gesture_cards:
                card = self._gesture_cards[gesture_key]
                actions = binding.get("actions", [])
                if actions:
                    action = actions[0]
                    card.update_binding(
                        action.get("type", ""),
                        action.get("params", {})
                    )
                card.enabled = binding.get("enabled", True)
                card._enable_check.setChecked(card.enabled)
                card._update_style()

    def get_bindings(self) -> list:
        """获取所有绑定配置"""
        bindings = []
        for gesture_key, card in self._gesture_cards.items():
            if card.action:
                bindings.append({
                    "id": f"default_{gesture_key}",
                    "gesture_type": "static",
                    "gesture": gesture_key,
                    "actions": [{"type": card.action, "params": card.params}],
                    "enabled": card.enabled,
                    "description": f"{card.gesture_name} -> {card.action}",
                    "cooldown": 1.5
                })
        return bindings
