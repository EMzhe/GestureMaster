"""
GestureMaster - 手势控制大师
基于 MediaPipe 的 Windows 手势识别桌面控制应用。
"""

import sys
import os
import time
import logging
import copy
import traceback
from threading import Thread

# 修复 Windows 控制台编码
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QThread

from core.camera import CameraManager
from core.hand_detector import HandDetector
from core.gesture_classifier import GestureClassifier, GestureResult, GESTURE_NAMES
from core.action_executor import ActionExecutor
from core.mouse_controller import MouseController, MouseConfig
from ui.main_window import MainWindow
from ui.styles import get_style
from utils.config_manager import ConfigManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("GestureMaster")


# ---------------------------------------------------------------------------
# 识别工作线程（使用 QThread 避免跨线程信号问题）
# ---------------------------------------------------------------------------

class RecognitionWorker(QThread):
    """
    手势识别工作线程。
    使用 QThread 而非普通 threading.Thread，确保信号槽机制正常工作。
    """

    # 信号：使用 bytes 传递帧数据（线程安全的拷贝）
    frame_ready = pyqtSignal(bytes, int, int, int)  # data, h, w, ch
    gesture_detected = pyqtSignal(str, float, str, str)  # key, conf, emoji, action
    fps_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    mouse_status = pyqtSignal(tuple, str)  # position, action

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._running = False
        self._camera = None
        self._detector = None
        self._classifier = None
        self._executor = None
        self._mouse_controller = None
        self._mouse_enabled = False
        self._consecutive_errors = 0
        self._max_consecutive_errors = 30  # 连续错误阈值

        # 手势稳定性检查
        self._gesture_buffer = []  # 存储最近识别的手势
        self._buffer_size = 5  # 缓冲区大小（需要连续识别相同手势的次数）
        self._last_confirmed_gesture = ""  # 最后确认的手势

    def run(self):
        """线程主循环。"""
        try:
            # 初始化组件
            cam_cfg = self._config.get("camera", {})
            det_cfg = self._config.get("detection", {})

            self._camera = CameraManager(
                device_id=cam_cfg.get("device_id", 0),
                resolution=tuple(cam_cfg.get("resolution", [640, 480])),
                fps=cam_cfg.get("fps", 30),
            )

            self._detector = HandDetector(
                max_hands=det_cfg.get("max_hands", 1),
                detection_confidence=det_cfg.get("confidence", 0.7),
                tracking_confidence=0.5,
            )

            self._classifier = GestureClassifier(
                confidence_threshold=det_cfg.get("confidence", 0.7),
                history_size=det_cfg.get("history_size", 30),
                sequence_window=det_cfg.get("sequence_window", 2.0),
            )

            self._executor = ActionExecutor(
                cooldown=det_cfg.get("gesture_cooldown", 1.0),
            )

            # Initialize mouse controller
            self._mouse_controller = MouseController()

            if not self._camera.start():
                self.error_occurred.emit("无法启动摄像头，请检查摄像头是否被其他程序占用")
                return

            self._running = True
            fps_counter = 0
            fps_start = time.time()

            logger.info("识别线程已启动")

            while self._running:
                try:
                    frame = self._camera.get_frame()
                    if frame is None:
                        time.sleep(0.01)
                        continue

                    # 【修复】发送帧数据的拷贝（bytes 格式，完全线程安全）
                    h, w, ch = frame.shape
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frame_ready.emit(frame_rgb.tobytes(), h, w, ch)

                    # 手部检测
                    hands = self._detector.detect(frame)
                    self._consecutive_errors = 0  # 重置错误计数

                    if hands:
                        hand = hands[0]
                        landmarks = hand.landmarks

                        # 手势分类
                        bindings = self._config.get("bindings", [])
                        sequences = {}
                        for seq in self._config.get("sequences", []):
                            sequences[seq.get("id", "")] = {
                                "gestures": seq.get("gestures", []),
                                "timeout": seq.get("timeout", 2.0),
                            }

                        result = self._classifier.classify(landmarks, sequences)

                        if result.gesture != "none" and result.confidence >= 0.7:
                            # 手势稳定性检查
                            self._gesture_buffer.append(result.gesture)
                            if len(self._gesture_buffer) > self._buffer_size:
                                self._gesture_buffer.pop(0)

                            # 计算稳定性
                            if len(self._gesture_buffer) >= 3:
                                stability = sum(1 for g in self._gesture_buffer if g == result.gesture) / len(self._gesture_buffer)
                            else:
                                stability = 0

                            # 稳定后触发动作
                            if stability >= 0.6:
                                action_desc = self._find_action(result.gesture, bindings)
                                gesture_info = GESTURE_NAMES.get(result.gesture, ("未知", "❓"))
                                emoji = gesture_info[1]

                                # 手势变化时触发动作执行
                                if result.gesture != self._last_confirmed_gesture:
                                    self._last_confirmed_gesture = result.gesture
                                    self._execute_action(result.gesture, bindings)

                                self.gesture_detected.emit(
                                    result.gesture, result.confidence, emoji, action_desc
                                )
                            else:
                                # 还在稳定中
                                gesture_info = GESTURE_NAMES.get(result.gesture, ("未知", "❓"))
                                emoji = gesture_info[1]
                                action_desc = self._find_action(result.gesture, bindings)
                                self.gesture_detected.emit(
                                    result.gesture, result.confidence * 0.8, emoji, action_desc
                                )
                        else:
                            # 没有检测到手势
                            if len(self._gesture_buffer) > 0:
                                self._gesture_buffer.clear()
                                self._last_confirmed_gesture = ""

                        # Mouse control
                        if self._mouse_enabled and self._mouse_controller:
                            mouse_result = self._mouse_controller.update(landmarks, result.gesture)
                            if mouse_result.get("action") != "none":
                                self.mouse_status.emit(
                                    mouse_result.get("position", (0, 0)),
                                    mouse_result.get("action", "none")
                                )

                    # FPS 计算
                    fps_counter += 1
                    elapsed = time.time() - fps_start
                    if elapsed >= 1.0:
                        self.fps_updated.emit(fps_counter / elapsed)
                        fps_counter = 0
                        fps_start = time.time()

                    time.sleep(0.01)

                except Exception as e:
                    self._consecutive_errors += 1
                    logger.warning(f"识别循环异常 ({self._consecutive_errors}/{self._max_consecutive_errors}): {e}")
                    if self._consecutive_errors >= self._max_consecutive_errors:
                        logger.error(f"连续错误过多，停止识别线程")
                        self.error_occurred.emit(f"识别出错: {e}")
                        break
                    time.sleep(0.05)  # 短暂暂停后重试

        except Exception as e:
            logger.error(f"识别线程启动失败: {e}\n{traceback.format_exc()}")
            self.error_occurred.emit(f"识别线程启动失败: {e}")
        finally:
            # 清理资源
            self._cleanup_resources()
            logger.info("识别线程已停止")

    def _cleanup_resources(self):
        """安全清理所有资源。"""
        try:
            if self._mouse_controller:
                self._mouse_controller.stop()
                self._mouse_controller = None
        except Exception as e:
            logger.warning(f"清理鼠标控制器资源时出错: {e}")

        try:
            if self._camera:
                self._camera.stop()
                self._camera = None
        except Exception as e:
            logger.warning(f"清理摄像头资源时出错: {e}")

        try:
            if self._detector:
                self._detector.close()
                self._detector = None
        except Exception as e:
            logger.warning(f"清理检测器资源时出错: {e}")

    def enable_mouse_control(self, enabled: bool):
        """Enable or disable mouse control"""
        self._mouse_enabled = enabled
        if self._mouse_controller:
            if enabled:
                self._mouse_controller.start()
            else:
                self._mouse_controller.stop()

    def update_mouse_sensitivity(self, value: float):
        """Update mouse sensitivity"""
        if self._mouse_controller:
            self._mouse_controller.set_sensitivity(value)

    def update_mouse_smooth(self, value: float):
        """Update mouse smoothing"""
        if self._mouse_controller:
            self._mouse_controller.set_smooth_factor(value)

    def stop(self):
        """停止识别。"""
        self._running = False
        self._consecutive_errors = 0

    def _find_action(self, gesture_key: str, bindings: list) -> str:
        """查找手势绑定的动作描述。"""
        for binding in bindings:
            if binding.get("gesture") == gesture_key and binding.get("enabled", True):
                actions = binding.get("actions", [])
                if actions:
                    action_type = actions[0].get("type", "")
                    action_info = ActionExecutor.AVAILABLE_ACTIONS.get(action_type, {})
                    return action_info.get("name", action_type)
        return ""

    def _execute_action(self, gesture_key: str, bindings: list):
        """执行手势绑定的动作。"""
        try:
            for binding in bindings:
                if binding.get("gesture") == gesture_key and binding.get("enabled", True):
                    actions = binding.get("actions", [])
                    for action in actions:
                        action_type = action.get("type", "")
                        params = action.get("params", {})
                        try:
                            # ActionExecutor 内部会检查冷却时间
                            result = self._executor.execute(action_type, params)
                            if result.success:
                                logger.info(f"执行动作: {action_type} (手势: {gesture_key})")
                            else:
                                logger.debug(f"动作未执行: {result.message}")
                        except Exception as e:
                            logger.warning(f"动作执行异常: {e}")
                    break
        except Exception as e:
            logger.warning(f"_execute_action 异常: {e}")

    def get_executor(self) -> ActionExecutor:
        """获取动作执行器（用于测试页面）。"""
        return self._executor


# ---------------------------------------------------------------------------
# 应用主类
# ---------------------------------------------------------------------------

class GestureMasterApp:
    """GestureMaster 应用主类。"""

    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("GestureMaster")
        self._app.setApplicationVersion("1.0.0")
        self._app.setStyleSheet(get_style("dark"))

        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self._app.setWindowIcon(QIcon(icon_path))

        # 设置全局异常处理
        sys.excepthook = self._global_exception_handler

        self._config = ConfigManager()
        self._window = MainWindow(self._config)

        # 设置窗口图标
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self._window.setWindowIcon(QIcon(icon_path))

        # 【修复】独立的动作执行器（用于测试页面，不依赖识别线程）
        self._standalone_executor = ActionExecutor(cooldown=1.0)

        # 识别工作线程
        self._worker = None

        self._connect_signals()

    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """全局异常处理函数 - 静默处理，不弹窗。"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 只记录日志，不弹窗
        logger.debug(
            f"异常: {exc_type.__name__}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    def _connect_signals(self):
        """连接信号和槽。"""
        try:
            # 窗口信号 → 启动/停止识别
            self._window.camera_start_requested.connect(self._start_recognition)
            self._window.camera_stop_requested.connect(self._stop_recognition)

            # 手势管理页面信号
            self._window._gesture_manager_page.binding_changed.connect(self._on_binding_changed)
            self._window._gesture_manager_page.toggle_changed.connect(self._on_gesture_toggled)
            self._window._gesture_manager_page.save_requested.connect(self._on_save_config)

            # 手势测试页面信号
            self._window._test_page_improved.test_action_requested.connect(self._on_test_action)

            # Mouse control page signals
            self._window._mouse_control_page.mouse_control_toggled.connect(self._on_mouse_control_toggled)
            self._window._mouse_control_page.sensitivity_changed.connect(self._on_mouse_sensitivity_changed)
            self._window._mouse_control_page.smooth_factor_changed.connect(self._on_mouse_smooth_changed)

            # Load initial bindings to gesture manager
            bindings = self._config.get_bindings()
            self._window._gesture_manager_page.load_bindings(bindings)
        except Exception as e:
            logger.error(f"连接信号时出错: {e}")

    def _start_recognition(self):
        """启动识别线程。"""
        try:
            if self._worker and self._worker.isRunning():
                logger.warning("识别线程已在运行")
                return

            self._worker = RecognitionWorker(self._config)

            # 连接信号
            self._worker.frame_ready.connect(self._on_frame)
            self._worker.gesture_detected.connect(self._on_gesture)
            self._worker.fps_updated.connect(self._window.update_fps)
            self._worker.error_occurred.connect(self._on_recognition_error)
            self._worker.mouse_status.connect(self._on_mouse_status)

            self._worker.start()
            logger.info("识别已启动")
        except Exception as e:
            logger.error(f"启动识别失败: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(
                self._window,
                "启动失败",
                f"无法启动识别:\n{e}"
            )

    def _stop_recognition(self):
        """停止识别线程。"""
        try:
            if self._worker:
                self._worker.stop()
                if not self._worker.wait(3000):
                    logger.warning("识别线程未能在3秒内停止，强制终止")
                    self._worker.terminate()
                    self._worker.wait(1000)
                self._worker = None
            logger.info("识别已停止")
        except Exception as e:
            logger.error(f"停止识别时出错: {e}")
            self._worker = None

    def _on_recognition_error(self, msg: str):
        """识别错误回调 - 静默处理。"""
        logger.error(f"引擎错误: {msg}")
        try:
            # 停止识别
            self._stop_recognition()
            # 更新 UI 状态
            self._window._on_stop()
            # 不弹窗，只记录日志
        except Exception as e:
            logger.debug(f"处理识别错误时出错: {e}")

    def _on_frame(self, data: bytes, h: int, w: int, ch: int):
        """接收帧数据（bytes 格式，线程安全）。"""
        try:
            # 从 bytes 重建 numpy 数组
            rgb_array = np.frombuffer(data, dtype=np.uint8).reshape(h, w, ch)
            # 创建副本以确保数据独立性
            rgb_array = rgb_array.copy()
            self._window.update_camera_frame(rgb_array)
        except Exception as e:
            # 静默处理，不记录日志
            pass

    def _on_gesture(self, gesture_key: str, confidence: float, emoji: str, action: str):
        """手势识别结果回调。"""
        self._window.update_gesture(gesture_key, emoji, confidence, action)

    def _on_test_gesture(self, gesture_key: str, gesture_name: str):
        """测试手势触发。"""
        logger.info(f"测试手势: {gesture_key} ({gesture_name})")

        # 【修复】使用独立的执行器，不依赖识别线程
        bindings = self._config.get_bindings()
        for binding in bindings:
            if binding.get("gesture") == gesture_key and binding.get("enabled", True):
                actions = binding.get("actions", [])
                for action in actions:
                    action_type = action.get("type", "")
                    params = action.get("params", {})
                    try:
                        self._standalone_executor.execute(action_type, params)
                    except Exception as e:
                        logger.warning(f"测试动作执行异常: {e}")
                break

        # 更新测试页面
        self._window._test_page.add_test_history(gesture_key)

    def _on_binding_changed(self, gesture_key: str, binding_data: dict):
        """Handle binding change from gesture manager"""
        logger.info(f"Binding changed: {gesture_key} -> {binding_data}")

        # Update config
        bindings = self._config.get("bindings", [])
        found = False
        for binding in bindings:
            if binding.get("gesture") == gesture_key:
                binding["actions"] = [{"type": binding_data["action"], "params": binding_data["params"]}]
                found = True
                break

        if not found and binding_data["action"]:
            bindings.append({
                "id": f"default_{gesture_key}",
                "gesture_type": "static",
                "gesture": gesture_key,
                "actions": [{"type": binding_data["action"], "params": binding_data["params"]}],
                "enabled": True,
                "description": f"{gesture_key} -> {binding_data['action']}",
                "cooldown": 1.5
            })

        self._config.set("bindings", bindings)

    def _on_gesture_toggled(self, gesture_key: str, enabled: bool):
        """Handle gesture toggle"""
        logger.info(f"Gesture toggled: {gesture_key} = {enabled}")

        bindings = self._config.get("bindings", [])
        for binding in bindings:
            if binding.get("gesture") == gesture_key:
                binding["enabled"] = enabled
                break
        self._config.set("bindings", bindings)

    def _on_save_config(self):
        """Save configuration"""
        try:
            self._config.save()
            logger.info("Configuration saved")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self._window, "保存成功", "配置已保存！")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self._window, "保存失败", f"保存配置失败: {e}")

    def _on_test_action(self, action_type: str, params: dict):
        """Test action from gesture test page"""
        logger.info(f"Testing action: {action_type} with params: {params}")
        try:
            result = self._standalone_executor.execute(action_type, params)
            if result.success:
                logger.info(f"Test action executed: {action_type}")
            else:
                logger.warning(f"Test action failed: {result.message}")
        except Exception as e:
            logger.error(f"Test action error: {e}")

    def _on_mouse_control_toggled(self, enabled: bool):
        """Handle mouse control toggle"""
        logger.info(f"Mouse control: {'enabled' if enabled else 'disabled'}")
        if self._worker:
            self._worker.enable_mouse_control(enabled)

    def _on_mouse_sensitivity_changed(self, value: float):
        """Handle mouse sensitivity change"""
        if self._worker:
            self._worker.update_mouse_sensitivity(value)

    def _on_mouse_smooth_changed(self, value: float):
        """Handle mouse smooth factor change"""
        if self._worker:
            self._worker.update_mouse_smooth(value)

    def _on_mouse_status(self, position: tuple, action: str):
        """Handle mouse status update"""
        self._window._mouse_control_page.update_mouse_status(position, action)

    def run(self):
        """运行应用。"""
        self._window.show()
        logger.info("GestureMaster 已启动")
        return self._app.exec()

    def cleanup(self):
        """清理资源。"""
        try:
            self._stop_recognition()
        except Exception as e:
            logger.error(f"停止识别时出错: {e}")

        try:
            self._config.save()
        except Exception as e:
            logger.error(f"保存配置时出错: {e}")

        logger.info("GestureMaster 已退出")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    """程序入口。"""
    try:
        print("=" * 50)
        print("  GestureMaster - 手势控制大师 v1.0.0")
        print("  基于 MediaPipe 的手势识别桌面控制应用")
        print("=" * 50)

        app = GestureMasterApp()
        exit_code = app.run()
        app.cleanup()
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        try:
            input("按 Enter 键退出...")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
