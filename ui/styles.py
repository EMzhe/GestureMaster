"""
全局样式模块
提供 Catppuccin Mocha 风格的深色主题 QSS 样式表。
"""

# Catppuccin Mocha 调色板
COLORS = {
    "bg": "#1e1e2e",
    "bg_dark": "#181825",
    "surface": "#313244",
    "overlay": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "purple": "#cba6f7",
    "teal": "#94e2d5",
    "pink": "#f5c2e7",
    "peach": "#fab387",
}

DARK_STYLE = f"""
/* ===== 全局 ===== */
QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}}

/* ===== 主窗口 ===== */
QMainWindow {{
    background-color: {COLORS['bg']};
}}

/* ===== 按钮 ===== */
QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['overlay']};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {COLORS['overlay']};
    border-color: {COLORS['blue']};
}}
QPushButton:pressed {{
    background-color: {COLORS['blue']};
    color: {COLORS['bg']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['overlay']};
    border-color: {COLORS['surface']};
}}

/* 主要按钮 */
QPushButton[cssClass="primary"] {{
    background-color: {COLORS['blue']};
    color: {COLORS['bg']};
    border: none;
}}
QPushButton[cssClass="primary"]:hover {{
    background-color: {COLORS['teal']};
}}

/* 危险按钮 */
QPushButton[cssClass="danger"] {{
    background-color: {COLORS['red']};
    color: {COLORS['bg']};
    border: none;
}}
QPushButton[cssClass="danger"]:hover {{
    background-color: {COLORS['peach']};
}}

/* 成功按钮 */
QPushButton[cssClass="success"] {{
    background-color: {COLORS['green']};
    color: {COLORS['bg']};
    border: none;
}}

/* ===== 框架/分组 ===== */
QFrame, QGroupBox {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['surface']};
    border-radius: 8px;
}}
QGroupBox {{
    font-weight: bold;
    margin-top: 10px;
    padding-top: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['text']};
}}

/* ===== 标签 ===== */
QLabel {{
    background: transparent;
    border: none;
    color: {COLORS['text']};
}}
QLabel[cssClass="title"] {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QLabel[cssClass="subtitle"] {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['subtext']};
}}
QLabel[cssClass="caption"] {{
    font-size: 11px;
    color: {COLORS['subtext']};
}}

/* ===== 输入框 ===== */
QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['overlay']};
    border-radius: 4px;
    padding: 6px;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['blue']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['overlay']};
}}

/* ===== 滑块 ===== */
QSlider::groove:horizontal {{
    background: {COLORS['surface']};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLORS['blue']};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {COLORS['teal']};
}}
QSlider::sub-page:horizontal {{
    background: {COLORS['blue']};
    border-radius: 3px;
}}

/* ===== 滚动区域 ===== */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {COLORS['bg']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['overlay']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['subtext']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ===== 列表 ===== */
QListWidget {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['surface']};
    border-radius: 6px;
    color: {COLORS['text']};
}}
QListWidget::item {{
    padding: 6px;
    border-bottom: 1px solid {COLORS['surface']};
}}
QListWidget::item:selected {{
    background-color: {COLORS['surface']};
}}
QListWidget::item:hover {{
    background-color: {COLORS['surface']};
}}

/* ===== 表格 ===== */
QTableWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['surface']};
    border-radius: 6px;
    gridline-color: {COLORS['surface']};
}}
QHeaderView::section {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    padding: 6px;
    border: none;
    font-weight: bold;
}}

/* ===== 标签页 ===== */
QTabWidget::pane {{
    border: 1px solid {COLORS['surface']};
    border-radius: 6px;
    background: {COLORS['bg']};
}}
QTabBar::tab {{
    background: {COLORS['surface']};
    color: {COLORS['subtext']};
    padding: 8px 20px;
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
    font-weight: bold;
}}
QTabBar::tab:hover {{
    color: {COLORS['text']};
}}

/* ===== 复选框 ===== */
QCheckBox {{
    spacing: 8px;
    color: {COLORS['text']};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['overlay']};
    border-radius: 4px;
    background: {COLORS['surface']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['blue']};
    border-color: {COLORS['blue']};
}}

/* ===== 进度条 ===== */
QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['overlay']};
    border-radius: 5px;
    text-align: center;
    color: {COLORS['text']};
}}
QProgressBar::chunk {{
    background-color: {COLORS['blue']};
    border-radius: 4px;
}}

/* ===== 提示框 ===== */
QToolTip {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['overlay']};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ===== 消息框 ===== */
QMessageBox {{
    background-color: {COLORS['bg']};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ===== 输入对话框 ===== */
QInputDialog {{
    background-color: {COLORS['bg']};
}}

/* ===== 分割器 ===== */
QSplitter::handle {{
    background: {COLORS['surface']};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}
"""


def get_style(theme: str = "dark") -> str:
    """获取指定主题的样式表。"""
    if theme == "dark":
        return DARK_STYLE
    return ""  # 未来可扩展 light 主题
