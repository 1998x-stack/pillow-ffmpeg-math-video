# Pillow + FFmpeg 数学教育视频 Skill

独立可复制的 Skill 目录，包含可执行的 Pillow 专属二维数学绘图函数、公式贴图、确定性时间轴、静态/动态 RGBA 层缓存、FFmpeg 安全编码、数学/几何/视觉/媒体 verifier、Manim Math Gotchas 迁移记录、勾股定理案例及可复现的 MP4 渲染流程。

请先读 [`INSTALL.md`](INSTALL.md) 了解如何作为独立 Skill 安装以及与 `manim_math` 双 Skill 架构的适配方式。

### 最快上手

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m scripts.demo --output /tmp/pillow-math-demo.mp4
python -m scripts.visual_review /tmp/pillow-math-demo.mp4 --outdir /tmp/pillow-math-review --count 8
```

需要系统可用 `ffmpeg`, `ffprobe` 和支持中文的系统字体。默认不覆盖已存在视频。`python -m scripts.demo` 可生成 6 秒工程演示（展示直角三角形、边标和刚体平移，**并非完整勾股定理证明**）。完整勾股定理案例源代码及其独立验证器位于 `examples/`。

### 入口

- [`SKILL.md`](SKILL.md)：核心触发条件、工作流、Verifiers、API 索引
- [`references/gotchas.md`](references/gotchas.md)：32 项 Pillow+FFmpeg 专属 Gotchas、根因和失败测试
- [`references/manim-math-source-map.md`](references/manim-math-source-map.md)：GitHub `manim_math` 的可追溯规范映射
- [`references/geometry-and-labels.md`](references/geometry-and-labels.md)：数学→屏幕坐标、真实点标/角、拼图证明
- [`references/formula-and-layout.md`](references/formula-and-layout.md)：数学公式与中文布局
- [`references/architecture-and-performance.md`](references/architecture-and-performance.md)：缓存、端到端性能、批量生产架构
- [`references/verification-contract.md`](references/verification-contract.md)：12 层 Verifier、分层证据、门禁
- [`scripts/pillow_draw.py`](scripts/pillow_draw.py)：Pillow 专属绘制函数和坐标封装
- [`scripts/math_primitives.py`](scripts/math_primitives.py)：虚线、贝塞尔、参数曲线、切线法线、数轴、尺寸标注、气泡
- [`scripts/timeline.py`](scripts/timeline.py)：关键帧/缓存/dirty rect
- [`scripts/formulas.py`](scripts/formulas.py)：MathText 公式和 token morph 原型
- [`scripts/geometry.py`](scripts/geometry.py)：基础纯数学几何计算
- [`scripts/verify.py`](scripts/verify.py)：数学/几何/标签/像素验证
- [`scripts/media.py`](scripts/media.py)：安全 rawvideo→FFmpeg 与媒体探测
- [`scripts/visual_review.py`](scripts/visual_review.py)：真实 MP4 分层随机抽帧与 contact sheet

**限制**：不能自动证明一般数学定理、不能对有限抽帧宣称所有像素绝对正确、不是完整 LaTeX 或 3D 引擎。样例通过测试并不意味着用户新增数学场景也自动通过，新增课程需要独立 proof spec + verifier。

## 音轨扩展（v1.1）

新增 `scripts/voiceover.py`（离线 eSpeak -> FFmpeg AAC -> 新 MP4）、`references/audio-and-tts.md`（数学术语读法、分镜同步、音频质量与人工听审门禁）和 `tests/test_voiceover.py`。详情见 `references/audio-and-tts.md`；**当前离线中文语音只作为工程验证版，不能替代自然中文旁白**。

## v2：数学口播 + eSpeak NG + 可替换 WAV 后端

新增语音规范化、发音词典、音频时间轴、PCM 声学 Verifier、eSpeak NG/旧版 eSpeak 自适配和已授权 WAV 后端。自动测试包括真实 6 秒 MP4 中 H.264 + AAC 两条媒体流的端到端验证；机器生成的 eSpeak 配音仅作技术预览。参考 [`references/audio-and-tts.md`](references/audio-and-tts.md)、[`references/pronunciation-gotchas.md`](references/pronunciation-gotchas.md)。

```bash
python -m scripts.demo --output /tmp/math-demo.mp4 --fps 12
python -m scripts.speech_pipeline \
  --video /tmp/math-demo.mp4 \
  --segments assets/narration.example.json \
  --output /tmp/math-demo-with-voice.mp4
python -m scripts.release_gate --input assets/demo_gates.json \
  --output /tmp/release-report.json --audio-required
```

GitHub 仓库以源代码、脚本、参考资料和可运行的测试为准。演示 MP4 和临时 WAV 不加入 Git，避免二进制成片使仓库膨胀。`assets/demo_geometry.mp4` 和 `examples/pythagoras_verified.mp4` 属于历史本地构建产物，在本仓库的版本中需要通过对应源代码重新生成。

**限制**：自动音频 Verifier 不能证明中文自然度和准确发音。没有真实听审结果时，`publishable=false` 是预期输出。