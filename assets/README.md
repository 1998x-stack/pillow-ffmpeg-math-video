# Assets / 素材政策

- `palette.json`：配色 token，供 Pillow 与 Manim 共用；颜色对比度须按实际镜头检查。
- `demo_geometry.mp4`：由 `python -m scripts.demo` 渲染的演示媒体（若此文件存在）。
- `demo_geometry_contact_sheet.png`：从实际 MP4 解码抽帧（若此文件存在）。
- 不随 Skill 分发系统字体：部署者在本地安装 Noto Sans CJK、PingFang 或微软雅黑等合适字体，并检查数学符号回退。
- 不随 Skill 分发未经明确授权的音轨、图片或视频；素材需记录来源、许可、版本、SHA256。
- 所有发布媒体和临时帧写到输出目录，避免覆盖源资源。