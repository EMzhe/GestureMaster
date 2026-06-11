"""
Mouse Controller Module
Control mouse with hand gestures via camera
"""
import time
import math
import logging
import threading
from typing import Optional, Tuple
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("GestureMaster")


@dataclass
class MouseConfig:
    """Mouse control configuration"""
    enabled: bool = False
    sensitivity: float = 1.5        # Mouse sensitivity
    smooth_factor: float = 0.3      # Smoothing factor (0-1)
    click_gesture: str = "pinch"    # Gesture for click
    right_click_gesture: str = "peace"  # Gesture for right click
    drag_gesture: str = "fist"      # Gesture for drag
    scroll_gesture: str = "two_fingers"  # Gesture for scroll
    dead_zone: float = 0.02         # Dead zone for movement
    screen_width: int = 1920
    screen_height: int = 1080


class MouseController:
    """
    Control mouse cursor with hand gestures.

    Features:
    - Move mouse with index finger
    - Click with pinch gesture
    - Right click with peace sign
    - Drag with fist
    - Scroll with two fingers
    """

    def __init__(self, config: MouseConfig = None):
        self.config = config or MouseConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Mouse control state
        self._last_hand_pos: Optional[Tuple[float, float]] = None
        self._smooth_pos: Optional[Tuple[float, float]] = None
        self._mouse_pressed = False
        self._right_mouse_pressed = False

        # Screen dimensions
        try:
            from screeninfo import get_monitors
            monitor = get_monitors()[0]
            self.config.screen_width = monitor.width
            self.config.screen_height = monitor.height
        except Exception:
            pass

        # Initialize mouse controller
        self._mouse = None
        self._init_mouse()

    def _init_mouse(self):
        """Initialize mouse controller (pynput)"""
        try:
            from pynput.mouse import Controller, Button
            self._mouse = Controller()
            self._Button = Button
            logger.info("Mouse controller initialized")
        except ImportError:
            logger.warning("pynput not available, mouse control disabled")
            self._mouse = None

    def start(self):
        """Start mouse control mode"""
        if self._running:
            return
        self._running = True
        self.config.enabled = True
        logger.info("Mouse control started")

    def stop(self):
        """Stop mouse control mode"""
        self._running = False
        self.config.enabled = False
        self._release_mouse()
        logger.info("Mouse control stopped")

    def _release_mouse(self):
        """Release any pressed mouse buttons"""
        if self._mouse and self._mouse_pressed:
            try:
                self._mouse.release(self._Button.left)
                self._mouse_pressed = False
            except Exception:
                pass
        if self._mouse and self._right_mouse_pressed:
            try:
                self._mouse.release(self._Button.right)
                self._right_mouse_pressed = False
            except Exception:
                pass

    def update(self, landmarks, gesture: str = "none") -> dict:
        """
        Update mouse position based on hand landmarks.

        Parameters:
            landmarks: Hand landmarks (21 points)
            gesture: Current recognized gesture

        Returns:
            dict with mouse action info
        """
        if not self._running or not self._mouse or not landmarks:
            return {"action": "none"}

        try:
            # Get index finger tip position (landmark 8)
            index_tip = landmarks[8]
            hand_x = index_tip.x
            hand_y = index_tip.y

            # Apply dead zone
            if self._last_hand_pos:
                dx = hand_x - self._last_hand_pos[0]
                dy = hand_y - self._last_hand_pos[1]
                if abs(dx) < self.config.dead_zone and abs(dy) < self.config.dead_zone:
                    return {"action": "none"}

            # Smooth position
            if self._smooth_pos is None:
                self._smooth_pos = (hand_x, hand_y)
            else:
                alpha = self.config.smooth_factor
                smooth_x = self._smooth_pos[0] * (1 - alpha) + hand_x * alpha
                smooth_y = self._smooth_pos[1] * (1 - alpha) + hand_y * alpha
                self._smooth_pos = (smooth_x, smooth_y)

            # Map hand position to screen coordinates
            # Camera is mirrored, hand x=0 is right side of screen
            screen_x = int(self._smooth_pos[0] * self.config.screen_width * self.config.sensitivity)
            screen_y = int(self._smooth_pos[1] * self.config.screen_height * self.config.sensitivity)

            # Clamp to screen bounds
            screen_x = max(0, min(screen_x, self.config.screen_width - 1))
            screen_y = max(0, min(screen_y, self.config.screen_height - 1))

            # Move mouse
            self._mouse.position = (screen_x, screen_y)
            self._last_hand_pos = (hand_x, hand_y)

            # Handle gestures for clicking
            action = self._handle_gesture(gesture)

            return {
                "action": action,
                "position": (screen_x, screen_y),
                "gesture": gesture
            }

        except Exception as e:
            logger.warning(f"Mouse control error: {e}")
            return {"action": "error", "message": str(e)}

    def _handle_gesture(self, gesture: str) -> str:
        """Handle gesture for mouse actions"""
        if not self._mouse:
            return "none"

        action = "move"

        # Left click
        if gesture == self.config.click_gesture:
            if not self._mouse_pressed:
                self._mouse.press(self._Button.left)
                self._mouse_pressed = True
                action = "click"
        else:
            if self._mouse_pressed:
                self._mouse.release(self._Button.left)
                self._mouse_pressed = False
                action = "release"

        # Right click
        if gesture == self.config.right_click_gesture:
            if not self._right_mouse_pressed:
                self._mouse.press(self._Button.right)
                self._right_mouse_pressed = True
                action = "right_click"
        else:
            if self._right_mouse_pressed:
                self._mouse.release(self._Button.right)
                self._right_mouse_pressed = False

        return action

    def is_active(self) -> bool:
        """Check if mouse control is active"""
        return self._running and self.config.enabled

    def get_config(self) -> dict:
        """Get current configuration"""
        return {
            "enabled": self.config.enabled,
            "sensitivity": self.config.sensitivity,
            "smooth_factor": self.config.smooth_factor,
            "click_gesture": self.config.click_gesture,
            "dead_zone": self.config.dead_zone,
        }

    def set_sensitivity(self, value: float):
        """Set mouse sensitivity"""
        self.config.sensitivity = max(0.5, min(3.0, value))

    def set_smooth_factor(self, value: float):
        """Set smoothing factor"""
        self.config.smooth_factor = max(0.0, min(1.0, value))
