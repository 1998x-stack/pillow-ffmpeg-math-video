# 数学视频音轨：TTS → 对齐 → 合成 → Verifier

## 环境与语音提供者

ChatGPT **对话语音**与生产级可下载 WAV/MP3 的 TTS 接口是不同的功能。使用当前会话可用的实际工具，不要假设“能语音聊天”就能调用原生可下载 TTS。对于 ChatGPT Python 运行环境，先实际探测 `ffmpeg`, `ffprobe`, `espeak`, 可用中文词典以及语音合成 API 凭据。

本 Skill 实现 `scripts/voiceover.py`：**离线 eSpeak 作为工程原型**，无需账号密钥，但中文词典可能不完整、中文数学术语发音生硬，**仅作为音视频端到端验证，禁止自动标记为正式教学配音**。视频本身由 Pillow + FFmpeg 生成或其他方式提供。FFmpeg 负责 AAC 编码、时间戳、流复用和媒体探测。

正式中文讲解建议外接质量经过试听的 TTS 服务（如支持中文的 OpenAI Speech API 或其他经授权服务）并保存已合成的 WAV/MP3，再通过同一段落时间轴混音。当前环境若没有密钥和可用 TTS 工具，**不可声称使用了 OpenAI 神经语音**。新版 API 调用应查官方文档：https://developers.openai.com/api/docs/guides/text-to-speech 。

## 演示命令

在 Skill 根目录：

```bash
python -m scripts.voiceover \
  --video /path/to/input.mp4 \
  --segments /path/to/narration_segments.json \
  --output /path/to/output_with_audio.mp4
```

`narration_segments.json` 结构：

```json
[
  {"start": 0, "end": 5, "title": "引入", "text": "今天我们认识椭圆。"},
  {"start": 5, "end": 11, "title": "定义", "text": "椭圆上动点到两个焦点的距离之和保持不变。"}
]
```

## 音频 Gotchas / 测试矩阵

| ID | 风险 | Verifier / 防护 |
|---|---|---|
| A01 | 中文 voice 可列出，但词典缺失、读音不准 | 捕获 stderr；保存 `pronunciation_review=not_run`；人工试听 |
| A02 | 数学符号读法混乱（平方、根号、上下标、焦距） | 单独制定语音可读稿；不把原样 LaTeX 直接提交 TTS |
| A03 | 单段配音超出幕长、被硬截断 | `raw_duration`, `atempo` 与 `estimated_ending` 自动验收；过长失败并重写文本 |
| A04 | 音轨与分镜时间错位 | 明确起止秒、FFprobe 验证长度、抽检首中末声学片段 |
| A05 | 音轨取代原始课堂讲解 | 始终保留原视频，只创建新输出；先 probe 原有音轨 |
| A06 | 噪声、爆音、静音或峰值削波 | 波形 RMS/peak、true peak、响度 LUFS；最后人工听审 |
| A07 | 语速过快、错误重音 | 避免超过 1.8x，实际教学优先重新分镜而非加速 |
| A08 | 音乐侵权或掩盖人声 | 必须确认授权；背景音乐独立音量与 ducking |
| A09 | 只有音轨存在即错误宣布质量通过 | 媒体 technical_pass 与 `human_listening`, `pronunciation` 分离 |
| A10 | 语音文本断言与屏幕公式不同 | `spoken_claim → math_spec → scene_time → proof` 一一对应，数学门禁先于生成 |
| A11 | AAC 编码延迟导致首尾细微偏移 | 容许容器级时差，解码检查段落起止、音画同步 |
| A12 | ASR 自动转写漏掉不易读符号 | ASR 可作为候选检查，不能替代数学与人工听审 |

## 发布分层证据

`math_claims`, `tts_provider`, `tts_generated`, `timing_fit`, `audio_stream_probe`, `audio_levels`, `asr_review`（可选）, `human_pronunciation`, `human_av_sync`, `media_license`。任何重要阶段为 `not_run` 不能默默升级为“发布通过”。尤其数学术语和中文读音必须由能够听到音频的人复核。

## v2：生产级结构分离（替代旧版便捷入口）

- `scripts/speech_normalizer.py`：保守的数学 LaTeX 子集 → 中文读法建议；遇不支持的语法拒绝，**不等同数学证明器**。
- `scripts/speech_timeline.py`：数学 `claim_id`、唯一 `segment_id`、口播稿与时间窗、SRT。
- `scripts/tts/espeak_backend.py`：自动探测 eSpeak NG（cmn）或旧版 eSpeak（zh）；记录词典错误但不批准发音。
- `scripts/tts/file_backend.py`：读取经授权的第三方生成 WAV；保留许可与审核元数据，不依赖隐式云凭据。
- `scripts/audio_verifier.py`：PCM16 WAV RMS、峰值、长静音、节奏限制（默认最大 1.25x）。
- `scripts/speech_pipeline.py`：音频先转换为 48kHz PCM，在样本索引处确定性合并后输出 AAC+MP4。严禁覆盖已有音轨。
- `scripts/pronunciation_probe.py`：eSpeak 音素输出调试，仅为候选，不能认定普通话正确。
- `references/pronunciation-gotchas.md`：S01–S20 详细风险、负例与修复。
- `references/speech-verifier.md`：数学口播、技术声学、时间轴、音画人工审核与许可的独立 Gate。

示例：

```bash
python -m scripts.demo --output /tmp/math-demo.mp4 --fps 12
python -m scripts.speech_pipeline \
  --video /tmp/math-demo.mp4 \
  --segments assets/narration.example.json \
  --output /tmp/math-demo-narrated.mp4
python -m scripts.pronunciation_probe '切线与焦距'
```

`/tmp/math-demo-narrated.verification.json` 中的 `publishable` 必须保持 false，直到中文语音试听、数学内容核对、音画同步与许可全部获得真实的验收证据。不要把其 `technical_pass_review_pending` 称为正式教学音质通过。`voiceover.py` 保留为旧版本兼容入口，新增项目优先使用本节的 `speech_pipeline.py`。