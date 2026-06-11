"""
Generate modern tech-style icon for GestureMaster
"""
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient
from PyQt6.QtCore import Qt, QPoint, QPointF
import math

def create_color(hex_color, alpha=255):
    """Create QColor from hex string with alpha"""
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color

def create_tech_icon():
    app = QApplication([])

    sizes = [16, 32, 48, 64, 128, 256]
    pixmaps = []

    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale = size / 256.0
        cx = size / 2
        cy = size / 2

        # === 外圈发光效果 ===
        glow_gradient = QRadialGradient(cx, cy, 120*scale)
        glow_gradient.setColorAt(0.8, create_color("#89b4fa", 60))
        glow_gradient.setColorAt(1.0, create_color("#89b4fa", 0))
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - 120*scale), int(cy - 120*scale), int(240*scale), int(240*scale))

        # === 背景圆形（深色科技风）===
        bg_gradient = QRadialGradient(cx, cy, 110*scale)
        bg_gradient.setColorAt(0, QColor("#1e1e2e"))
        bg_gradient.setColorAt(1, QColor("#11111b"))
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(QColor("#45475a"), max(1, int(2*scale))))
        painter.drawEllipse(int(cx - 105*scale), int(cy - 105*scale), int(210*scale), int(210*scale))

        # === 内圈装饰线 ===
        painter.setPen(QPen(QColor("#313244"), max(1, int(1*scale))))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(cx - 85*scale), int(cy - 85*scale), int(170*scale), int(170*scale))

        # === 手掌（科技风格化）===
        hand_color = QColor("#89b4fa")

        # 手掌主体
        painter.setPen(QPen(hand_color, max(1, int(2.5*scale))))
        painter.setBrush(QBrush(create_color("#89b4fa", 30)))

        # 简化的手掌形状 - 使用圆形和矩形组合
        # 手掌
        painter.drawEllipse(int(cx - 25*scale), int(cy - 15*scale), int(50*scale), int(55*scale))

        # === 手指（线条风格）===
        finger_color = QColor("#74c7ec")
        painter.setPen(QPen(finger_color, max(1, int(3*scale))))

        # 拇指
        painter.drawLine(
            int(cx - 25*scale), int(cy + 5*scale),
            int(cx - 45*scale), int(cy - 15*scale)
        )
        painter.drawLine(
            int(cx - 45*scale), int(cy - 15*scale),
            int(cx - 50*scale), int(cy - 30*scale)
        )

        # 食指
        painter.drawLine(
            int(cx - 10*scale), int(cy - 15*scale),
            int(cx - 10*scale), int(cy - 50*scale)
        )
        painter.drawLine(
            int(cx - 10*scale), int(cy - 50*scale),
            int(cx - 8*scale), int(cy - 65*scale)
        )

        # 中指
        painter.drawLine(
            int(cx), int(cy - 15*scale),
            int(cx), int(cy - 60*scale)
        )
        painter.drawLine(
            int(cx), int(cy - 60*scale),
            int(cx + 2*scale), int(cy - 75*scale)
        )

        # 无名指
        painter.drawLine(
            int(cx + 10*scale), int(cy - 15*scale),
            int(cx + 12*scale), int(cy - 45*scale)
        )
        painter.drawLine(
            int(cx + 12*scale), int(cy - 45*scale),
            int(cx + 14*scale), int(cy - 60*scale)
        )

        # 小指
        painter.drawLine(
            int(cx + 20*scale), int(cy - 10*scale),
            int(cx + 25*scale), int(cy - 30*scale)
        )
        painter.drawLine(
            int(cx + 25*scale), int(cy - 30*scale),
            int(cx + 28*scale), int(cy - 43*scale)
        )

        # === 鼠标光标（科技风格）===
        cursor_x = cx + 55*scale
        cursor_y = cy - 40*scale

        # 光标发光
        cursor_glow = QRadialGradient(cursor_x, cursor_y, 25*scale)
        cursor_glow.setColorAt(0, create_color("#f38ba8", 80))
        cursor_glow.setColorAt(1, create_color("#f38ba8", 0))
        painter.setBrush(QBrush(cursor_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cursor_x - 25*scale), int(cursor_y - 25*scale), int(50*scale), int(50*scale))

        # 光标主体
        painter.setBrush(QBrush(QColor("#f38ba8")))
        painter.setPen(QPen(QColor("#1e1e2e"), max(1, int(1.5*scale))))

        cursor_points = [
            QPoint(int(cursor_x), int(cursor_y)),
            QPoint(int(cursor_x + 8*scale), int(cursor_y + 22*scale)),
            QPoint(int(cursor_x + 12*scale), int(cursor_y + 12*scale)),
            QPoint(int(cursor_x + 22*scale), int(cursor_y + 8*scale)),
        ]
        painter.drawPolygon(cursor_points)

        # === 检测点（科技风格）===
        dot_positions = [
            (cx - 40*scale, cy - 20*scale),
            (cx - 30*scale, cy - 35*scale),
            (cx - 20*scale, cy - 50*scale),
            (cx - 50*scale, cy - 10*scale),
        ]

        # 连接线
        painter.setPen(QPen(create_color("#a6e3a1", 150), max(1, int(1*scale))))
        for i in range(len(dot_positions) - 1):
            painter.drawLine(
                int(dot_positions[i][0]), int(dot_positions[i][1]),
                int(dot_positions[i+1][0]), int(dot_positions[i+1][1])
            )

        # 检测点
        painter.setPen(Qt.PenStyle.NoPen)
        for dx, dy in dot_positions:
            # 外圈
            painter.setBrush(QBrush(create_color("#a6e3a1", 60)))
            painter.drawEllipse(int(dx - 6*scale), int(dy - 6*scale), int(12*scale), int(12*scale))
            # 内圈
            painter.setBrush(QBrush(QColor("#a6e3a1")))
            painter.drawEllipse(int(dx - 3*scale), int(dy - 3*scale), int(6*scale), int(6*scale))

        # === 装饰性科技元素 ===
        # 扫描线
        painter.setPen(QPen(create_color("#89b4fa", 30), max(1, int(1*scale))))
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + 90*scale * math.cos(rad)
            y1 = cy + 90*scale * math.sin(rad)
            x2 = cx + 100*scale * math.cos(rad)
            y2 = cy + 100*scale * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()
        pixmaps.append(pixmap)

    # 保存文件
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    for size, pixmap in zip(sizes, pixmaps):
        png_path = os.path.join(assets_dir, f"icon_{size}x{size}.png")
        pixmap.save(png_path, "PNG")
        print(f"Saved: {png_path}")

    # 保存主图标
    main_path = os.path.join(assets_dir, "icon.png")
    pixmaps[-1].save(main_path, "PNG")
    print(f"Saved: {main_path}")

    print(f"\nIcon files created in '{assets_dir}'")
    print("Note: For .ico format, use an online converter like https://convertico.com/")

    return pixmaps

if __name__ == "__main__":
    create_tech_icon()
