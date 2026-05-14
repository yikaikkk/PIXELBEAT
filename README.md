# PixelBeat 🎵

一款复古像素风格的音乐播放器，融合了现代音频处理技术与经典像素美学。

## 功能特性

- 🎮 **像素风格UI**：复古像素艺术设计，带来怀旧游戏氛围
- 🎵 **音频播放**：支持多种音频格式播放
- 📊 **频谱分析**：实时音频频谱可视化
- 📝 **播放列表管理**：创建和管理音乐播放列表
- 🎨 **主题系统**：支持多种像素风格主题切换

## 技术栈

- **框架**: PySide6 (Qt6)
- **音频引擎**: Pygame
- **数值计算**: NumPy
- **语言**: Python 3.11+

## 项目结构

```
PixelBeat/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖列表
├── assets/                 # 资源文件
│   ├── fonts/              # 像素字体
│   ├── icons/              # 图标资源
│   └── sprites/            # 精灵图
├── core/                   # 核心服务
│   └── audio_engine.py     # 音频引擎
├── models/                 # 数据模型
│   ├── playlist_model.py   # 播放列表模型
│   └── track.py            # 音轨数据结构
├── ui/                     # 用户界面
│   ├── main_window.py      # 主窗口
│   ├── themes.py           # 主题系统
│   └── widgets/            # 自定义控件
├── utils/                  # 工具模块
│   ├── pixel_icons.py      # 像素图标生成
│   ├── spectrum_analyzer.py # 频谱分析
│   └── storage.py          # 数据持久化
└── tests/                  # 测试用例
```

## 快速开始

### 环境要求

- Python 3.11 或更高版本
- macOS / Windows / Linux

### 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c "import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), 'Qt/plugins/platforms'))")
```

### 运行应用

```bash
python main.py
```

## 使用说明

1. 启动应用后，点击添加按钮导入音频文件
2. 在播放列表中选择歌曲进行播放
3. 调整音量和播放进度
4. 欣赏实时频谱可视化效果

## 开发

### 运行测试

```bash
python -m pytest tests/
```

### 代码检查

```bash
flake8 . --exclude=.venv
```

## 许可证

MIT License
