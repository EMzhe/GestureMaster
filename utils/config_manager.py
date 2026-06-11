"""
配置管理模块
提供 JSON 配置文件的读写、管理手势绑定和应用设置。
"""

import os
import json
import uuid
import shutil
import threading
from typing import Any, Dict, List, Optional
from pathlib import Path


# 默认配置
DEFAULT_CONFIG = {
    "camera": {
        "device_id": 0,
        "resolution": [640, 480],
        "fps": 30,
    },
    "detection": {
        "confidence": 0.70,
        "max_hands": 1,
        "gesture_cooldown": 1.5,
        "history_size": 30,
        "sequence_window": 2.0,
        "stability_buffer": 4,
    },
    "bindings": [
        {
            "id": "default_fist",
            "gesture_type": "static",
            "gesture": "fist",
            "actions": [{"type": "lock_screen", "params": {}}],
            "enabled": True,
            "description": "握拳锁屏",
            "cooldown": 1.0,
        },
        {
            "id": "default_thumbs_up",
            "gesture_type": "static",
            "gesture": "thumbs_up",
            "actions": [{"type": "open_url", "params": {"url": "https://www.bilibili.com"}}],
            "enabled": True,
            "description": "竖大拇指打开B站",
            "cooldown": 1.5,
        },
        {
            "id": "default_peace",
            "gesture_type": "static",
            "gesture": "peace",
            "actions": [{"type": "mute", "params": {}}],
            "enabled": True,
            "description": "比耶静音",
            "cooldown": 1.0,
        },
    ],
    "sequences": [],
    "ui": {
        "theme": "dark",
        "language": "zh_CN",
        "minimize_to_tray": True,
        "start_minimized": False,
        "show_detection_overlay": True,
    },
    "advanced": {
        "auto_start": False,
        "log_level": "INFO",
        "max_log_size_mb": 10,
    },
}


class ConfigManager:
    """
    配置管理器。
    线程安全的 JSON 配置文件管理。

    Parameters
    ----------
    config_path : str
        配置文件路径，默认为程序目录下的 config.json。
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = str(base_dir / "config.json")
        self.config_path = config_path
        self._config: Dict = {}
        self._lock = threading.Lock()
        self.load()

    def load(self):
        """加载配置文件。如果文件不存在则创建默认配置。"""
        with self._lock:
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                    # 合并缺失的默认值
                    self._merge_defaults(self._config, DEFAULT_CONFIG)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"配置文件加载失败: {e}，使用默认配置")
                    self._config = self._deep_copy(DEFAULT_CONFIG)
            else:
                self._config = self._deep_copy(DEFAULT_CONFIG)
                self._save_to_file()

    def save(self):
        """保存当前配置到文件。"""
        with self._lock:
            self._save_to_file()

    def _save_to_file(self):
        """内部保存方法（调用时需已持有锁）。"""
        try:
            os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"配置文件保存失败: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点分路径）。
        例如: get("camera.device_id")
        """
        with self._lock:
            keys = key_path.split(".")
            value = self._config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value

    def set(self, key_path: str, value: Any):
        """
        设置配置值（支持点分路径）。
        例如: set("camera.device_id", 1)
        """
        with self._lock:
            keys = key_path.split(".")
            config = self._config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value

    def get_bindings(self) -> List[Dict]:
        """获取所有手势绑定。"""
        with self._lock:
            return self._config.get("bindings", [])

    def add_binding(self, binding: Dict) -> str:
        """添加一个新的手势绑定。返回绑定 ID。"""
        with self._lock:
            if "id" not in binding:
                binding["id"] = uuid.uuid4().hex[:8]
            self._config.setdefault("bindings", []).append(binding)
            return binding["id"]

    def remove_binding(self, binding_id: str) -> bool:
        """删除指定 ID 的手势绑定。"""
        with self._lock:
            bindings = self._config.get("bindings", [])
            for i, b in enumerate(bindings):
                if b.get("id") == binding_id:
                    bindings.pop(i)
                    return True
            return False

    def update_binding(self, binding_id: str, updates: Dict) -> bool:
        """更新指定 ID 的手势绑定。"""
        with self._lock:
            bindings = self._config.get("bindings", [])
            for b in bindings:
                if b.get("id") == binding_id:
                    b.update(updates)
                    return True
            return False

    def get_sequences(self) -> List[Dict]:
        """获取所有手势序列。"""
        with self._lock:
            return self._config.get("sequences", [])

    def add_sequence(self, sequence: Dict) -> str:
        """添加手势序列。返回序列 ID。"""
        with self._lock:
            if "id" not in sequence:
                sequence["id"] = uuid.uuid4().hex[:8]
            self._config.setdefault("sequences", []).append(sequence)
            return sequence["id"]

    def remove_sequence(self, sequence_id: str) -> bool:
        """删除手势序列。"""
        with self._lock:
            sequences = self._config.get("sequences", [])
            for i, s in enumerate(sequences):
                if s.get("id") == sequence_id:
                    sequences.pop(i)
                    return True
            return False

    def get_all(self) -> Dict:
        """获取完整配置的副本。"""
        with self._lock:
            return self._deep_copy(self._config)

    def reset_to_defaults(self):
        """重置为默认配置。"""
        with self._lock:
            self._config = self._deep_copy(DEFAULT_CONFIG)
            self._save_to_file()

    def export_config(self, path: str):
        """导出配置到指定文件。"""
        with self._lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

    def import_config(self, path: str) -> bool:
        """从指定文件导入配置。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            with self._lock:
                self._config = imported
                self._merge_defaults(self._config, DEFAULT_CONFIG)
                self._save_to_file()
            return True
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False

    def _merge_defaults(self, config: dict, defaults: dict):
        """递归合并缺失的默认值。"""
        for key, value in defaults.items():
            if key not in config:
                config[key] = self._deep_copy(value)
            elif isinstance(value, dict) and isinstance(config[key], dict):
                self._merge_defaults(config[key], value)

    @staticmethod
    def _deep_copy(obj):
        """简单深拷贝。"""
        if isinstance(obj, dict):
            return {k: ConfigManager._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ConfigManager._deep_copy(item) for item in obj]
        return obj
