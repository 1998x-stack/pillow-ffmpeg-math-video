# 中文数学 TTS 专项 Gotchas（S01–S20）

**适用范围**：eSpeak 1.x、eSpeak NG、由已批准音频文件接入的神经 TTS；规则首先用于声音脚本、分镜与实际 WAV，不声称当前引擎可以进行自动中文发音质量识别。

| ID | 故障 / 根因 | 限制 / 修复 | 检查与证据 |
|---|---|---|---|
| S01 | 把屏幕上的 LaTeX 原样传给 TTS | 显示公式和 `spoken_text` 分开存储 | `require_reviewed_narration` 拒绝 `\frac` 等裸命令 |
| S02 | 公式的量词、条件在朗读里消失 | `claim_id` 追踪已核数学主张；人审口播等价性 | claim→spoken→scene 矩阵 |
| S03 | `x²`、`x^2`、`x^{2}` 读法不一致 | 经受限语法 AST 规范化，未知宏拒绝猜测 | `tests/test_speech_v2.py` |
| S04 | `\frac` 分子、分母结合范围被读错 | 每个分组单独朗读，保留口语括号 | 整式/嵌套分式口播审核 |
| S05 | `\sqrt{a+b}` 被误读为仅根号 a | 根号内保持整体括号语义 | 根式数学习题专项测试 |
| S06 | 正负号混淆 `-3` 与 `a-b` | 区分一元负号和二元减法 | 函数/数列负例测试 |
| S07 | 下标 F1 与序号/变量 F×1 混淆 | 默认“F 下标一”；课堂讲解手动写“焦点一” | 数学术语听审 |
| S08 | 多音字“切线、重合、长度”等读错 | 专门发音词典及人工听审，调参不能自动纠正 | 人工音频审核记录 |
| S09 | 老版 eSpeak `zh` 与 NG `cmn` 混用 | 检测可执行文件自动选择缺省 voice | `EspeakBackend` 单测及 `--voices` |
| S10 | 出现 `Full dictionary is not installed for 'zh'` 仍宣称中文高质量 | 保存 stderr 并标记未通过人工发音验收 | verification.json 不自动 pass |
| S11 | 语速过高导致可懂度下降 | `max_tempo=1.25`，过长则拒绝、缩文稿或延长分镜 | `fit_speech` 负面测试 |
| S12 | 音频被 `-shortest` 意外截短 | 视频时长为主，合成后 ffprobe 验证 | 端到端媒体门禁 |
| S13 | 片段重叠导致语音混响 | 时间轴必须非重叠，分段 ID 唯一 | `validate_timeline` |
| S14 | WAV 为空、纯静音、削波 | 16 位 PCM 逐样本 RMS/peak/最长静音 | `inspect_pcm16_wav` |
| S15 | AAC priming / pad 导致起止偏移 | ffprobe + 解码分镜附近听审 | media + human_av_sync 分离 |
| S16 | 先前已有真人讲课音轨被覆盖 | 有音轨默认拒绝；明确审阅后另做混音 | `produce_narrated_video` 拒绝带音频输入 |
| S17 | 临时数据、用户音频或 token 被提交 | 临时目录、`.gitignore`、无密钥读入；不要嵌入私人音频 | 发布前文件白名单审核 |
| S18 | 使用第三方语音却缺许可证 | 外来 WAV 保留来源、许可、人工批准标记 | audio_license 独立门禁 |
| S19 | 自动 ASR/音高检查冒充人工试听 | 自动结果只为候选，人工发音/数学等价性另验 | `audio_pronunciation=not_run` |
| S20 | 未知 LaTeX 宏被无声丢弃，改变数学含义 | 使用明确支持的子集，遇未知结构拒绝 | `MathSpeechError` 负例 |

## 三类重要反例

**数学误导**：`\frac{x^2+1}{2}` 若错误只把 `x^2` 放在分子，会改变命题。必须保留大括号范围。

**时间误导**：4 秒的镜头被塞入 9 秒口播后不能无提示加速到 2.3x，更不能 `atrim` 截断尚未讲完的定理。

**听觉误导**：即使音频 RMS、AAC 码流和 WAV 峰值检查全部通过，也无法证明“长轴”“平方根”的中文发音准确。这一缺口只能用受控字典、试听和准确的旁白证据补上。

## `manim_math` 历史映射

参考 [仓库来源映射](manim-math-source-map.md) 的 H01/H02（中文字形和数学显示文本）、H11（随机性可复现）、H16（误覆盖原始音轨）。这些是**设计启发**，不应误称为 Pillow/TTS 已复现的 Manim API 故障。