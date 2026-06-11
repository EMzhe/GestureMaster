"""
主窗口模块
整合所有页面，提供导航、状态栏、系统托盘等功能。
"""

import sys
import psutil
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QStatusBar,
    QSystemTrayIcon, QMenu, QFrame, QSplitter,
    QComboBox, QSlider, QCheckBox, QSpinBox,
    QGroupBox, QLineEdit, QFileDialog, QMessageBox,
    QApplication, QScrollArea, QFormLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont

from ui.camera_widget import CameraWidget
from ui.gesture_settings import GestureSettingsPage
from ui.action_settings import ActionSettingsPage
from ui.gesture_test import GestureTestPage
from ui.custom_gesture import CustomGesturePage
from ui.mouse_control_page import MouseControlPage
from ui.gesture_manager_page import GestureManagerPage
from ui.gesture_test_page import GestureTestPageImproved


# ---------------------------------------------------------------------------
# 导航按钮
# ---------------------------------------------------------------------------

class NavButton(QPushButton):
    """侧边栏导航按钮。"""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"{icon}  {text}", parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self._update_style(False)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._update_style(active)

    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #89b4fa;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: left;
                    padding-left: 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #a6adc8;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    text-align: left;
                    padding-left: 16px;
                }
                QPushButton:hover {
                    background-color: #313244;
                    color: #cdd6f4;
                }
            """)


# ---------------------------------------------------------------------------
# 预览页面
# ---------------------------------------------------------------------------

class PreviewPage(QWidget):
    """摄像头预览主页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 左侧：摄像头预览
        self.camera_widget = CameraWidget()
        layout.addWidget(self.camera_widget, 3)

        # 右侧：当前手势信息
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)

        info_title = QLabel("📊 当前识别")
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #cdd6f4; border: none;")
        right_layout.addWidget(info_title)

        self._gesture_label = QLabel("等待识别...")
        self._gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gesture_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #89b4fa; border: none;")
        right_layout.addWidget(self._gesture_label)

        self._confidence_label = QLabel("")
        self._confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._confidence_label.setStyleSheet("font-size: 14px; color: #a6adc8; border: none;")
        right_layout.addWidget(self._confidence_label)

        self._action_label = QLabel("")
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_label.setStyleSheet("font-size: 14px; color: #a6e3a1; border: none;")
        self._action_label.setWordWrap(True)
        right_layout.addWidget(self._action_label)

        right_layout.addStretch()

        # 快捷操作
        ops_group = QGroupBox("快捷操作")
        ops_group.setStyleSheet(
            "QGroupBox { color: #cdd6f4; border: 1px solid #313244; border-radius: 8px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        ops_layout = QVBoxLayout(ops_group)

        self._btn_start = QPushButton("▶ 开始识别")
        self._btn_start.setStyleSheet(
            "background: #a6e3a1; color: #1e1e2e; font-weight: bold; border: none; border-radius: 6px; padding: 10px;"
        )
        ops_layout.addWidget(self._btn_start)

        self._btn_stop = QPushButton("⏹ 停止识别")
        self._btn_stop.setStyleSheet(
            "background: #f38ba8; color: #1e1e2e; font-weight: bold; border: none; border-radius: 6px; padding: 10px;"
        )
        self._btn_stop.setEnabled(False)
        ops_layout.addWidget(self._btn_stop)

        right_layout.addWidget(ops_group)
        layout.addWidget(right_panel, 1)

    def update_gesture(self, gesture_name: str, emoji: str, confidence: float, action: str = ""):
        self._gesture_label.setText(f"{emoji} {gesture_name}")
        self._confidence_label.setText(f"置信度: {confidence:.0%}")
        self._action_label.setText(f"→ {action}" if action else "")


# ---------------------------------------------------------------------------
# 设置页面
# ---------------------------------------------------------------------------

class SettingsPage(QWidget):
    """应用设置页面。"""

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 摄像头设置
        cam_group = QGroupBox("📷 摄像头设置")
        cam_group.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-weight: bold; border: 1px solid #45475a; border-radius: 8px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
        )
        cam_layout = QFormLayout(cam_group)

        self._camera_combo = QComboBox()
        self._camera_combo.addItem("摄像头 0", 0)
        self._camera_combo.addItem("摄像头 1", 1)
        cam_layout.addRow("设备:", self._camera_combo)

        self._resolution_combo = QComboBox()
        self._resolution_combo.addItem("640 × 480", (640, 480))
        self._resolution_combo.addItem("1280 × 720", (1280, 720))
        self._resolution_combo.addItem("1920 × 1080", (1920, 1080))
        cam_layout.addRow("分辨率:", self._resolution_combo)

        self._fps_combo = QComboBox()
        self._fps_combo.addItem("15 FPS", 15)
        self._fps_combo.addItem("30 FPS", 30)
        self._fps_combo.addItem("60 FPS", 60)
        self._fps_combo.setCurrentIndex(1)
        cam_layout.addRow("帧率:", self._fps_combo)
        layout.addWidget(cam_group)

        # 检测设置
        det_group = QGroupBox("🔍 检测设置")
        det_group.setStyleSheet(cam_group.styleSheet())
        det_layout = QFormLayout(det_group)

        self._confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self._confidence_slider.setRange(30, 95)
        self._confidence_slider.setValue(70)
        conf_row = QHBoxLayout()
        conf_row.addWidget(self._confidence_slider)
        self._conf_label = QLabel("0.70")
        self._conf_label.setFixedWidth(40)
        self._confidence_slider.valueChanged.connect(lambda v: self._conf_label.setText(f"{v/100:.2f}"))
        conf_row.addWidget(self._conf_label)
        det_layout.addRow("置信度阈值:", conf_row)

        self._max_hands_combo = QComboBox()
        self._max_hands_combo.addItem("1 只手", 1)
        self._max_hands_combo.addItem("2 只手", 2)
        det_layout.addRow("最大手数:", self._max_hands_combo)

        self._cooldown_slider = QSlider(Qt.Orientation.Horizontal)
        self._cooldown_slider.setRange(5, 50)
        self._cooldown_slider.setValue(10)
        cd_row = QHBoxLayout()
        cd_row.addWidget(self._cooldown_slider)
        self._cd_label = QLabel("1.0 秒")
        self._cd_label.setFixedWidth(60)
        self._cooldown_slider.valueChanged.connect(lambda v: self._cd_label.setText(f"{v/10:.1f} 秒"))
        cd_row.addWidget(self._cd_label)
        det_layout.addRow("冷却时间:", cd_row)
        layout.addWidget(det_group)

        # 界面设置
        ui_group = QGroupBox("🎨 界面设置")
        ui_group.setStyleSheet(cam_group.styleSheet())
        ui_layout = QFormLayout(ui_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("深色", "dark")
        self._theme_combo.addItem("浅色", "light")
        ui_layout.addRow("主题:", self._theme_combo)

        self._tray_check = QCheckBox("最小化到系统托盘")
        self._tray_check.setChecked(True)
        ui_layout.addRow("", self._tray_check)

        self._overlay_check = QCheckBox("显示检测叠加层")
        self._overlay_check.setChecked(True)
        ui_layout.addRow("", self._overlay_check)
        layout.addWidget(ui_group)

        # 高级设置
        adv_group = QGroupBox("⚙ 高级设置")
        adv_group.setStyleSheet(cam_group.styleSheet())
        adv_layout = QFormLayout(adv_group)

        self._autostart_check = QCheckBox("开机自启动")
        adv_layout.addRow("", self._autostart_check)

        # 导入导出
        io_layout = QHBoxLayout()
        btn_export = QPushButton("📤 导出配置")
        btn_export.clicked.connect(self._export_config)
        io_layout.addWidget(btn_export)

        btn_import = QPushButton("📥 导入配置")
        btn_import.clicked.connect(self._import_config)
        io_layout.addWidget(btn_import)
        adv_layout.addRow("配置:", io_layout)

        btn_reset = QPushButton("🔄 恢复默认设置")
        btn_reset.setStyleSheet("background: #f38ba8; color: #1e1e2e; font-weight: bold; border: none; border-radius: 6px;")
        btn_reset.clicked.connect(self._reset_settings)
        adv_layout.addRow("", btn_reset)
        layout.addWidget(adv_group)

        # 关于
        about_group = QGroupBox("ℹ 关于")
        about_group.setStyleSheet(cam_group.styleSheet())
        about_layout = QVBoxLayout(about_group)
        about_text = QLabel(
            "<b>GestureMaster</b> v1.0.0<br>"
            "基于 MediaPipe 的手势识别桌面控制应用<br><br>"
            "技术栈: Python + PyQt6 + MediaPipe + OpenCV<br>"
            "支持: 静态手势 / 动态手势 / 手势序列<br>"
            "动作: 系统控制 / 媒体控制 / 应用启动 / 窗口管理 / 自定义"
        )
        about_text.setTextFormat(Qt.TextFormat.RichText)
        about_text.setStyleSheet("color: #a6adc8; font-size: 12px; border: none;")
        about_layout.addWidget(about_text)
        layout.addWidget(about_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "config.json", "JSON (*.json)")
        if path and self._config:
            self._config.export_config(path)
            QMessageBox.information(self, "成功", f"配置已导出到: {path}")

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if path and self._config:
            if self._config.import_config(path):
                QMessageBox.information(self, "成功", "配置已导入，重启后生效。")
            else:
                QMessageBox.warning(self, "失败", "导入配置失败。")

    def _reset_settings(self):
        reply = QMessageBox.question(
            self, "确认", "确定要恢复默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._config:
            self._config.reset_to_defaults()
            QMessageBox.information(self, "成功", "已恢复默认设置，重启后生效。")


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """
    GestureMaster 主窗口。
    左侧导航 + 右侧内容区域 + 底部状态栏。
    """

    camera_start_requested = pyqtSignal()
    camera_stop_requested = pyqtSignal()
    config_changed = pyqtSignal(dict)

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._running = False
        self.setWindowTitle("🎯 GestureMaster - 手势控制大师")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)

        self._init_ui()
        self._init_status_bar()
        self._init_tray()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 左侧导航栏 ----
        nav_panel = QFrame()
        nav_panel.setFixedWidth(180)
        nav_panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border-right: 1px solid #313244;
            }
        """)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(8, 12, 8, 12)
        nav_layout.setSpacing(4)

        # Logo
        logo = QLabel("🎯 GestureMaster")
        logo.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa; padding: 8px; border: none;")
        nav_layout.addWidget(logo)
        nav_layout.addSpacing(8)

        # 导航按钮
        self._nav_buttons = []
        nav_items = [
            ("📷", "摄像头预览"),
            ("✋", "手势管理"),
            ("🧪", "手势测试"),
            ("🖱️", "鼠标控制"),
            ("⚙", "应用设置"),
        ]
        for icon, text in nav_items:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, b=btn: self._on_nav_clicked(b))
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        nav_layout.addStretch()

        # 底部状态指示
        self._status_indicator = QLabel("🔴 未启动")
        self._status_indicator.setStyleSheet("color: #f38ba8; font-size: 12px; padding: 8px; border: none;")
        nav_layout.addWidget(self._status_indicator)

        main_layout.addWidget(nav_panel)

        # ---- 右侧内容区 ----
        self._stack = QStackedWidget()

        # 页面 0: 预览
        self._preview_page = PreviewPage()
        self._preview_page._btn_start.clicked.connect(self._on_start)
        self._preview_page._btn_stop.clicked.connect(self._on_stop)
        self._stack.addWidget(self._preview_page)

        # 页面 1: 手势管理（整合绑定功能）
        self._gesture_manager_page = GestureManagerPage()
        self._stack.addWidget(self._gesture_manager_page)

        # 页面 2: 手势测试
        self._test_page_improved = GestureTestPageImproved()
        self._stack.addWidget(self._test_page_improved)

        # 页面 3: 鼠标控制
        self._mouse_control_page = MouseControlPage()
        self._stack.addWidget(self._mouse_control_page)

        # 页面 4: 设置
        self._settings_page = SettingsPage(self._config)
        self._stack.addWidget(self._settings_page)

        main_layout.addWidget(self._stack, 1)

        # 默认选中第一个
        self._nav_buttons[0].set_active(True)

    def _init_status_bar(self):
        """初始化状态栏。"""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._status_label = QLabel("🔴 未启动")
        self._fps_label = QLabel("FPS: --")
        self._cpu_label = QLabel("CPU: --%")
        self._gesture_status_label = QLabel("当前: --")

        self._status_bar.addWidget(self._status_label)
        self._status_bar.addWidget(QLabel(" | "))
        self._status_bar.addWidget(self._fps_label)
        self._status_bar.addWidget(QLabel(" | "))
        self._status_bar.addWidget(self._cpu_label)
        self._status_bar.addWidget(QLabel(" | "))
        self._status_bar.addWidget(self._gesture_status_label)

        # 定时更新 CPU
        self._cpu_timer = QTimer()
        self._cpu_timer.timeout.connect(self._update_cpu)
        self._cpu_timer.start(2000)

    def _init_tray(self):
        """初始化系统托盘。"""
        self._tray = QSystemTrayIcon(self)
        # 创建一个简单的图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#89b4fa"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#1e1e2e"))
        painter.setFont(QFont("Segoe UI Emoji", 16))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎯")
        painter.end()
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip("GestureMaster")

        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_nav_clicked(self, clicked_btn):
        """导航按钮点击处理。"""
        for i, btn in enumerate(self._nav_buttons):
            if btn == clicked_btn:
                btn.set_active(True)
                self._stack.setCurrentIndex(i)
            else:
                btn.set_active(False)

    def _on_start(self):
        """开始识别。"""
        self._running = True
        self._status_label.setText("🟢 运行中")
        self._status_indicator.setText("🟢 运行中")
        self._status_indicator.setStyleSheet("color: #a6e3a1; font-size: 12px; padding: 8px; border: none;")
        self._preview_page._btn_start.setEnabled(False)
        self._preview_page._btn_stop.setEnabled(True)
        self.camera_start_requested.emit()

    def _on_stop(self):
        """停止识别。"""
        self._running = False
        self._status_label.setText("🔴 已停止")
        self._status_indicator.setText("🔴 已停止")
        self._status_indicator.setStyleSheet("color: #f38ba8; font-size: 12px; padding: 8px; border: none;")
        self._preview_page._btn_start.setEnabled(True)
        self._preview_page._btn_stop.setEnabled(False)
        self.camera_stop_requested.emit()

    def _update_cpu(self):
        """更新 CPU 使用率。"""
        try:
            cpu = psutil.cpu_percent(interval=None)
            self._cpu_label.setText(f"CPU: {cpu:.0f}%")
        except Exception:
            pass

    def _on_tray_activated(self, reason):
        """托盘图标激活。"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        """关闭事件：最小化到托盘或退出。"""
        minimize_to_tray = self._config and self._config.get("ui.minimize_to_tray", True)
        if minimize_to_tray and self._tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self.camera_stop_requested.emit()
            event.accept()

    # ------------------------------------------------------------------
    # 公共 API - 供外部调用更新 UI
    # ------------------------------------------------------------------

    def update_camera_frame(self, cv_image):
        """更新摄像头画面。"""
        self._preview_page.camera_widget.set_frame(cv_image)
        self._test_page_improved.update_camera_frame(cv_image)
        self._custom_gesture_page.update_camera_frame(cv_image)

    def update_gesture(self, gesture_key: str, emoji: str, confidence: float, action: str = "", params: dict = None):
        """更新识别结果。"""
        from core.gesture_classifier import GESTURE_NAMES
        name = GESTURE_NAMES.get(gesture_key, ("未知", "❓"))[0]

        self._preview_page.update_gesture(name, emoji, confidence, action)
        self._preview_page.camera_widget.set_gesture_info(name, confidence, emoji)
        self._gesture_status_label.setText(f"当前: {emoji} {name}")

        # 更新改进的测试页面
        self._test_page_improved.update_recognition(
            gesture_key=gesture_key,
            gesture_name=name,
            emoji=emoji,
            confidence=confidence,
            stability=confidence,  # 简化：用置信度作为稳定性
            action=action,
            params=params or {}
        )

    def update_fps(self, fps: float):
        """更新 FPS 显示。"""
        self._fps_label.setText(f"FPS: {fps:.0f}")
        self._preview_page.camera_widget.set_fps(fps)

    def get_camera_settings(self) -> dict:
        """获取摄像头设置。"""
        return {
            "device_id": self._settings_page._camera_combo.currentData() or 0,
            "resolution": self._settings_page._resolution_combo.currentData() or (640, 480),
            "fps": self._settings_page._fps_combo.currentData() or 30,
        }

    def get_detection_settings(self) -> dict:
        """获取检测设置。"""
        return {
            "confidence": self._settings_page._confidence_slider.value() / 100,
            "max_hands": self._settings_page._max_hands_combo.currentData() or 1,
            "cooldown": self._settings_page._cooldown_slider.value() / 10,
        }
