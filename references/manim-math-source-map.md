# manim_math → Pillow/FFmpeg 数学视频 Skill 溯源映射

参考仓库：[`1998x-stack/manim_math`](https://github.com/1998x-stack/manim_math)，查询分支 `main`，检索日期 2026-11-20。这里的链接用于设计溯源；本 Skill 不要求联网运行，也**不会断言历史审计发现必然仍存在于最新课程源码**。

| 已查阅文件 | 实际设计经验 | 在本 Skill 中落点 |
|---|---|---|
| [skills/source/manim-video-production/SKILL.md](https://github.com/1998x-stack/manim_math/blob/main/skills/source/manim-video-production/SKILL.md) | `math_claim → validated_data → screen_object → checkpoint`、证据分层、故障 fail-closed | `SKILL.md`、`verification-contract.md` |
| [skills/source/manim-video-production/references/repository-gotchas-and-patterns.md](https://github.com/1998x-stack/manim_math/blob/main/skills/source/manim-video-production/references/repository-gotchas-and-patterns.md) | H01–H16、观察故障与潜在风险分级；历史问题不等于最新成片故障 | `gotchas.md` Pxx 分类、`observed/risk/verified` 标签 |
| [docs/engineering/historical-gotchas.md](https://github.com/1998x-stack/manim_math/blob/main/docs/engineering/historical-gotchas.md) | 中文公式混排、动态域、数学图形标注、对象身份、局部 RNG | Pillow Font/MathText、函数断点、标签绑定、对象 ID |
| [docs/engineering/quality-gates.md](https://github.com/1998x-stack/manim_math/blob/main/docs/engineering/quality-gates.md) | 代码/数学/分镜/视频/媒体分别保存证据 | `verification-contract.md` |
| [docs/engineering/scene-workflow.md](https://github.com/1998x-stack/manim_math/blob/main/docs/engineering/scene-workflow.md) | 从教学契约→分镜→纯数学函数→渲染→真实关键帧→发布 | `SKILL.md` 工作流 |
| [docs/engineering/references/Error.md](https://github.com/1998x-stack/manim_math/blob/main/docs/engineering/references/Error.md) | 失败模式的文档可追溯性 | `gotchas.md` 条目需要原始路径/复现 |
| [docs/manim_geometry_precision_guide.md](https://github.com/1998x-stack/manim_math/blob/main/docs/manim_geometry_precision_guide.md) | 几何精度参考迁移入口 | `geometry-and-labels.md` |
| [tests/test_grade8_pythagorean_math.py](https://github.com/1998x-stack/manim_math/blob/main/tests/test_grade8_pythagorean_math.py) | 学科专项测试入口独立于渲染 | `tests/` 和 `examples/` |
| [skills/source/manim-video-production/scripts/runtime_probe.py](https://github.com/1998x-stack/manim_math/blob/main/skills/source/manim-video-production/scripts/runtime_probe.py) | 实际画面对象检查，比 AST 更强 | Pillow 标签 bbox、真实解码帧像素采样 |
| [skills/source/manim-video-production/scripts/production_check.py](https://github.com/1998x-stack/manim_math/blob/main/skills/source/manim-video-production/scripts/production_check.py) | 各 gate 记录事实，区分 preview 与 production | `scripts/verify.py`, `scripts/media.py` |

## 不应照搬的内容

- `MathTex` 默认中文/Unicode 度号、`Sector(inner_radius)`、`Rectangle(corner_radius)`、`self.play([])`、Manim updater 对象引用生命周期：**均为 Manim API 特有的故障模式**，不能声称 Pillow 存在这些 API。
- 应映射为 Pillow 原生风险：FreeType 中文字体缺 glyph、数学公式 MathText 解析/字形图层、`textbbox(anchor)`、`ImageDraw` y-down 与弧度正方向、路径移动后点标滞后、`Image.alpha_composite` 的 RGBA 要求、FFmpeg stdin 帧协议、脏区域缓存拖影。
- `manim_math` 默认竖屏 9:16 的课程规范不是本 Skill 强制默认画幅；先读取真实发布目标，默认示例是 16:9。竖屏需独立检查 UI 安全区。
- 没有当前分支的 Scene 实际运行视频、完整媒体检查和人审，不使用 `render_verified` 描述相关历史资产。