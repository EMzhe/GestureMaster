"""
动作执行器模块
负责执行手势绑定的各种系统/媒体/应用/窗口/自定义动作。
依赖: pynput, subprocess, webbrowser, ctypes
"""

import os
import time
import ctypes
import logging
import subprocess
import webbrowser
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("GestureMaster")


@dataclass
class ActionResult:
    """动作执行结果。"""
    success: bool
    message: str
    action_type: str = ""
    duration: float = 0.0


class ActionExecutor:
    """
    动作执行器。
    根据动作类型和参数执行相应的系统操作。

    Parameters
    ----------
    cooldown : float
        动作冷却时间（秒），防止重复触发。默认 1.0。
    """

    # 所有支持的动作类型及其描述
    AVAILABLE_ACTIONS = {
        # 系统控制
        "lock_screen": {"name": "锁屏", "icon": "🔒", "params": []},
        "shutdown": {"name": "关机", "icon": "⏻", "params": []},
        "restart": {"name": "重启", "icon": "🔄", "params": []},
        "hibernate": {"name": "休眠", "icon": "💤", "params": []},
        "mute": {"name": "静音", "icon": "🔇", "params": []},
        "unmute": {"name": "取消静音", "icon": "🔊", "params": []},
        # 媒体控制
        "play_pause": {"name": "播放/暂停", "icon": "▶", "params": []},
        "next_track": {"name": "下一曲", "icon": "⏭", "params": []},
        "prev_track": {"name": "上一曲", "icon": "⏮", "params": []},
        "volume_up": {"name": "音量+", "icon": "🔊", "params": ["step"]},
        "volume_down": {"name": "音量-", "icon": "🔉", "params": ["step"]},
        # 应用启动
        "open_url": {"name": "打开网址", "icon": "🌐", "params": ["url"]},
        "open_app": {"name": "打开程序", "icon": "📁", "params": ["path"]},
        "open_folder": {"name": "打开目录", "icon": "📂", "params": ["path"]},
        # 窗口管理
        "minimize_window": {"name": "最小化窗口", "icon": "📌", "params": []},
        "maximize_window": {"name": "最大化窗口", "icon": "📌", "params": []},
        "close_window": {"name": "关闭窗口", "icon": "❌", "params": []},
        "alt_tab": {"name": "切换窗口", "icon": "🔄", "params": []},
        # 键盘按键
        "send_key": {"name": "发送按键", "icon": "⌨", "params": ["key"]},
        "send_combo": {"name": "发送组合键", "icon": "⌨", "params": ["combo"]},
        # 自定义
        "send_keys": {"name": "发送快捷键", "icon": "⌨", "params": ["shortcut"]},
        "run_command": {"name": "运行命令", "icon": "💻", "params": ["cmd"]},
        "run_script": {"name": "运行脚本", "icon": "📜", "params": ["path"]},
    }

    def __init__(self, cooldown: float = 1.0):
        self.cooldown = cooldown
        self._last_execute_time: float = 0.0
        self._keyboard = None

    def _get_keyboard(self):
        """延迟初始化键盘控制器。"""
        if self._keyboard is None:
            try:
                from pynput.keyboard import Controller
                self._keyboard = Controller()
            except ImportError:
                logger.warning("pynput 未安装，键盘相关功能不可用")
        return self._keyboard

    def can_execute(self) -> bool:
        """检查是否已过冷却时间。"""
        return (time.time() - self._last_execute_time) >= self.cooldown

    def execute(self, action_type: str, params: Dict = None) -> ActionResult:
        """
        执行指定动作。

        Parameters
        ----------
        action_type : str
            动作类型标识。
        params : dict
            动作参数。

        Returns
        -------
        ActionResult
            执行结果。
        """
        if not self.can_execute():
            return ActionResult(False, "冷却中，请稍后再试", action_type)

        if action_type not in self.AVAILABLE_ACTIONS:
            return ActionResult(False, f"未知动作类型: {action_type}", action_type)

        params = params or {}
        start_time = time.time()

        try:
            # 分发执行
            handler = getattr(self, f"_exec_{action_type}", None)
            if handler:
                handler(params)
            else:
                return ActionResult(False, f"未实现的动作: {action_type}", action_type)

            self._last_execute_time = time.time()
            duration = self._last_execute_time - start_time
            logger.info(f"执行动作: {action_type} ({duration:.3f}s)")
            return ActionResult(True, f"已执行: {action_type}", action_type, duration)

        except Exception as e:
            logger.error(f"执行动作失败 [{action_type}]: {e}")
            return ActionResult(False, f"执行失败: {e}", action_type)

    def execute_chain(self, actions: List[Dict]) -> List[ActionResult]:
        """依次执行多个动作。"""
        results = []
        for action in actions:
            action_type = action.get("action_type", "")
            params = action.get("params", {})
            if action.get("enabled", True):
                result = self.execute(action_type, params)
                results.append(result)
                time.sleep(0.1)  # 动作间短暂延迟
        return results

    def get_available_actions(self) -> Dict:
        """返回所有可用动作类型及其参数定义。"""
        return self.AVAILABLE_ACTIONS

    # ------------------------------------------------------------------
    # 系统控制动作
    # ------------------------------------------------------------------

    def _exec_lock_screen(self, params: dict):
        """锁屏。"""
        ctypes.windll.user32.LockWorkStation()

    def _exec_shutdown(self, params: dict):
        """关机（60秒后）。"""
        os.system("shutdown /s /t 60")

    def _exec_restart(self, params: dict):
        """重启（60秒后）。"""
        os.system("shutdown /r /t 60")

    def _exec_hibernate(self, params: dict):
        """休眠。"""
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def _exec_mute(self, params: dict):
        """静音。"""
        self._send_media_key("mute")

    def _exec_unmute(self, params: dict):
        """取消静音。"""
        self._send_media_key("mute")

    # ------------------------------------------------------------------
    # 媒体控制动作
    # ------------------------------------------------------------------

    def _exec_play_pause(self, params: dict):
        """播放/暂停。"""
        self._send_media_key("play_pause")

    def _exec_next_track(self, params: dict):
        """下一曲。"""
        self._send_media_key("next_track")

    def _exec_prev_track(self, params: dict):
        """上一曲。"""
        self._send_media_key("prev_track")

    def _exec_volume_up(self, params: dict):
        """音量增大。"""
        step = params.get("step", 5)
        for _ in range(step):
            self._send_media_key("volume_up")
            time.sleep(0.02)

    def _exec_volume_down(self, params: dict):
        """音量减小。"""
        step = params.get("step", 5)
        for _ in range(step):
            self._send_media_key("volume_down")
            time.sleep(0.02)

    # ------------------------------------------------------------------
    # 应用启动动作
    # ------------------------------------------------------------------

    def _exec_open_url(self, params: dict):
        """打开网页。"""
        url = params.get("url", "")
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)

    def _exec_open_app(self, params: dict):
        """打开程序。"""
        path = params.get("path", "")
        if not path:
            logger.warning("open_app: No path specified")
            return

        # Expand environment variables and user home
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)

        if os.path.exists(path):
            try:
                os.startfile(path)
                logger.info(f"Opened app: {path}")
            except Exception as e:
                logger.error(f"Failed to open app: {e}")
                # Try alternative method
                try:
                    import subprocess
                    subprocess.Popen([path], shell=True)
                    logger.info(f"Opened app via subprocess: {path}")
                except Exception as e2:
                    logger.error(f"Failed to open app via subprocess: {e2}")
        else:
            logger.warning(f"open_app: Path not found: {path}")
            # Try to find the app in common locations
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", ""), path),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), path),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), path),
                os.path.join(os.environ.get("APPDATA", ""), path),
            ]
            for common_path in common_paths:
                if os.path.exists(common_path):
                    try:
                        os.startfile(common_path)
                        logger.info(f"Opened app from common path: {common_path}")
                        return
                    except Exception:
                        continue
            logger.error(f"open_app: Could not find app: {path}")

    def _exec_open_folder(self, params: dict):
        """打开文件夹。"""
        path = params.get("path", "")
        if path and os.path.exists(path):
            os.startfile(path)

    # ------------------------------------------------------------------
    # 窗口管理动作
    # ------------------------------------------------------------------

    def _exec_minimize_window(self, params: dict):
        """最小化当前窗口。"""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        except ImportError:
            # 回退方案：使用快捷键
            self._send_keys("alt+space")
            time.sleep(0.05)
            self._send_keys("n")

    def _exec_maximize_window(self, params: dict):
        """最大化/还原当前窗口。"""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        except ImportError:
            self._send_keys("alt+space")
            time.sleep(0.05)
            self._send_keys("x")

    def _exec_close_window(self, params: dict):
        """关闭当前窗口。"""
        self._send_keys("alt+f4")

    def _exec_alt_tab(self, params: dict):
        """切换窗口。"""
        self._send_keys("alt+tab")

    # ------------------------------------------------------------------
    # 自定义动作
    # ------------------------------------------------------------------

    def _exec_send_keys(self, params: dict):
        """发送键盘快捷键。"""
        shortcut = params.get("shortcut", "")
        if shortcut:
            self._send_keys(shortcut)

    def _exec_send_key(self, params: dict):
        """发送单个按键。"""
        key = params.get("key", "")
        if key:
            self._send_single_key(key)

    def _exec_send_combo(self, params: dict):
        """发送组合键。"""
        combo = params.get("combo", "")
        if combo:
            self._send_keys(combo)

    def _send_single_key(self, key_name: str):
        """发送单个按键。"""
        keyboard = self._get_keyboard()
        if keyboard is None:
            return

        from pynput.keyboard import Key, KeyCode

        # 常用按键映射
        key_map = {
            # 功能键
            "enter": Key.enter,
            "return": Key.enter,
            "space": Key.space,
            "tab": Key.tab,
            "escape": Key.esc,
            "esc": Key.esc,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "insert": Key.insert,
            "home": Key.home,
            "end": Key.end,
            "pageup": Key.page_up,
            "pagedown": Key.page_down,

            # 方向键
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,

            # 功能键
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,

            # 修饰键
            "ctrl": Key.ctrl_l,
            "control": Key.ctrl_l,
            "alt": Key.alt_l,
            "shift": Key.shift_l,
            "win": Key.cmd_l,
            "super": Key.cmd_l,
            "meta": Key.cmd_l,

            # 其他
            "capslock": Key.caps_lock,
            "numlock": Key.num_lock,
            "scrolllock": Key.scroll_lock,
            "printscreen": Key.print_screen,
            "pause": Key.pause,

            # 媒体键
            "media_play_pause": Key.media_play_pause,
            "media_next": Key.media_next,
            "media_previous": Key.media_previous,
            "media_volume_up": Key.media_volume_up,
            "media_volume_down": Key.media_volume_down,
            "media_volume_mute": Key.media_volume_mute,
        }

        key_lower = key_name.lower().strip()
        if key_lower in key_map:
            key = key_map[key_lower]
            keyboard.press(key)
            keyboard.release(key)
        elif len(key_lower) == 1:
            # 单个字符
            keyboard.press(key_lower)
            keyboard.release(key_lower)
        else:
            logger.warning(f"Unknown key: {key_name}")

    def _exec_run_command(self, params: dict):
        """执行命令行。"""
        cmd = params.get("cmd", "")
        if cmd:
            subprocess.Popen(cmd, shell=True)

    def _exec_run_script(self, params: dict):
        """运行脚本文件。"""
        path = params.get("path", "")
        if path and os.path.exists(path):
            os.startfile(path)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _send_media_key(self, key_type: str):
        """发送媒体控制按键。"""
        keyboard = self._get_keyboard()
        if keyboard is None:
            return

        from pynput.keyboard import Key
        key_map = {
            "play_pause": Key.media_play_pause,
            "next_track": Key.media_next,
            "prev_track": Key.media_previous,
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "mute": Key.media_volume_mute,
        }
        key = key_map.get(key_type)
        if key:
            keyboard.press(key)
            keyboard.release(key)

    def _send_keys(self, shortcut: str):
        """发送组合快捷键，如 'ctrl+c', 'alt+f4'。"""
        keyboard = self._get_keyboard()
        if keyboard is None:
            return

        from pynput.keyboard import Key, KeyCode

        key_map = {
            "ctrl": Key.ctrl_l, "control": Key.ctrl_l,
            "alt": Key.alt_l, "shift": Key.shift_l,
            "tab": Key.tab, "enter": Key.enter,
            "space": Key.space, "esc": Key.esc, "escape": Key.esc,
            "f4": Key.f4, "f11": Key.f11,
            "up": Key.up, "down": Key.down,
            "left": Key.left, "right": Key.right,
            "backspace": Key.backspace, "delete": Key.delete,
            "win": Key.cmd_l, "super": Key.cmd_l,
        }

        parts = [p.strip().lower() for p in shortcut.split("+")]
        keys_to_press = []

        for part in parts:
            if part in key_map:
                keys_to_press.append(key_map[part])
            elif len(part) == 1:
                keys_to_press.append(KeyCode.from_char(part))

        # 按下所有键
        for key in keys_to_press:
            keyboard.press(key)
        # 释放所有键（反序）
        for key in reversed(keys_to_press):
            keyboard.release(key)
