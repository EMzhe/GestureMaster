"""
手势分类器模块
支持静态手势、动态手势和手势序列三种识别模式。
依赖: numpy, mediapipe (通过 hand_detector 获取关键点)
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

import numpy as np

from core.hand_detector import Landmark, FINGER_NAMES


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class GestureResult:
    """手势识别结果。"""
    gesture: str = "none"           # 手势名称
    gesture_type: str = "static"    # "static" / "dynamic" / "sequence"
    confidence: float = 0.0         # 置信度 0.0 ~ 1.0
    description: str = ""           # 中文描述


# ---------------------------------------------------------------------------
# 手势名称常量
# ---------------------------------------------------------------------------

GESTURE_NAMES = {
    "fist": ("握拳", "✊"),
    "open_palm": ("张开手掌", "🖐"),
    "thumbs_up": ("竖大拇指", "👍"),
    "thumbs_down": ("大拇指朝下", "👎"),
    "peace": ("比耶", "✌"),
    "ok": ("OK手势", "👌"),
    "pointing_up": ("食指朝上", "☝"),
    "three_fingers": ("三指", "🤟"),
    "rock": ("摇滚手势", "🤘"),
    "pinch": ("捏合", "🤏"),
    "pointing_left": ("指向左", "👈"),
    "pointing_right": ("指向右", "👉"),
    "wave": ("挥手", "👋"),
    "circle": ("画圈", "⭕"),
    "swipe_left": ("左滑", "⬅"),
    "swipe_right": ("右滑", "➡"),
    "swipe_up": ("上滑", "⬆"),
    "swipe_down": ("下滑", "⬇"),
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _is_finger_extended(landmarks: List[Landmark], finger: str) -> bool:
    """
    判断手指是否伸展。
    使用简单可靠的位置判断。
    """
    tips = {"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}
    tip_idx = tips[finger]

    if finger == "thumb":
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]

        # 拇指尖到 MCP 的距离 vs IP 到 MCP 的距离
        dist_tip_mcp = math.hypot(thumb_tip.x - thumb_mcp.x, thumb_tip.y - thumb_mcp.y)
        dist_ip_mcp = math.hypot(thumb_ip.x - thumb_mcp.x, thumb_ip.y - thumb_mcp.y)

        # 伸展判断：指尖远离 MCP
        return dist_tip_mcp > dist_ip_mcp * 1.2
    else:
        pip_map = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}
        mcp_map = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}

        tip = landmarks[tip_idx]
        pip = landmarks[pip_map[finger]]
        mcp = landmarks[mcp_map[finger]]

        # 简单判断：指尖在 PIP 关节上方
        return tip.y < pip.y


def _distance(a: Landmark, b: Landmark) -> float:
    """计算两个关键点的欧氏距离。"""
    return math.hypot(a.x - b.x, a.y - b.y)


def _angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """计算三点夹角（度）。"""
    ba = np.array([a.x - b.x, a.y - b.y])
    bc = np.array([c.x - b.x, c.y - b.y])
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return 0.0
    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = float(np.clip(cosine, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


# ---------------------------------------------------------------------------
# 手势分类器
# ---------------------------------------------------------------------------

class GestureClassifier:
    """
    手势分类器。
    支持静态手势、动态手势和手势序列的识别。

    Parameters
    ----------
    confidence_threshold : float
        静态手势置信度阈值，默认 0.7。
    history_size : int
        动态手势分析的历史帧数，默认 30。
    sequence_window : float
        手势序列的时间窗口（秒），默认 2.0。
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        history_size: int = 30,
        sequence_window: float = 2.0,
    ):
        self.confidence_threshold = confidence_threshold
        self.history_size = history_size
        self.sequence_window = sequence_window

        # 关键点历史（用于动态手势分析）
        self._history: deque = deque(maxlen=history_size)
        self._gesture_history: deque = deque(maxlen=50)
        self._last_update_time: float = 0.0

    def update(self, landmarks: List[Landmark]):
        """添加一帧关键点到历史记录。"""
        now = time.time()
        self._last_update_time = now
        # 存储手腕位置和时间戳
        wrist = landmarks[0]
        self._history.append({
            "time": now,
            "wrist_x": wrist.x,
            "wrist_y": wrist.y,
            "landmarks": landmarks,
        })

    def classify_static(self, landmarks: List[Landmark]) -> GestureResult:
        """
        分类静态手势。
        使用简单可靠的判断逻辑。
        """
        # 获取各手指伸展状态
        fingers = {}
        for fname in FINGER_NAMES:
            fingers[fname] = _is_finger_extended(landmarks, fname)

        extended_count = sum(fingers.values())

        # 关键点
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]

        # 拇指尖到食指尖的距离
        thumb_index_dist = _distance(thumb_tip, index_tip)

        # ============================================================
        # 手势判断（按优先级排序）
        # ============================================================

        # --- 1. 握拳：所有手指弯曲 ---
        if extended_count == 0:
            return GestureResult("fist", "static", 0.95, "握拳")

        # --- 2. 张开手掌：所有手指伸展 ---
        if extended_count == 5:
            return GestureResult("open_palm", "static", 0.95, "张开手掌")

        # --- 3. 竖大拇指：仅拇指伸展 ---
        if fingers["thumb"] and extended_count == 1:
            # 判断拇指朝向
            if thumb_tip.y < thumb_ip.y:
                return GestureResult("thumbs_up", "static", 0.9, "竖大拇指")
            else:
                return GestureResult("thumbs_down", "static", 0.9, "大拇指朝下")

        # --- 4. 比耶：食指和中指伸展 ---
        if (fingers["index"] and fingers["middle"] and
            not fingers["ring"] and not fingers["pinky"]):
            return GestureResult("peace", "static", 0.9, "比耶")

        # --- 5. 食指朝上：仅食指伸展 ---
        if (fingers["index"] and not fingers["middle"] and
            not fingers["ring"] and not fingers["pinky"] and
            not fingers["thumb"]):
            # 判断方向
            if index_tip.y < index_mcp.y:
                return GestureResult("pointing_up", "static", 0.9, "食指朝上")
            elif index_tip.x < index_mcp.x - 0.05:
                return GestureResult("pointing_left", "static", 0.85, "指向左")
            elif index_tip.x > index_mcp.x + 0.05:
                return GestureResult("pointing_right", "static", 0.85, "指向右")

        # --- 6. OK 手势：拇指和食指形成圆圈 ---
        if thumb_index_dist < 0.06 and fingers["middle"]:
            return GestureResult("ok", "static", 0.9, "OK手势")

        # --- 7. 捏合：拇指和食指靠近 ---
        if thumb_index_dist < 0.05 and not fingers["middle"]:
            return GestureResult("pinch", "static", 0.85, "捏合")

        # --- 8. 三指：拇指+食指+中指伸展 ---
        if (fingers["thumb"] and fingers["index"] and fingers["middle"] and
            not fingers["ring"] and not fingers["pinky"]):
            return GestureResult("three_fingers", "static", 0.85, "三指")

        # --- 9. 摇滚：食指和小指伸展 ---
        if (fingers["index"] and fingers["pinky"] and
            not fingers["middle"] and not fingers["ring"]):
            return GestureResult("rock", "static", 0.85, "摇滚手势")

        # --- 10. 食指指向（带拇指） ---
        if (fingers["index"] and not fingers["middle"] and
            not fingers["ring"] and not fingers["pinky"]):
            if index_tip.x < index_mcp.x - 0.05:
                return GestureResult("pointing_left", "static", 0.8, "指向左")
            elif index_tip.x > index_mcp.x + 0.05:
                return GestureResult("pointing_right", "static", 0.8, "指向右")

        return GestureResult("none", "static", 0.0, "未识别")

    def classify_dynamic(self) -> Optional[GestureResult]:
        """
        分析历史轨迹，识别动态手势。
        需要先通过 update() 积累足够帧数。
        """
        if len(self._history) < 10:
            return None

        recent = list(self._history)[-30:]
        xs = [f["wrist_x"] for f in recent]
        ys = [f["wrist_y"] for f in recent]
        times = [f["time"] for f in recent]

        duration = times[-1] - times[0]
        if duration < 0.3:
            return None

        dx = xs[-1] - xs[0]
        dy = ys[-1] - ys[0]
        dist = math.hypot(dx, dy)
        speed = dist / duration if duration > 0 else 0

        # --- 挥手: 左右方向反复变化 ---
        x_changes = 0
        for i in range(2, len(xs)):
            if (xs[i] - xs[i-1]) * (xs[i-1] - xs[i-2]) < 0:
                x_changes += 1
        if x_changes >= 4 and speed > 0.1:
            return GestureResult("wave", "dynamic", 0.8, "挥手")

        # --- 画圈: 轨迹近似圆形 ---
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        radii = [math.hypot(x - cx, y - cy) for x, y in zip(xs, ys)]
        avg_r = sum(radii) / len(radii)
        if avg_r > 0.05:
            variance = sum((r - avg_r) ** 2 for r in radii) / len(radii)
            if variance < 0.002 and dist < avg_r * 3:
                return GestureResult("circle", "dynamic", 0.75, "画圈")

        # --- 滑动: 快速方向性移动 ---
        if speed > 0.3 and dist > 0.15:
            angle = math.degrees(math.atan2(-dy, dx))
            if -45 <= angle < 45:
                return GestureResult("swipe_right", "dynamic", 0.85, "右滑")
            elif 45 <= angle < 135:
                return GestureResult("swipe_up", "dynamic", 0.85, "上滑")
            elif angle >= 135 or angle < -135:
                return GestureResult("swipe_left", "dynamic", 0.85, "左滑")
            else:
                return GestureResult("swipe_down", "dynamic", 0.85, "下滑")

        return None

    def classify_sequence(self, sequences: Dict) -> Optional[str]:
        """
        检查手势序列是否匹配。
        sequences: {"sequence_id": {"gestures": ["fist", "open_palm", "fist"], "timeout": 2.0}}
        """
        if not self._gesture_history:
            return None

        now = time.time()
        for seq_id, seq_config in sequences.items():
            expected = seq_config.get("gestures", [])
            timeout = seq_config.get("timeout", self.sequence_window)
            if not expected:
                continue

            # 从历史中查找匹配的序列
            recent_gestures = [
                (g, t) for g, t in self._gesture_history
                if now - t <= timeout
            ]

            if len(recent_gestures) < len(expected):
                continue

            # 检查是否按序匹配
            match_idx = 0
            for gesture_name, _ in recent_gestures:
                if match_idx < len(expected) and gesture_name == expected[match_idx]:
                    match_idx += 1
                if match_idx == len(expected):
                    return seq_id

        return None

    def classify(
        self,
        landmarks: List[Landmark],
        sequences: Optional[Dict] = None,
    ) -> GestureResult:
        """
        综合分类入口。
        优先级: 序列 > 动态 > 静态。
        """
        self.update(landmarks)

        # 静态识别
        static_result = self.classify_static(landmarks)

        # 记录到手势历史
        if static_result.gesture != "none":
            self._gesture_history.append((static_result.gesture, time.time()))

        # 检查手势序列
        if sequences:
            seq_match = self.classify_sequence(sequences)
            if seq_match:
                return GestureResult(seq_match, "sequence", 0.9, f"序列: {seq_match}")

        # 检查动态手势
        dynamic_result = self.classify_dynamic()
        if dynamic_result and dynamic_result.confidence > static_result.confidence:
            return dynamic_result

        return static_result

    def reset(self):
        """重置历史记录。"""
        self._history.clear()
        self._gesture_history.clear()
