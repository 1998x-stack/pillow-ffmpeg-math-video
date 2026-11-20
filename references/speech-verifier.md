# 数学配音 Verifier 契约（分层、否决、证据）

## 目标

对每个结论保留可追溯链：`math_claim_id → screened_formula → explicitly_authorized_spoken_text → recorded_wav_sha256 → segment_time → encoded_MP4 → human_review`。

| 层级 | 机器检查 | 人工检查 | 必须保存的证据 |
|---|---|---|---|
| A0 数学口播 | `spoken_text` 非空、无原样 LaTeX、具 claim_id | 定理前提、量词、结论语义不丢失 | 数学证明、字幕与旁白对照 |
| A1 语音后端 | 探测 espeak/NG 路径与 voice、捕获 stderr | 选择教学声音 | 引擎版本、词典警告、来源及许可 |
| A2 时间线 | start/end、唯一 ID、顺序、无重叠 | 讲解节奏是否合理 | 分镜原始 JSON |
| A3 声学 | PCM WAV、RMS、峰值、长静音、时长 | 破音/杂音/语气 | acoustic report + WAV |
| A4 剪辑 | 超长拒绝，tempo <=1.25 | 语速是否可懂 | tempo、lead、tail 每段明细 |
| A5 媒体 | FFprobe MP4 视频流/音频流/时长 | 首尾/衔接试听 | ffprobe、编码日志、成片 |
| A6 发音 | 可选 ASR 做提示，**不能自动认证** | 多音字/数字/公式口播准确性 | human_pronunciation reviewer 与时间戳 |
| A7 音画对应 | 场景时间与声道时间对齐 | 字幕、画面和讲解同步 | 人工关键时间戳 |
| A8 资源许可 | WAV provenance 必填；不隐式丢弃原音轨 | 判断商业传播授权 | license note |

机器技术状态与教学发布状态分离。`technical_pass_review_pending` **不是** release-pass。运行发布门禁时应使用 `python -m scripts.release_gate ... --audio-required`；缺少 `audio_pronunciation`、`audio_av_sync` 或 `audio_license` 会 fail-closed。

## 为什么不能依靠 eSpeak 自身自动“验收发音”

eSpeak 不提供可靠的 Mandarin 教学语义判分器。词典不完整的 stderr 可作为风险证据；没有 stderr 不表示发音正确。自动转写、音素对齐、字符级发音检查只能辅助定位，应由能听到音频的人核对。

## 大规模视频生产的缓存键

`SHA256(backend_identifier + version + voice + speed + pitch + normalized_spoken_text + glossary_version)`。只缓存 WAV；不同语义/改写的口播必须得到不同键。来源 WAV/第三方音色和完整配置不得泄漏 API 密钥、登录信息或用户私人声音。