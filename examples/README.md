# Provenance / 历史案例

这里保留前一轮勾股定理 Pillow + FFmpeg 已验证工程的源代码与独立 proof/geometry/temporal/visual verifier。与 `scripts/` 新一轮通用绘图库**并存**，还没有全部迁移为新组件 API。

从 Skill 根目录：

```bash
python examples/render_video.py --fps 24 --output /tmp/pythagoras-verified.mp4
# 根据实际的媒体路径/参数再运行原场景的验证脚本
```

`geometry_model.py` 精确构造两套拼图，`verifier.py` 利用 SymPy/Shapely 检查面积/无重叠/无遗漏/全等，`visual_verifier.py` 从 MP4 解码抽帧。代码自包含在 `examples/`，与上一级 Skill 主模块没有硬编码路径依赖。示例视频 `pythagoras_verified.mp4` 是之前独立工程的实际产物、并非新 `scripts/demo.py` 的产物；旧视频的原核验记录不自动转移为最新 Skill 的 release gate。