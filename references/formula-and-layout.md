# 数学公式栅格排版、中文字体和语义公式变化

## 三种公式输入策略

1. 普通中文和单字符符号：`ImageFont.truetype(font_path,size)` + `Painter.label()`，通过 `textbbox()` 核验。适合点标、标题、单行字幕。
2. 常见数学式：`scripts/formulas.py:math_sprite(r'\frac{a}{b}', fontsize=...)`，使用 Matplotlib MathText 生成透明 PNG，再 `paste_math()` 叠到 RGBA 画面。MathText **只支持 TeX 风格数学语法的子集**，不是完整 LaTeX 环境；若失败不得伪造替代文字。
3. 多行公式推导、复杂排版、任意字形路径精确匹配：使用 Manim/专门 TeX 引擎或 MathJax/KaTeX → PNG/SVG 的外部受控服务。将公式栅格结果缓存；不得每帧调用独立 LaTeX 编译。

## 明确的 FormulaToken 语义 ID

```python
from scripts.formulas import FormulaToken, matching_token_states
before = [
    FormulaToken('lhs_x','x',(100,50)),
    FormulaToken('add','+', (160,50))
]
after = [
    FormulaToken('lhs_x','x',(320,50)),
    FormulaToken('equals','=',(380,50))
]
print(matching_token_states(before, after, .5))
```

`lhs_x` 会移动；`add` 逐渐淡出；`equals` 逐渐淡入。同一阶段重复 ID、同 ID 的 LaTeX 内容变化会拒绝。公式表达式变换是否数学等价，必须另由 SymPy/数学规则核验；token 动画本身不提供代数证明。

## 字体与 UI 边界

- 文字 bbox 必须使用**真正渲染**时的同一字体、字号、描边、anchor 与 pixel offset。
- 字体选择使用 `resolve_font()` 显式路径；部署环境无 CJK 字体时记录 `blocked`。不能依赖 Pillow 默认位图字体绘制中文。
- 文字初始 anchor 位置虽然在画布内，不代表完整字形 bbox 没越界。
- 竖屏额外保留上方标题安全区、底部评论与互动 UI；安全区与发布平台相关，不能复用一个硬编码绝对值覆盖所有比例。
- 对高光/阴影文字，bbox 还需补充滤镜半径；将真实字形渲染结果的 bbox 记录在 verifier 证据中。

## 公式与几何联动

一条屏幕公式应该关联具体 `claim_id` 和图元：

```json
{
  "claim_id": "square_area_a",
  "text": "a^2",
  "geometry_id": "square_a",
  "source": "area(square_a)",
  "semantic": "measured_area"
}
```

不允许仅根据展示顺序推断它的几何含义。Area label 应来自真实 polygon，可用外部 Shapely 检测整个文字盒子落在区域内。若勾股定理拼图的两个面积区域交换位置，公式 ID 和验证器也必须跟随真实对象，而不是硬编码屏幕左右。

## 不应自行重新实现的部分

逐字形拓扑形变、完整 LaTeX 排版、断行自动讲解和 3D 遮挡属于成本很高的领域，除非大量课程明确需要并有回归集，否则优先复用成熟引擎；保留本 Skill 的渲染后端作为字幕/图形叠层与批量编码器。