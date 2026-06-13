"""
手势识别 - 手部检测模块
基于 MediaPipe Hands 实现手部关键点检测，
提供手指计数、手指伸展判断、手指角度计算等辅助功能。
依赖: mediapipe, opencv-python, numpy
"""

import math
import logging
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp

logger = logging.getLogger("GestureMaster")


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

class Landmark:
    """单个关键点，包含 x / y / z 归一化坐标。"""

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __repr__(self) -> str:
        return f"Landmark(x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f})"


class HandResult:
    """
    单只手的检测结果。
    Attributes:
        landmarks : 长度为 21 的关键点列表，顺序与 MediaPipe 定义一致。
        handedness: "Left" 或 "Right"（基于摄像头画面，非真实左右手）。
        score     : 手部检测置信度。
    """

    def __init__(
        self,
        landmarks: List[Landmark],
        handedness: str = "Right",
        score: float = 0.0,
    ):
        self.landmarks = landmarks
        self.handedness = handedness
        self.score = score

    def __len__(self) -> int:
        return len(self.landmarks)

    def __repr__(self) -> str:
        return (
            f"HandResult(handedness={self.handedness}, "
            f"score={self.score:.2f}, landmarks={len(self.landmarks)})"
        )


# ---------------------------------------------------------------------------
# 手指关键点索引（MediaPipe Hands 21 点定义）
# ---------------------------------------------------------------------------
# 0  - 手腕 (WRIST)
# 1  - 拇指近端指骨 (THUMB_CMC)
# 2  - 拇指中间指骨 (THUMB_MCP)
# 3  - 拇指远端指骨 (THUMB_IP)
# 4  - 拇指尖 (THUMB_TIP)
# 5  - 食指近端指骨 (INDEX_FINGER_MCP)
# 6  - 食指中间指骨 (INDEX_FINGER_PIP)
# 7  - 食指远端指骨 (INDEX_FINGER_DIP)
# 8  - 食指尖 (INDEX_FINGER_TIP)
# 9  - 中指近端指骨 (MIDDLE_FINGER_MCP)
# 10 - 中指中间指骨 (MIDDLE_FINGER_PIP)
# 11 - 中指远端指骨 (MIDDLE_FINGER_DIP)
# 12 - 中指尖 (MIDDLE_FINGER_TIP)
# 13 - 无名指近端指骨 (RING_FINGER_MCP)
# 14 - 无名指中间指骨 (RING_FINGER_PIP)
# 15 - 无名指远端指骨 (RING_FINGER_DIP)
# 16 - 无名指尖 (RING_FINGER_TIP)
# 17 - 小指近端指骨 (PINKY_MCP)
# 18 - 小指中间指骨 (PINKY_PIP)
# 19 - 小指远端指骨 (PINKY_DIP)
# 20 - 小指尖 (PINKY_TIP)

# 每根手指的关键点三元组: (近端, 中间, 远端/指尖)
_FINGER_TIPS = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}

# 手指对应的三个关键点索引，用于判断是否伸展
_FINGER_PIP_TIP = {
    "thumb": (2, 3, 4),
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

# 用于计算手指弯曲角度的三组关键点 (关节A, 关节B, 关节C)
_FINGER_ANGLE_INDICES = {
    "thumb": (1, 2, 4),
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

# 五根手指名称的固定顺序
FINGER_NAMES: List[str] = ["thumb", "index", "middle", "ring", "pinky"]


# ---------------------------------------------------------------------------
# 辅助数学函数
# ---------------------------------------------------------------------------

def _angle_between_three_points(
    a: Landmark, b: Landmark, c: Landmark
) -> float:
    """
    计算三个点形成的夹角（以 b 为顶点），返回角度值（度）。
    使用向量 BA 和 BC 的点积公式。
    """
    ba = np.array([a.x - b.x, a.y - b.y, a.z - b.z], dtype=np.float64)
    bc = np.array([c.x - b.x, c.y - b.y, c.z - b.z], dtype=np.float64)

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return 0.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    # 防止浮点误差导致 arccos 域越界
    cosine = float(np.clip(cosine, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


# ---------------------------------------------------------------------------
# HandDetector 主类
# ---------------------------------------------------------------------------

class HandDetector:
    """
    基于 MediaPipe Hands 的手部检测器。

    Parameters
    ----------
    max_hands : int
        最大同时检测手数，默认 2。
    detection_confidence : float
        检测置信度阈值，默认 0.7。
    tracking_confidence : float
        追踪置信度阈值，默认 0.5。
    """

    def __init__(
        self,
        max_hands: int = 2,
        detection_confidence: float = 0.7,
        tracking_confidence: float = 0.5,
    ):
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence

        # 初始化 MediaPipe 组件
        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_drawing_styles = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence,
        )

    # ------------------------------------------------------------------
    # 核心检测方法
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> List[HandResult]:
        """
        对输入图像进行手部关键点检测。

        Parameters
        ----------
        image : np.ndarray
            BGR 格式的图像（OpenCV 默认格式）。

        Returns
        -------
        List[HandResult]
            检测到的手部结果列表，每只手包含 21 个关键点和手性信息。
            如果未检测到手，返回空列表。
        """
        if image is None or image.size == 0:
            return []

        try:
            # 确保图像是连续的
            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)

            # MediaPipe 要求 RGB 输入
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            rgb_image.flags.writeable = False
            results = self._hands.process(rgb_image)
            rgb_image.flags.writeable = True

            hand_results: List[HandResult] = []

            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness_info in zip(
                    results.multi_hand_landmarks, results.multi_handedness
                ):
                    # 提取 21 个关键点
                    landmarks: List[Landmark] = []
                    for lm in hand_landmarks.landmark:
                        landmarks.append(Landmark(lm.x, lm.y, lm.z))

                    # 获取手性（Left / Right）和置信度
                    handedness = handedness_info.classification[0]
                    hand_label = handedness.label  # "Left" 或 "Right"
                    hand_score = handedness.score

                    hand_results.append(
                        HandResult(
                            landmarks=landmarks,
                            handedness=hand_label,
                            score=hand_score,
                        )
                    )

            return hand_results

        except Exception as e:
            logger.warning(f"手部检测异常: {e}")
            return []

    # ------------------------------------------------------------------
    # 可视化方法
    # ------------------------------------------------------------------

    # 分指颜色（BGR）：拇指=红, 食指=绿, 中指=蓝, 无名指=紫, 小指=青
    _FINGER_COLORS = {
        "thumb":  (0, 0, 255),     # 红
        "index":  (0, 200, 0),     # 绿
        "middle": (255, 150, 0),   # 蓝
        "ring":   (200, 0, 200),   # 紫
        "pinky":  (255, 200, 0),   # 青
    }

    # 每根手指的关键点索引（含掌指关节）
    _FINGER_LANDMARK_INDICES = {
        "thumb":  [1, 2, 3, 4],
        "index":  [5, 6, 7, 8],
        "middle": [9, 10, 11, 12],
        "ring":   [13, 14, 15, 16],
        "pinky":  [17, 18, 19, 20],
    }

    # 骨架连接线定义（每条线两端的关键点索引）
    _CONNECTIONS = [
        # 手腕到各手指根部
        (0, 1), (0, 5), (0, 9), (0, 13), (0, 17),
        # 拇指
        (1, 2), (2, 3), (3, 4),
        # 食指
        (5, 6), (6, 7), (7, 8),
        # 中指
        (9, 10), (10, 11), (11, 12),
        # 无名指
        (13, 14), (14, 15), (15, 16),
        # 小指
        (17, 18), (18, 19), (19, 20),
        # 掌心连接
        (5, 9), (9, 13), (13, 17),
    ]

    def draw_landmarks(
        self,
        image: np.ndarray,
        hand_results: List[HandResult],
        draw_connections: bool = True,
        draw_indices: bool = True,
    ) -> np.ndarray:
        """
        在图像上绘制手部关键点和连接线。

        Parameters
        ----------
        image : np.ndarray
            要绘制的原始图像（BGR）。
        hand_results : List[HandResult]
            detect() 返回的检测结果。
        draw_connections : bool
            是否绘制关键点之间的连接线，默认 True。
        draw_indices : bool
            是否在关键点旁标注编号，默认 True。

        Returns
        -------
        np.ndarray
            绘制了关键点标注后的图像副本。
        """
        annotated = image.copy()

        for hand in hand_results:
            h, w, _ = annotated.shape

            # 构建像素坐标映射
            pts = {}
            for i, lm in enumerate(hand.landmarks):
                pts[i] = (int(lm.x * w), int(lm.y * h))

            if draw_connections:
                # 按手指分色绘制骨架连接线
                # 先画掌心连线（灰色）
                palm_connections = [(0, 1), (0, 5), (0, 9), (0, 13), (0, 17), (5, 9), (9, 13), (13, 17)]
                for i_start, i_end in palm_connections:
                    if i_start in pts and i_end in pts:
                        cv2.line(annotated, pts[i_start], pts[i_end], (180, 180, 180), 2)

                # 再画每根手指的连线（分色）
                finger_connections = {
                    "thumb":  [(1, 2), (2, 3), (3, 4)],
                    "index":  [(5, 6), (6, 7), (7, 8)],
                    "middle": [(9, 10), (10, 11), (11, 12)],
                    "ring":   [(13, 14), (14, 15), (15, 16)],
                    "pinky":  [(17, 18), (18, 19), (19, 20)],
                }
                for finger, conns in finger_connections.items():
                    color = self._FINGER_COLORS[finger]
                    for i_start, i_end in conns:
                        if i_start in pts and i_end in pts:
                            cv2.line(annotated, pts[i_start], pts[i_end], color, 2)

            # 绘制关键点（分指颜色 + 白色圆心）
            for finger, indices in self._FINGER_LANDMARK_INDICES.items():
                color = self._FINGER_COLORS[finger]
                for idx in indices:
                    if idx in pts:
                        cv2.circle(annotated, pts[idx], 7, color, -1)
                        cv2.circle(annotated, pts[idx], 3, (255, 255, 255), -1)

            # 手腕点（黄色）
            if 0 in pts:
                cv2.circle(annotated, pts[0], 8, (0, 255, 255), -1)
                cv2.circle(annotated, pts[0], 4, (255, 255, 255), -1)

            # 关键点编号标注
            if draw_indices:
                for i, lm in enumerate(hand.landmarks):
                    if i in pts:
                        px, py = pts[i]
                        # 编号放在点的右上方偏移
                        tx, ty = px + 10, py - 10
                        # 背景色提高可读性
                        cv2.putText(
                            annotated, str(i), (tx + 1, ty + 1),
                            cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 0), 2,
                        )
                        cv2.putText(
                            annotated, str(i), (tx, ty),
                            cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1,
                        )

            # 在手腕上方标注手性和置信度
            if 0 in pts:
                cx, cy = pts[0]
                label = f"{hand.handedness} ({hand.score:.0%})"
                # 阴影
                cv2.putText(
                    annotated, label, (cx - 29, cy - 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3,
                )
                cv2.putText(
                    annotated, label, (cx - 30, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                )

        return annotated

    @staticmethod
    def _create_mp_landmark_list(
        landmarks: List[Landmark],
    ):
        """将自定义 Landmark 列表转换为 MediaPipe 的 protobuf 格式。"""
        from mediapipe.framework.formats import landmark_pb2

        landmark_list = landmark_pb2.NormalizedLandmarkList()
        for lm in landmarks:
            new_landmark = landmark_list.landmark.add()
            new_landmark.x = lm.x
            new_landmark.y = lm.y
            new_landmark.z = lm.z
        return landmark_list

    # ------------------------------------------------------------------
    # 辅助分析方法（静态/类方法，可独立使用）
    # ------------------------------------------------------------------

    @staticmethod
    def is_finger_extended(landmarks: List[Landmark], finger: str) -> bool:
        """
        判断指定手指是否伸展（伸直）。

        判断逻辑:
        - 对于拇指: 使用拇指尖与拇指 IP 关节的横向距离来判断。
        - 对于其他四指: 比较指尖 y 坐标与 PIP 关节 y 坐标，
          指尖在 PIP 关节上方（y 更小）则视为伸展。
        """
        if finger not in _FINGER_PIP_TIP:
            raise ValueError(
                f"未知手指名称: {finger}，"
                f"可选值: {list(_FINGER_PIP_TIP.keys())}"
            )

        tip_idx = _FINGER_TIPS[finger]

        if finger == "thumb":
            # 拇指: 比较指尖 x 与 IP 关节 x 的距离（考虑左右手差异）
            thumb_tip = landmarks[tip_idx]
            thumb_ip = landmarks[3]
            thumb_mcp = landmarks[2]
            dist_tip_mcp = math.hypot(
                thumb_tip.x - thumb_mcp.x, thumb_tip.y - thumb_mcp.y
            )
            dist_ip_mcp = math.hypot(
                thumb_ip.x - thumb_mcp.x, thumb_ip.y - thumb_mcp.y
            )
            return dist_tip_mcp > dist_ip_mcp * 1.2
        else:
            # 其他手指: 指尖 y < PIP 关节 y 即为伸展（图像坐标系 y 轴向下）
            mcp_idx, pip_idx, _ = _FINGER_PIP_TIP[finger]
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            return tip.y < pip.y

    @staticmethod
    def finger_count(landmarks: List[Landmark]) -> int:
        """计算伸展的手指数量（0~5）。"""
        count = 0
        for finger_name in FINGER_NAMES:
            if HandDetector.is_finger_extended(landmarks, finger_name):
                count += 1
        return count

    @staticmethod
    def get_finger_angles(landmarks: List[Landmark]) -> Dict[str, float]:
        """
        计算每根手指的弯曲角度。
        角度越大表示手指越伸直（180 度为完全伸直）。
        """
        angles: Dict[str, float] = {}
        for finger_name, (a_idx, b_idx, c_idx) in _FINGER_ANGLE_INDICES.items():
            a = landmarks[a_idx]
            b = landmarks[b_idx]
            c = landmarks[c_idx]
            angles[finger_name] = _angle_between_three_points(a, b, c)
        return angles

    # ------------------------------------------------------------------
    # 资源管理
    # ------------------------------------------------------------------

    def close(self) -> None:
        """释放 MediaPipe 资源。"""
        try:
            if self._hands is not None:
                self._hands.close()
                self._hands = None
        except Exception as e:
            logger.warning(f"释放 MediaPipe 资源时出错: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 演示代码
# ---------------------------------------------------------------------------

def main():
    """演示: 打开摄像头进行实时手部检测。"""
    print("=" * 50)
    print("手势识别 - 手部检测演示")
    print("按 'q' 键退出")
    print("=" * 50)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误: 无法打开摄像头，请检查设备连接。")
        return

    with HandDetector(
        max_hands=2,
        detection_confidence=0.7,
        tracking_confidence=0.5,
    ) as detector:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("警告: 无法读取摄像头画面。")
                break

            # 镜像翻转
            frame = cv2.flip(frame, 1)

            # 检测手部
            hands = detector.detect(frame)

            # 绘制关键点
            annotated = detector.draw_landmarks(frame, hands)

            # 显示每只手的信息
            for i, hand in enumerate(hands):
                finger_num = HandDetector.finger_count(hand.landmarks)
                angles = HandDetector.get_finger_angles(hand.landmarks)

                info_text = (
                    f"Hand {i + 1}: {hand.handedness} | "
                    f"Fingers: {finger_num}/5"
                )
                cv2.putText(
                    annotated,
                    info_text,
                    (10, 30 + i * 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            # 显示检测到的手数
            cv2.putText(
                annotated,
                f"Hands: {len(hands)}",
                (10, annotated.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                1,
            )

            cv2.imshow("GestureMaster - Hand Detection", annotated)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    print("\n演示结束，资源已释放。")


if __name__ == "__main__":
    main()
