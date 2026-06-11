"""
Mouse Control Page
Camera-based mouse cursor control
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QSlider, QComboBox, QFrame,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter


class MouseControlPage(QWidget):
    """
    Mouse Control Page
    Enable/disable camera-based mouse control
    """

    # Signals
    mouse_control_toggled = pyqtSignal(bool)  # enabled/disabled
    sensitivity_changed = pyqtSignal(float)
    smooth_factor_changed = pyqtSignal(float)
    click_gesture_changed = pyqtSignal(str)

    GESTURES = [
        ("pinch", "捏合"),
        ("fist", "握拳"),
        ("peace", "比耶"),
        ("ok", "OK手势"),
        ("thumbs_up", "竖大拇指"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_active = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title
        title = QLabel("🖱️ 鼠标控制")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #cdd6f4;")
        main_layout.addWidget(title)

        # Description
        desc = QLabel("通过摄像头手势控制鼠标光标")
        desc.setStyleSheet("color: #a6adc8; font-size: 13px;")
        main_layout.addWidget(desc)

        main_layout.addSpacing(10)

        # Main control area
        content_layout = QHBoxLayout()

        # Left: Preview and toggle
        left_panel = QVBoxLayout()

        # Status display
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 2px solid #313244;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)

        self._status_icon = QLabel("🖱️")
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_icon.setStyleSheet("font-size: 64px; background: transparent; border: none;")
        status_layout.addWidget(self._status_icon)

        self._status_label = QLabel("鼠标控制: 关闭")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f38ba8; background: transparent; border: none;")
        status_layout.addWidget(self._status_label)

        self._position_label = QLabel("位置: --, --")
        self._position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._position_label.setStyleSheet("font-size: 14px; color: #a6adc8; background: transparent; border: none;")
        status_layout.addWidget(self._position_label)

        self._action_label = QLabel("动作: --")
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_label.setStyleSheet("font-size: 14px; color: #a6adc8; background: transparent; border: none;")
        status_layout.addWidget(self._action_label)

        left_panel.addWidget(status_frame)

        # Toggle button
        self._toggle_btn = QPushButton("启动鼠标控制")
        self._toggle_btn.setFixedHeight(50)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 16px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #94e2d5;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_mouse_control)
        left_panel.addWidget(self._toggle_btn)

        content_layout.addLayout(left_panel, 1)

        # Right: Settings
        right_panel = QVBoxLayout()

        # Settings group
        settings_group = QGroupBox("设置")
        settings_group.setStyleSheet("""
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
        settings_layout = QVBoxLayout(settings_group)

        # Sensitivity
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("灵敏度:"))
        self._sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setRange(5, 30)
        self._sensitivity_slider.setValue(15)
        self._sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        sens_layout.addWidget(self._sensitivity_slider)
        self._sens_label = QLabel("1.5")
        self._sens_label.setFixedWidth(30)
        sens_layout.addWidget(self._sens_label)
        settings_layout.addLayout(sens_layout)

        # Smoothing
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("平滑度:"))
        self._smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self._smooth_slider.setRange(0, 90)
        self._smooth_slider.setValue(30)
        self._smooth_slider.valueChanged.connect(self._on_smooth_changed)
        smooth_layout.addWidget(self._smooth_slider)
        self._smooth_label = QLabel("0.3")
        self._smooth_label.setFixedWidth(30)
        smooth_layout.addWidget(self._smooth_label)
        settings_layout.addLayout(smooth_layout)

        # Click gesture
        click_layout = QHBoxLayout()
        click_layout.addWidget(QLabel("点击手势:"))
        self._click_combo = QComboBox()
        for key, name in self.GESTURES:
            self._click_combo.addItem(name, key)
        self._click_combo.currentIndexChanged.connect(self._on_click_gesture_changed)
        click_layout.addWidget(self._click_combo)
        settings_layout.addLayout(click_layout)

        # Dead zone
        dead_layout = QHBoxLayout()
        dead_layout.addWidget(QLabel("死区:"))
        self._dead_slider = QSlider(Qt.Orientation.Horizontal)
        self._dead_slider.setRange(1, 10)
        self._dead_slider.setValue(2)
        self._dead_slider.valueChanged.connect(self._on_dead_zone_changed)
        dead_layout.addWidget(self._dead_slider)
        self._dead_label = QLabel("0.02")
        self._dead_label.setFixedWidth(30)
        dead_layout.addWidget(self._dead_label)
        settings_layout.addLayout(dead_layout)

        right_panel.addWidget(settings_group)

        # Instructions
        instructions_group = QGroupBox("使用说明")
        instructions_group.setStyleSheet(settings_group.styleSheet())
        instructions_layout = QVBoxLayout(instructions_group)

        instructions = QLabel(
            "1. 点击「启动鼠标控制」按钮\n"
            "2. 用食指移动控制光标位置\n"
            "3. 做出选定的手势进行点击\n"
            "4. 根据需要调整灵敏度等参数"
        )
        instructions.setStyleSheet("color: #a6adc8; font-size: 12px; background: transparent; border: none;")
        instructions_layout.addWidget(instructions)

        right_panel.addWidget(instructions_group)
        right_panel.addStretch()

        content_layout.addLayout(right_panel, 1)
        main_layout.addLayout(content_layout, 1)

    def _toggle_mouse_control(self):
        """Toggle mouse control on/off"""
        self._is_active = not self._is_active

        if self._is_active:
            self._toggle_btn.setText("停止鼠标控制")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #f38ba8;
                    color: #1e1e2e;
                    font-weight: bold;
                    font-size: 16px;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: #eba0ac;
                }
            """)
            self._status_label.setText("鼠标控制: 开启")
            self._status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1; background: transparent; border: none;")
            self._status_icon.setText("🖱️")
        else:
            self._toggle_btn.setText("启动鼠标控制")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #a6e3a1;
                    color: #1e1e2e;
                    font-weight: bold;
                    font-size: 16px;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: #94e2d5;
                }
            """)
            self._status_label.setText("鼠标控制: 关闭")
            self._status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f38ba8; background: transparent; border: none;")
            self._position_label.setText("位置: --, --")
            self._action_label.setText("动作: --")

        self.mouse_control_toggled.emit(self._is_active)

    def _on_sensitivity_changed(self, value: int):
        """Handle sensitivity change"""
        sens = value / 10.0
        self._sens_label.setText(f"{sens:.1f}")
        self.sensitivity_changed.emit(sens)

    def _on_smooth_changed(self, value: int):
        """Handle smoothing change"""
        smooth = value / 100.0
        self._smooth_label.setText(f"{smooth:.2f}")
        self.smooth_factor_changed.emit(smooth)

    def _on_click_gesture_changed(self, index: int):
        """Handle click gesture change"""
        gesture = self._click_combo.currentData()
        self.click_gesture_changed.emit(gesture)

    def _on_dead_zone_changed(self, value: int):
        """Handle dead zone change"""
        dead = value / 100.0
        self._dead_label.setText(f"{dead:.2f}")

    def update_mouse_status(self, position: tuple = None, action: str = "none"):
        """Update mouse status display"""
        if position:
            self._position_label.setText(f"位置: {position[0]}, {position[1]}")

        action_text = {
            "move": "移动中",
            "click": "点击!",
            "release": "释放",
            "right_click": "右键点击!",
            "none": "空闲",
        }.get(action, action)

        self._action_label.setText(f"动作: {action_text}")

    def is_active(self) -> bool:
        """Check if mouse control is active"""
        return self._is_active

    def get_settings(self) -> dict:
        """Get current settings"""
        return {
            "sensitivity": self._sensitivity_slider.value() / 10.0,
            "smooth_factor": self._smooth_slider.value() / 100.0,
            "click_gesture": self._click_combo.currentData(),
            "dead_zone": self._dead_slider.value() / 100.0,
        }
