"""
摄像头管理模块
提供线程安全的摄像头捕获、帧获取、设备管理等功能。
依赖: opencv-python
"""

import time
import logging
import threading
from typing import Optional, Callable, Tuple

import cv2
import numpy as np

logger = logging.getLogger("GestureMaster")


class CameraManager:
    """
    摄像头管理器。
    在独立线程中持续读取帧，提供线程安全的帧获取接口。

    Parameters
    ----------
    device_id : int
        摄像头设备编号，默认 0。
    resolution : tuple
        分辨率 (宽, 高)，默认 (640, 480)。
    fps : int
        目标帧率，默认 30。
    """

    def __init__(
        self,
        device_id: int = 0,
        resolution: Tuple[int, int] = (640, 480),
        fps: int = 30,
    ):
        self.device_id = device_id
        self.resolution = resolution
        self.fps = fps

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._start_time = 0.0
        self._error: Optional[str] = None
        self._frame_callback: Optional[Callable] = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 50  # 连续读取失败阈值

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps_actual(self) -> float:
        """实际帧率。"""
        elapsed = time.time() - self._start_time
        if elapsed <= 0:
            return 0.0
        return self._frame_count / elapsed

    @property
    def error(self) -> Optional[str]:
        return self._error

    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """设置帧回调函数，每获取一帧都会调用。"""
        self._frame_callback = callback

    def start(self) -> bool:
        """启动摄像头捕获。返回是否成功。"""
        if self._running:
            return True

        try:
            self._cap = cv2.VideoCapture(self.device_id)
            if not self._cap.isOpened():
                self._error = f"无法打开摄像头 {self.device_id}，请检查摄像头是否被其他程序占用"
                logger.error(self._error)
                return False

            # 设置分辨率和帧率
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)

            # 等待摄像头预热，尝试多次读取
            logger.info(f"正在启动摄像头 {self.device_id}...")
            max_retries = 10
            for i in range(max_retries):
                ret, test_frame = self._cap.read()
                if ret and test_frame is not None:
                    logger.info(f"摄像头预热成功 (尝试 {i+1}/{max_retries})")
                    break
                time.sleep(0.1)
            else:
                # 所有重试都失败
                self._error = f"摄像头 {self.device_id} 无法读取画面（已尝试 {max_retries} 次）"
                logger.error(self._error)
                self._cap.release()
                self._cap = None
                return False

            self._running = True
            self._error = None
            self._frame_count = 0
            self._start_time = time.time()
            self._consecutive_failures = 0

            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info(f"摄像头 {self.device_id} 已启动 ({self.resolution[0]}x{self.resolution[1]} @ {self.fps}fps)")
            return True

        except Exception as e:
            self._error = f"启动摄像头失败: {e}"
            logger.error(self._error)
            return False

    def stop(self):
        """停止摄像头捕获。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._release_camera()
        with self._lock:
            self._frame = None
        logger.info("摄像头已停止")

    def _release_camera(self):
        """安全释放摄像头资源。"""
        try:
            if self._cap:
                self._cap.release()
                self._cap = None
        except Exception as e:
            logger.warning(f"释放摄像头资源时出错: {e}")

    def get_frame(self) -> Optional[np.ndarray]:
        """获取最新一帧（线程安全）。返回 BGR 图像或 None。"""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def _capture_loop(self):
        """摄像头捕获循环（在独立线程中运行）。"""
        frame_interval = 1.0 / self.fps

        while self._running:
            try:
                if self._cap is None or not self._cap.isOpened():
                    self._error = "摄像头连接断开"
                    logger.error(self._error)
                    self._running = False
                    break

                ret, frame = self._cap.read()
                if not ret or frame is None:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self._max_consecutive_failures:
                        self._error = f"摄像头连续 {self._max_consecutive_failures} 次读取失败"
                        logger.error(self._error)
                        self._running = False
                        break
                    time.sleep(0.01)
                    continue

                # 重置失败计数
                self._consecutive_failures = 0

                # 镜像翻转
                frame = cv2.flip(frame, 1)

                with self._lock:
                    self._frame = frame
                    self._frame_count += 1

                # 调用回调
                if self._frame_callback:
                    try:
                        self._frame_callback(frame)
                    except Exception as e:
                        logger.warning(f"帧回调异常: {e}")

                # 控制帧率
                time.sleep(frame_interval)

            except Exception as e:
                logger.warning(f"摄像头捕获循环异常: {e}")
                time.sleep(0.1)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def enumerate_cameras(max_id: int = 5) -> list:
    """枚举可用的摄像头设备。返回 [(device_id, name), ...]。"""
    cameras = []
    for i in range(max_id):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 尝试读取一帧确认摄像头可用
                ret, _ = cap.read()
                if ret:
                    cameras.append((i, f"摄像头 {i}"))
                cap.release()
        except Exception as e:
            logger.warning(f"枚举摄像头 {i} 时出错: {e}")
    return cameras
