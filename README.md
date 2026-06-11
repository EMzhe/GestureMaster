<div align="center">

# 🎯 GestureMaster

### 手势控制大师

**基于 MediaPipe 的智能手势识别桌面控制应用**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [手势列表](#-支持的手势) • [自定义配置](#-自定义配置)

</div>

---

## ✨ 功能特性

- 🎥 **实时手势识别** - 基于 MediaPipe 的高精度手部检测
- 🖱️ **鼠标控制** - 用手势控制鼠标移动和点击
- ⌨️ **按键映射** - 支持任意键盘按键和组合键
- 🎨 **现代 UI** - Catppuccin Mocha 主题，全中文界面
- ⚙️ **高度可定制** - 自定义手势绑定、灵敏度调节
- 🚀 **即装即用** - 简单的安装和配置流程

## 📦 快速开始

### 系统要求

- Windows 10/11
- Python 3.8+
- 摄像头

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/GestureMaster.git
   cd GestureMaster
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python launch.py
   ```
   
   或双击 `start.bat`

### 依赖包

| 包名 | 版本 | 用途 |
|------|------|------|
| PyQt6 | >=6.5.0 | GUI 框架 |
| opencv-python | >=4.8.0 | 摄像头捕获 |
| mediapipe | ==0.10.14 | 手势识别 |
| numpy | >=1.24.0 | 数值计算 |
| pynput | >=1.7.6 | 键鼠控制 |
| psutil | >=5.9.0 | 系统监控 |

## 🎮 使用指南

### 主界面

| 页面 | 功能 |
|------|------|
| 📷 摄像头预览 | 查看摄像头画面和识别结果 |
| ✋ 手势管理 | 管理手势绑定，启用/禁用手势 |
| 🧪 手势测试 | 实时测试手势识别效果 |
| 🖱️ 鼠标控制 | 用手势控制鼠标 |
| ⚙ 应用设置 | 调整摄像头、检测等参数 |

### 设置手势绑定

1. 进入「✋ 手势管理」页面
2. 点击手势卡片的「编辑绑定」
3. 选择动作类型（锁屏、打开网址、发送按键等）
4. 点击「💾 保存配置」

### 鼠标控制

1. 进入「🖱️ 鼠标控制」页面
2. 点击「启动鼠标控制」
3. 用食指移动控制光标
4. 做出捏合手势进行点击

## 🤚 支持的手势

| 手势 | Emoji | 说明 |
|------|-------|------|
| 握拳 | ✊ | 所有手指弯曲 |
| 张开手掌 | 🖐 | 所有手指伸展 |
| 竖大拇指 | 👍 | 仅拇指伸展 |
| 大拇指朝下 | 👎 | 拇指伸展朝下 |
| 比耶 | ✌ | 食指和中指伸展 |
| OK手势 | 👌 | 拇指和食指形成圆圈 |
| 食指朝上 | ☝ | 仅食指伸展 |
| 三指 | 🤟 | 拇指+食指+中指 |
| 摇滚 | 🤘 | 食指和小指伸展 |
| 捏合 | 🤏 | 拇指和食指捏合 |
| 指向左 | 👈 | 食指指向左 |
| 指向右 | 👉 | 食指指向右 |

## ⚙ 自定义配置

### 支持的动作类型

#### 系统控制
- 🔒 锁屏
- ⏻ 关机 / 重启 / 休眠
- 🔇 静音 / 取消静音

#### 媒体控制
- ▶ 播放/暂停
- ⏭ 下一曲 / ⏮ 上一曲
- 🔊 音量+ / 🔉 音量-

#### 应用启动
- 🌐 打开网址
- 📁 打开程序
- 📂 打开目录

#### 键盘按键
- ⌨ 发送单个按键（Enter、Space、F1-F12 等）
- ⌨ 发送组合键（Ctrl+C、Alt+Tab 等）

#### 窗口管理
- 📌 最小化 / 最大化窗口
- ❌ 关闭窗口
- 🔄 切换窗口

### 配置文件

配置文件 `config.json` 示例：

```json
{
  "camera": {
    "device_id": 0,
    "resolution": [640, 480],
    "fps": 30
  },
  "detection": {
    "confidence": 0.70,
    "max_hands": 1,
    "gesture_cooldown": 1.5
  },
  "bindings": [
    {
      "gesture": "fist",
      "actions": [{"type": "lock_screen", "params": {}}],
      "enabled": true
    }
  ]
}
```

## 📁 项目结构

```
GestureMaster/
├── core/                    # 核心识别模块
│   ├── camera.py           # 摄像头管理
│   ├── hand_detector.py    # 手部检测
│   ├── gesture_classifier.py # 手势分类
│   ├── action_executor.py  # 动作执行
│   └── mouse_controller.py # 鼠标控制
├── ui/                      # 界面模块
│   ├── main_window.py      # 主窗口
│   ├── gesture_manager_page.py # 手势管理
│   ├── gesture_test_page.py # 手势测试
│   ├── mouse_control_page.py # 鼠标控制
│   └── styles.py           # 样式主题
├── utils/                   # 工具模块
│   └── config_manager.py   # 配置管理
├── main.py                  # 主程序
├── launch.py                # 启动脚本
├── start.bat                # Windows 启动
├── config.json              # 配置文件
├── requirements.txt         # 依赖列表
├── LICENSE                  # MIT 许可证
└── README.md                # 项目说明
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [MediaPipe](https://google.github.io/mediapipe/) - 手部检测框架
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [Catppuccin](https://github.com/catppuccin/catppuccin) - 主题配色

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

</div>
