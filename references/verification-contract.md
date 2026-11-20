# Verifier contract / 数学视频验证契约

所有 verifier 输出状态为 `pass | fail | blocked | not_run`，不得用 `warnings=0`、`CI green` 代替成片质量。`pass` 必须附执行命令、环境、待测版本、数量、阈值/随机种子、时间戳、产物哈希与原始 log 路径；`fail` 会阻止成片发布。课堂数学结论的 verifier 必须由**独立于绘图函数**的数学/几何计算生成预期值。

## 十二层分离

| Gate | 输入 | 检查 | 正例、负例 / 证据 |
|---|---|---|---|
| V01 Proof | 题目、假设、符号公式 | 公式逐条等价、定义域与条件 | SymPy 化简 + 课程正式证明、反例 |
| V02 Numeric/Property | 独立数学模型、参数空间 | 取样数值不变量、边界和退化 | 40+ 固定种子样本，不能冒充普遍证明 |
| V03 Geometry | 点、边、角、辅助线 | 点积、长度、共线、旋转/全等 | 故意 89° 直角、0 长度，需失败 |
| V04 Topology/Tiling | 真实多边形集合 | overlap/intersection/union/holes | Shapely 面积差；挪动顶点触发 fail |
| V05 Scene/Object ID | 模型几何与 screen object | 点标/边标从同一个对象导出 | 交换 a/b、删除对象、改 ID 需失败 |
| V06 Layout/BBox | 实际字体、实际 viewport | bbox 在安全区、不能覆盖关键图形 | C 标签移动撞标题应失败 |
| V07 Temporal | 关键帧、运动方程 | 单调/平滑、位置/全等不变量 | 非单调 easing、形变需失败 |
| V08 Render Engine | RGBA 图层、缓存/dirty | 对缓存结果与全量重合成逐像素比较 | 移动后旧 bbox 不清除需失败 |
| V09 Raster/Pixels | Pillow frame | 区域内部色彩/边缘位置/坐标映射 | 固定模型预期像素采样；颜色/像素容差 |
| V10 Actual MP4 | 编码结果 | ffprobe codec/fps/resolution/duration/audio | 错码率/时长/音轨需失败 |
| V11 Decoded Frames | MP4 抽帧 | 固定种子、转场边界、SHA256、相对 OCR-free 分析 | 真实抽帧 contact sheet 与审阅记录 |
| V12 Human Review | 真实 MP4、数学分镜 | 几何语义、证明流程、可读性、字幕音轨 | 审阅人/日期/时间点/修复结论 |

## release_manifest.json 最小字段

```json
{
  "artifact": "video.mp4",
  "scene": "pythagoras-dissection",
  "source_sha256": "<hash>",
  "math_spec_sha256": "<hash>",
  "render": {"width": 1280, "height": 720, "fps": 30, "duration_seconds": 37},
  "gates": {
    "proof": {"status": "pass", "evidence": ["symbolic-test.json"]},
    "geometry": {"status": "pass", "evidence": ["geometry.json"]},
    "topology": {"status": "pass", "evidence": ["tiling-check.json"]},
    "layout": {"status": "pass", "evidence": ["label-bbox.json"]},
    "temporal": {"status": "pass", "evidence": ["motion.json"]},
    "cache_equivalence": {"status": "pass", "evidence": ["pixel-diff.json"]},
    "media": {"status": "pass", "evidence": ["ffprobe.json"]},
    "decoded_frame_review": {"status": "pass", "evidence": ["contact_sheet.png", "visual_review.md"]},
    "human_review": {"status": "not_run", "evidence": []}
  },
  "publishable": false
}
```

`publishable` 只有按对应风险选择的必需 gates 全为 pass 才能由 release validator 设为 true；上述例子的 `human_review=not_run` 因而不可发布。分镜更新、数学证明更新、动态对象改变或配音改变时，原证据需要根据受影响范围重新运行，不能仅复用旧 checksum。

## 课程中常被误判的三个原则

**(1) 符号证明 ≠ 拼图正确**：`(a+b)^2 - 2ab = a²+b²` 正确，仍可能画错四块三角形。

**(2) 画面正确 ≠ 叙述正确**：真正的数轴轨迹可以被字幕错误地称作普遍证明。文案必须有证据绑定。

**(3) 随机像素采样 ≠ 全片逐像素认证**：JPEG/MP4 有损编码会改变颜色，像素采样应设置合理容差；截图抽样未覆盖的时刻状态标为“未抽到”，不能断言全帧正确。

## 本 Skill 中实际可以执行的 checks

```bash
python -m pytest -q
python -m scripts.demo --output /tmp/demo_math.mp4
python -m scripts.visual_review /tmp/demo_math.mp4 --outdir /tmp/viz --count 10 --seed 20261120
ffprobe -v error -show_streams -show_format -of json /tmp/demo_math.mp4
```

`tests/` 内含数学错误、图形碰撞、错直角、退化箭头、缓存像素等 Negative Tests。本 Skill 的 demo 是 2D 几何渲染功能演示，**不是勾股定理完整证明**；完整可参考 `examples/` 中可独立执行的上一阶段拼图案例。