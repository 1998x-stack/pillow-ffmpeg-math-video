# Pillow + FFmpeg 高性能渲染架构和生产落地

## 模型→状态→图层→原始帧→视频

```text
math_spec / storyboards
      ↓ independent math / symbolic model
scene_graph (semantic object ID, geometry, label relationships)
      ↓ timeline.evaluate(t) - deterministic from t, not previous frame
frame_state(t)
      ↓ Painter (Pillow RGBA)
static_background + accumulated geometry + dynamic overlay
      ↓ LayerCache (safe dirty union when proven correct)
RGBA full frame → RGB rawvideo bytes → FFmpeg stdin → H.264 / MP4
      ↓ ffprobe + decoded screenshot verifier + human review
verification.json / contact_sheet / release_manifest
```

## 缓存三层，按收益递进

### Level 1：静态层缓存（P0）

背景、网格、固定表格、标题、图例分别静态生成一次，复制并叠加动态帧。成本 O(WH) 的拷贝仍存在，但消除了大量 Python `ImageDraw` 对象绘制。适合所有课程，正确性风险较低。

### Level 2：累积层缓存（P1）

树的已生成节点、已经稳定出现的笔画可以持续累积到单独 RGBA 层。遇到对象需要删除、颜色变化、顺序调整时，相关层必须重新构造；**不能**假设所有对象永不更新。在任务日志中记录 `new_objects`, `removed_objects`, `recomputed_regions`。

### Level 3：Dirty rectangles（P1，需要等价测试）

对当前帧和上一帧所有变化对象收集 `old bbox + new bbox + stroke/blur radius`，合并成重绘区域。只重合成区域，然后与“整张重绘”在 Pillow 原始 RGBA 空间逐字节对照；失败自动退回全量绘制并登记故障。这是正确性前提，不是用户可以跳过的性能开关。

`LayerCache` 只实现图层重合成，**不会**自动发现变化区域；调用者必须给出完整 bbox。对于移动背景/镜头、大范围擦除、大量透明叠层，使用全量重绘通常更安全。

## 基准与指标

基准必须同时保留：`content_version`, `math_spec_hash`, `render_version`, `Pillow_version`, `FFmpeg_version`, `font_path_or_hash`, `OS`, `CPU`, `width`, `height`, `fps`, `duration`, `cache_hit_rate`, `drawing_seconds`, `encoding_seconds`, `peak_RSS`, `output_bytes`, `verified_gate_status`。不得将原版 15 FPS 与新版 30 FPS 的耗时直接视为相同工作量的性能提升；要在同规格输出+相同内容场景下对比。

之前 Collatz 方案 120 个采样画面绘制提升约 3.31×，同 34 秒 30 FPS 的端到端测试约 1.63×：这是特定环境的历史实验记录，不是所有场景的性能保证；新 Skill 必须自己重新 benchmark。

## 减少 FFmpeg 原始字节吞吐

`rgb24` 单帧约 `W*H*3` 字节，1280×720 一帧 2,764,800B；30FPS 原始吞吐约 82.94MB/s（未计 Python 创建/拷贝）。如果实际帧完全静止，可用 FFmpeg 对图片生成 hold 片段，再合并，但要保持帧率/音轨对齐；短视频更适合固定 stdin pipe 统一编码。

- 预览时降低分辨率/FPS，但验证媒体参数必须与生产规格对应。
- 缓存相同的公式 sprite 和 glyph 图层，避免每帧重算 MathText 和 `ImageFont.truetype`。
- 动画时间精确由 `i/fps` 计算，`fps*duration` 必须是整数，避免重复/漏帧。
- `-pix_fmt yuv420p` 提升兼容性，但色度抽样会影响彩色细线，需检查编码后截图。

## Docker / MCP 的生产架构建议

```
client -> /mcp (submit_render, get_render_status, get_render_artifact)
       -> job validator (schema, math spec, asset manifest)
       -> queue + isolated worker (no arbitrary code by default)
       -> pillow renderer + ffmpeg process (timeout/resource caps)
       -> geometry+visual+media verification
       -> signed artifact manifest / object storage
```

实际 MCP 服务器尚未在本 Skill 中实现或部署，此图是未来接口设计，不应声称现成可用。严禁允许公网任意 Python 代码以宿主权限运行；必要时启用容器隔离、UID 降权、网络限制、内存/CPU/时间配额、审计日志、对象存储签名 URL、素材大小限制与授权。推荐 `JSON scene spec + 受信任函数注册表`，而非直接运行 AI 任意生成的脚本。

## 输出文件和失败恢复

- 使用唯一 job ID/随机临时目录，生成时保留 `stdout/stderr`、版本和 manifest。
- `ffmpeg` return code 非零，未产生输出、时长/音轨不符，一律 fail；不得返回 200 与“视频完成”标记。
- 生产渲染时可先写临时目录，验证后原子移动到最终路径；本 Skill 的 `encode_rgb_frames` 是最小单任务版本，只负责不覆盖已存在目标和异常清理，**不是跨进程原子发布系统**。
- 可复现时用 `seed`、渲染参数、数学模型数据版本与时间轴记录；任何随机数使用局部 RNG，避免改写全局状态。