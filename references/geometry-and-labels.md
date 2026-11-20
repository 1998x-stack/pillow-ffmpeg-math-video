# 二维几何与点标：从数学对象到像素对象

## 三层坐标不可混淆

1. **数学层**：点 `A=(0,0)`、`B=(a,0)`、`C=(0,b)`，单位可以是米、厘米或抽象长度。计算线段长度、角、面积、点是否属于区域始终使用数学坐标。
2. **布局层**：为每个对象分配逻辑画幅、世界坐标、相机缩放和可用标题/字幕安全区；具有稳定 ID，标签依附真实点或真实边。
3. **栅格层**：Pillow `pixel=(x,y)`，原点左上，y 向下；`stroke`, `font.size`, `arrowhead` 是像素宽度，不是数学长度。

要求：屏幕呈现真正的欧式形状时世界 x/y 等比例；非等比例图表不得从像素推导角度、真实距离或面积。

## 可复制代码：正确绘制直角和标签

```python
from scripts.pillow_draw import Viewport, Painter, create_canvas

v = Viewport(1280, 720, xlim=(-8,8), ylim=(-4.5,4.5))
p = Painter(create_canvas(v), v)
A, B, C = (0,0), (3,0), (0,4)
p.polygon([A,B,C], fill='#275A71', outline='#6BE2F9')
p.right_angle(A, B, C)              # 实际点积与退化检查
p.segment_label('a', A, B, offset_px=20, name='leg_a')
p.segment_label('b', A, C, offset_px=-20, name='leg_b')
p.segment_label('c', B, C, offset_px=20, name='hypotenuse')
```

危险：三角形移动时，`A,B,C` 必须随同一数学变换更新；不可仅移动多边形而留下旧点标。

## 四块全等直角三角形：勾股定理严格拼排

设 `a,b>0`, `s=a+b`。第一种外正方形由四块面积为 `ab/2` 的全等直角三角形与边长 `c` 的中心正方形拼成。第二种相同的大正方形由**同样四块全等三角形**与边长 `a`、`b` 的两个小正方形拼成；三角形只平移，不能缩放/形变。外正方形与三角形面积两次相同，因此互补面积相同。

```text
outer = Polygon([(0,0),(s,0),(s,s),(0,s)])
A:  triangles + [central_square]
B:  moved_triangles + [square_a,square_b]
```

**验证方式**：`verify_polygon_partition()` 对两种结构各自核对：合法 polygons、均在外部以内、每对 polygon 交叠面积 ~0、整个 union 与 outer 对称差面积 ~0。再检验中心四边形每条边长度平方 `a²+b²`、相邻边点积 0，才能把它标记为“正方形”。`scripts/verify.py:verify_rigid_translation()` 检验所有移动顶点拥有共同 translation 向量。该工程完整旧场景参考 `examples/geometry_model.py` + `examples/verifier.py`。

## 标签的几何规范

- 点标 `A`：绑定 `vertex_id`，偏移仅用于可读性；当视角变化，重新计算而不是使用旧屏幕坐标。
- 边 `a`：绑定 `segment_id`，用数学中点与投影到像素的法向方向；保证文案正确时，再由布局器选择朝内/朝外侧。
- 角标 `α`：绑定 `angle(vertex, start_ray, end_ray)`，明确优角/劣角与顺逆时针；画右角标记前做点积校验。
- 区域 `a²`：绑定实际 polygon，使用面积质心（不是任意多边形顶点平均值）与边界内部 padding；必须验证真实文字 bbox 全部可见。
- 公式 `c² = a²+b²`：绑定 `claim_id` + proof steps，不能因屏幕形状看似一样就直接判真。

## geometry helper 对应关系

| 概念 | 实现 | 负例 |
|---|---|---|
| 区域符号面积 | `scripts/geometry.py:polygon_signed_area` | 退化/自相交需要更高级几何库 |
| 面积质心 | `scripts/geometry.py:centroid` | 共线多边形直接拒绝 |
| 刚体变换 | `scripts/geometry.py:transform_point` | scale≤0 拒绝；严格“仅平移”不能放开 angle/scale |
| 点在边投影 | `scripts/geometry.py:project_to_segment` | 零长线段拒绝 |
| 角/直角 | `scripts/pillow_draw.py:angle_arc/right_angle` | 小于 ε 的向量拒绝 |
| 多边形无缺口 | `scripts/verify.py:verify_polygon_partition` | 缺一块/重叠应 fail |
| 标注安全区 | `scripts/verify.py:verify_label_boxes/verify_reserved_regions` | 标注撞标题应 fail |

## 推荐关键帧集合

`before`, `during_25%`, `during_50%`, `during_75%`, `after`, `claim_visible`, `final_hold`。动态中间过程可能不是合法铺砌，所以**不能**在移动中途写“这一时刻刚好完整铺满外正方形”；只能说明“三角形正在平移，目标拼法即将形成”。