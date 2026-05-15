# PixelBeat 🎵

一款复古像素风格的音乐播放器，融合了现代音频处理技术与经典像素美学。

## 功能特性

- 🎮 **像素风格UI**：复古像素艺术设计，带来怀旧游戏氛围
- 🎵 **音频播放**：支持 MP3、WAV、OGG 等多种音频格式
- 📊 **频谱分析**：实时音频频谱可视化
- 📝 **播放列表管理**：创建和管理音乐播放列表
- 🎨 **主题系统**：支持多种像素风格主题切换
- 📥 **B站音频下载**：内置 Bilibili 视频音频提取功能
- 📜 **LRC 歌词支持**：加载并显示 LRC 格式歌词
- 💾 **状态持久化**：自动保存播放状态和播放列表

## 技术栈

- **框架**: PySide6 (Qt6)
- **音频引擎**: Pygame
- **视频下载**: you-get
- **音视频处理**: ffmpeg
- **数值计算**: NumPy
- **环境变量**: python-dotenv
- **语言**: Python 3.11+

## 项目结构

```
PixelBeat/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖列表
├── .env                    # 环境变量配置（需自行创建）
├── .env.example            # 环境变量示例
├── .gitignore              # Git 忽略规则
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
│       └── download_dialog.py  # B站下载对话框
├── utils/                  # 工具模块
│   ├── bilibili_downloader.py  # B站视频下载器
│   ├── pixel_icons.py      # 像素图标生成
│   ├── spectrum_analyzer.py # 频谱分析
│   └── storage.py          # 数据持久化
└── downloads/              # 下载文件默认保存目录
```

## 快速开始

### 环境要求

- Python 3.11 或更高版本
- macOS / Windows / Linux
- ffmpeg（用于音视频处理）

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

# 设置 Qt 平台插件路径（macOS 可能需要）
export QT_QPA_PLATFORM_PLUGIN_PATH=$(python -c "import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), 'Qt/plugins/platforms'))")
```

### 安装 ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
从 [ffmpeg 官网](https://ffmpeg.org/download.html) 下载并添加到 PATH

### 配置环境变量

复制示例配置文件并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 下载文件保存目录
DOWNLOAD_DIR=./downloads
```

### 运行应用

```bash
python main.py
```

## 使用说明

### 基本播放

1. 启动应用后，点击 **LOAD** 按钮导入音频文件
2. 在播放列表中选择歌曲进行播放
3. 调整音量和播放进度
4. 欣赏实时频谱可视化效果

### 加载歌词

1. 点击 **VIEW ART** 按钮
2. 选择对应的 LRC 歌词文件
3. 歌词将随音乐同步显示

### 下载 B 站音频

1. 点击 **DOWNLOAD** 按钮
2. 在弹窗中粘贴 B 站视频链接
3. 系统自动获取视频信息（标题、大小）
4. 点击 **DOWNLOAD** 开始下载
5. 下载完成后音频自动添加到播放列表

### 播放模式

- **SHUFFLE**：随机播放
- **SINGLE_LOOP**：单曲循环
- 默认顺序播放

## B 站下载功能

### 支持的链接格式

- `https://www.bilibili.com/video/BVxxxxxx`
- `https://b23.tv/xxxxxx`（短链接）

### 下载流程

1. **获取信息**：输入链接后自动获取视频标题和大小
2. **下载音频**：提取视频中的音频轨道
3. **自动合并**：使用 ffmpeg 合并音视频（如需要）
4. **清理临时文件**：下载完成后自动清理临时文件
5. **添加播放列表**：下载成功自动加入播放列表（不自动播放）

### 下载目录

默认保存在 `./downloads` 目录，可通过 `.env` 文件中的 `DOWNLOAD_DIR` 环境变量修改。

## 开发

### 运行测试

```bash
python -m pytest tests/
```

### 代码检查

```bash
flake8 . --exclude=.venv
```

### 添加新功能

项目采用 MVC 架构：
- `models/` - 数据模型
- `ui/` - 用户界面
- `core/` - 核心服务
- `utils/` - 工具模块

## 常见问题

**Q: 下载失败怎么办？**
A: 确保已安装 ffmpeg 并添加到 PATH，检查网络连接是否正常。

**Q: 音频无法播放？**
A: 检查音频格式是否支持（MP3/WAV/OGG），确认系统音频输出正常。

**Q: 界面显示异常？**
A: macOS 用户可能需要设置 `QT_QPA_PLATFORM_PLUGIN_PATH` 环境变量。

## 许可证

MIT License
