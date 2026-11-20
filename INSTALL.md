# 安装与集成

## 1. 独立使用

```bash
unzip Pillow_FFmpeg_Math_Video_Skill_v1.zip
cd pillow-ffmpeg-math-video
python -m pip install -r requirements.txt
python -m scripts.preflight
python -m pytest -q
python -m scripts.demo --output /tmp/pillow-demo.mp4
python -m scripts.visual_review /tmp/pillow-demo.mp4 --outdir /tmp/video-review
```

`python -m scripts.release_gate --input assets/demo_gates.json --output /tmp/manifest.json` 返回非零是**预期行为**：示例并非一部完整的勾股定理证明，demo 缺少课程证明/正式人审，不能发布为已验证数学课程。

## 2. 作为 Skill 使用

将完整目录放入智能助手支持的 Skills 根目录（例如相应环境的 `skills/pillow-ffmpeg-math-video/`）。名称保持 `pillow-ffmpeg-math-video`，根目录放 `SKILL.md`；`references/`、`scripts/`、`assets/` 与 `tests/` 不要拆散。具体自动发现方式取决于目标产品，不保证所有产品都支持任意用户 Skills。

## 3. 与 manim_math 结合

此前 `manim_math` 正式工程已收敛为两个 Skill：`curriculum-prompt-suite` 和 `manim-video-production`。如果希望保持双 Skill 架构，**不必将第三个独立 Skill 注册为第三个调度路由**：可以将本 Skill 作为 `manim-video-production` 的 Pillow 渲染后端参考包，以适配层调用；把算法/验证契约复用到其 `scripts/`，不要复制 Manim 特有 API 故障。

如果明确需要三种独立任务路由，则可作为单独 `pillow-ffmpeg-math-video` Skill 安装。此 ZIP 没有自动改写/提交 `1998x-stack/manim_math` 仓库。

## 4. 验证深度

`tests/` 新内核自动测试；`examples/test_verified_video.py` 是旧的勾股定理课程专项测试。全量参考执行：

```bash
python -m pytest -q tests
cd examples
python -m pytest -q test_verified_video.py
```

视频和解码截图只是例子；针对新增课程需要新增该课数学证明、参数边界及其对应的 frame verifier。见 `references/verification-contract.md`。


## 5. v2 音轨（首次建议）

在 Ubuntu 安装 `sudo apt-get install ffmpeg espeak-ng fonts-noto-cjk`；macOS 可使用 `brew install ffmpeg espeak-ng`。运行 `python -m scripts.preflight` 检查环境。完整的数学音轨优先使用人工审阅过的中文讲解稿及经授权的外部 TTS WAV，由 `scripts.tts.file_backend.ReviewedWavBackend` 导入。

GitHub 源码分发不会自动包含演示 MP4 或第三方语音模型权重。构建系统不允许在已有音轨上无授权地替换声音。