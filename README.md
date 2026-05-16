# PixelBeat 🎵

一款复古像素风格的音乐播放器，融合了现代音频处理技术与经典像素美学，并内置 AI Agent 终端支持智能交互。

## ✨ 功能特性

### 🎵 核心音乐播放
- 🎮 **像素风格UI**：复古像素艺术设计，CRT 屏幕效果，带来怀旧游戏氛围
- 🎵 **多格式音频播放**：支持 MP3、WAV、OGG 等多种音频格式
- 📊 **实时频谱可视化**：基于 FFT 的音频频谱分析，动态柱状图渲染
- 📝 **播放列表管理**：创建、删除、选择和管理音乐播放列表
- 📜 **LRC 歌词同步显示**：加载并高亮显示 LRC 格式时间轴歌词
- 🔄 **多种播放模式**：顺序播放、随机播放、单曲循环
- 💾 **状态持久化**：自动保存播放列表、播放模式和最近目录

### 🤖 AI 智能功能
- 💻 **Terminal 终端对话**：内置像素风终端界面，连接 AI Agent 进行多轮工具调用对话
- 🎙️ **音频转文字 (Audio to Doc)**：一键将当前播放的音频文件转录为文本并保存
- 🛠️ **Agent 工具系统**：支持 bash 命令执行、文件读写、网页搜索等工具

### 🔧 辅助功能
- 📥 **B站音频下载**：内置 Bilibili 视频音频提取，下载后自动加入播放列表
- 🎨 **主题系统**：支持像素风格配色方案切换
- ⌨️ **键盘快捷键**：支持 Space 播放/暂停、Ctrl+O 导入音乐、方向键切歌等

---

## 📸 预览

```
┌──────────────────────────────────────┐
│ 🎵 PIXEltune V1.0        ─ □ ✕      │
├──────────────────────────────────────┤
│                                      │
│          [ CRT Display Area ]        │
│         ┌──────────────────┐         │
│         │                  │         │
│         │   ♪ NOW PLAYING  │         │
│         │   TRACK NAME     │         │
│         │                  │         │
│         │  ▓▓░▒░▓▓░▒█▓▓   │  ◄ 频谱  │
│         └──────────────────┘         │
│         VIEW LYRICS  MENU       00:00 │
│         ═════════════════            │
│              ━━━━━━━━━━              │
│         ▶⏮ ◀⏹▶▶ 🔀 🔁               │
│                                        │
│   ♫ ━━━━━━━━━━                         │
│                              📃  ▼     │
└──────────────────────────────────────┘
```

## 技术栈

- **GUI 框架**: PySide6 (Qt6) — 无框窗口 + 自定义绘制
- **音频引擎**: pygame.mixer + numpy FFT 频谱分析
- **语音转写**: whisper / openai-whisper（音频转文字）
- **AI Agent**: OpenAI-compatible API（支持 OpenAI、Qwen、DeepSeek、Anthropic、GLM 等）
- **视频下载**: ffmpeg（音视频处理）+ 自研 B站下载器
- **开发语言**: Python 3.10+

---

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- macOS / Windows / Linux
- ffmpeg（用于音视频处理和 B站下载）
- （可选）whisper（音频转文字功能）

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

# macOS Qt 平台插件路径配置
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
从 [ffmpeg 官网](https://ffmpeg.org/download.html) 下载并添加到系统 PATH

### 配置环境变量

复制示例配置文件并编辑：

```bash
cp .env.example .env
```

`.env` 文件内容说明：

```env
# ===== 下载设置 =====
# 下载文件保存目录
DOWNLOAD_DIR=./downloads

# ===== AI 终端对话（Agent）=====
# 默认 AI 提供商: openai / qwen / deepseek / anthropic / glm
DEFAULT_PROVIDER=qwen

# 会话配置
SESSION_AUTO_SAVE=true          # 自动保存会话历史
SESSION_MAX_HISTORY=100         # 最大保留的历史条数

# AI 提供商 API 密钥（使用 PROVIDER_NAME 大写形式）
# 例如 PROVIDER=qwen 时使用 QWEN_API_KEY：
QWEN_API_KEY=sk-your-key-here   # Qwen DashScope API Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_DEFAULT_MODEL=qwen-turbo

# 如果使用 OpenAI 模型：
OPENAI_API_KEY=sk-your-key-here
# OPENAI_BASE_URL=https://api.openai.com  # 通常不需要修改

# 如果使用 DeepSeek：
DEEPSEEK_API_KEY=sk-your-key-here
# DEEPSEEK_BASE_URL=https://api.deepseek.com

# ===== 语音转文字（Speech Transcription）=====
SPEECH_API_KEY=your-siliconflow-key
SPEECH_API_URL=https://api.siliconflow.cn/v1/audio/transcriptions
SPEECH_MODEL=FunAudioLLM/SenseVoiceSmall
```

> **提示**: 如果你不确定配置哪些变量，可以参考项目根目录下的 `.env.example` 文件，其中包含了完整的环境变量示例。

### 运行应用

```bash
python main.py
```

---

## 使用说明

### 🎵 基本播放

1. **启动应用**后，点击 `MENU` 按钮打开菜单面板
2. 点击 **LOAD MUSIC** 导入本地音频文件（MP3/WAV/OGG）
3. 在底部展开的播放列表中选择歌曲进行播放
4. 使用底部控制条调整音量和拖拽播放进度
5. 欣赏 CRT 屏幕上的实时频谱可视化效果

### ⌨️ 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Space` | 播放 / 暂停 |
| `Ctrl + O` | 导入音频文件 |
| `Ctrl + Right` | 下一首 |
| `Ctrl + Left` | 上一首 |
| `Delete` | 删除当前选中的曲目 |
| `Escape` | 关闭窗口 |

### 📜 加载歌词

1. 点击 `MENU` → **LOAD LRC**
2. 选择对应的 LRC 歌词文件
3. 点击 `VIEW LYRICS` 按钮切换歌词显示模式
4. 歌词将随音乐时间轴同步高亮滚动

### 🔄 播放模式

通过下方工具栏图标切换：

- 🔀 **SHUFFLE**：随机播放
- 🔁 **SINGLE_LOOP**：单曲循环
- （默认不亮 = 顺序循环播放）

### 🤖 Terminal 终端对话

1. 点击 `MENU` → **TERMINAL** 打开 AI 终端对话框
2. 输入自然语言指令与 AI Agent 交互
3. 支持的快捷命令：
   - `play` / `pause` — 播放 / 暂停
   - `next` / `prev` — 切歌
   - `volume <0-100>` — 调节音量
   - `help` — 查看可用命令
4. AI Agent 可执行 bash 命令、读写文件、搜索网页等

### 🎙️ 音频转文字 (Audio to Doc)

1. 确保正在播放一首音频文件
2. 点击 `MENU` → **AUDIO TO DOC**
3. 系统自动调用语音识别模型转录该音频
4. 转录完成后提示文本保存路径

### 📥 B 站音频下载

1. 点击 `MENU` → **DOWNLOAD**
2. 在弹窗中粘贴 B 站视频链接
3. 系统自动获取视频标题和大小信息
4. 点击下载，音频提取并保存到 `./downloads`
5. 下载完成后自动加入播放列表

#### 支持的链接格式

- `https://www.bilibili.com/video/BVxxxxxx`
- `https://b23.tv/xxxxxx`（短链接）

---

## 项目结构

```
PixelBeat/
├── main.py                       # 应用入口，初始化 MVC
├── requirements.txt              # Python 依赖
├── .env                          # 环境变量配置（需自行创建）
├── .env.example                  # 环境变量示例模板
├── assets/                       # 资源文件
│   ├── fonts/                    # 像素字体（PressStart2P）
│   └── icons/                    # 图标资源
├── core/                         # 核心服务层
│   ├── audio_engine.py           # 音频引擎（pygame）
│   ├── agent/                    # AI Agent 子系统
│   │   ├── agent_loop.py         # 多轮 Tool Calling 循环
│   │   ├── conversation.py       # 对话管理
│   │   ├── history.py            # 对话历史
│   │   ├── session.py            # 会话管理
│   │   ├── tool_registry.py      # 工具注册中心
│   │   ├── providers/            # LLM 提供商适配
│   │   │   ├── base.py           # 抽象基类
│   │   │   ├── openai_provider.py
│   │   │   ├── qwen_provider.py
│   │   │   ├── deepseek_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   ├── glm_provider.py
│   │   │   └── openai_compatible.py
│   │   └── cli/                  # CLI 终端代理实现
│   └── speech/                   # 语音转写模块
│       └── transcriber.py        # 音频转文字接口
├── models/                       # 数据模型（MVC Model）
│   ├── playlist_model.py         # 播放列表状态管理
│   └── track.py                  # 音轨数据结构
├── ui/                           # 用户界面（MVC View/Controller）
│   ├── main_window.py            # 主窗口 + 所有 UI 逻辑
│   ├── terminal_dialog.py        # AI 终端对话框
│   ├── themes.py                 # 像素主题配色
│   └── widgets/                  # 自定义控件
│       ├── download_dialog.py    # B站下载对话框
│       ├── pixel_button.py       # 像素风格按钮
│       ├── playlist_widget.py    # 播放列表控件
│       ├── spectrum_widget.py    # 频谱可视化控件
│       ├── spin_sprite_widget.py # 旋转精灵图控件
│       └── title_bar.py          # 自定义标题栏
├── utils/                        # 工具模块
│   ├── bilibili_downloader.py    # B站音频下载器
│   ├── pixel_icons.py            # 像素图标生成器
│   ├── spectrum_analyzer.py      # FFT 频谱分析
│   └── storage.py                # JSON 持久化存储
├── downloads/                    # B站下载文件默认目录
├── scripts/                      # 辅助脚本
│   └── smoke_check.py            # 冒烟测试脚本
└── tests/                        # 单元测试
    ├── test_playlist_model.py    # 播放列表模型测试
    └── test_storage.py           # 存储模块测试
```

---

## 开发指南

### 运行测试

```bash
python -m pytest tests/ -v
```

### 代码检查

```bash
flake8 . --exclude=.venv,.pixelbeat,__pycache__
```

### 架构设计

本项目采用 **MVC 架构**：

| 层级 | 目录 | 职责 |
|------|------|------|
| **Model** | `models/` | 数据模型与业务状态（播放列表） |
| **View** | `ui/widgets/`, `ui/themes.py` | 自定义控件与视觉样式 |
| **Controller** | `ui/main_window.py` | 视图事件处理、MVC 桥接 |
| **Service** | `core/` | 核心服务（音频、Agent、语音） |
| **Utility** | `utils/` | 工具函数库 |

### 添加新功能

1. **新增 UI 控件**：在 `ui/widgets/` 下创建继承自 `QWidget` 的类
2. **新增核心服务**：在 `core/` 对应子目录下实现，然后通过信号槽连接到 Main Window
3. **新增 AI 工具**：在 `core/agent/tools/` 中注册，工具 schema 会被自动注入 Agent 系统
4. **新增 LLM 提供商**：继承 `core/agent/providers/base.BaseProvider` 并实现必要方法

---

## 常见问题 (FAQ)

**Q: B站下载失败怎么办？**  
A: 请确认已正确安装 `ffmpeg` 并在 PATH 中。B站策略可能随时变化，如果遇到无法解析的问题请提交 Issue。

**Q: 音频无法播放？**  
A: 检查音频格式是否为 MP3/WAV/OGG，同时确认系统音频输出设备正常工作。

**Q: Terminal 对话连接失败？**  
A: 检查 `.env` 中的 API Key 和 Base URL 配置是否正确，确认网络可访问目标 API 服务。

**Q: 音频转文字失败或缺失？**  
A: 需要安装 `openai-whisper`（`pip install openai-whisper`），并确保系统内存充足。

**Q: 界面显示异常（macOS）？**  
A: 设置 `QT_QPA_PLATFORM_PLUGIN_PATH` 指向 PySide6 的 Qt plugins 目录。

**Q: 如何更换 AI 提供商？**  
A: 修改 `.env` 中的 `PROVIDER` 变量，或在 Terminal 对话框中手动选择提供商。

---

## 许可证

MIT License
