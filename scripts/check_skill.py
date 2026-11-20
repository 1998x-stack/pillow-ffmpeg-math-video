"""Validate Skill's self-contained structure, local Markdown links and files."""
from __future__ import annotations
import re
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def run_checks():
    required=['SKILL.md','README.md','requirements.txt','references/gotchas.md',
              'references/verification-contract.md','references/manim-math-source-map.md',
              'scripts/pillow_draw.py','scripts/math_primitives.py','scripts/formulas.py',
              'scripts/timeline.py','scripts/geometry.py','scripts/verify.py',
              'scripts/visual_review.py','scripts/media.py','assets/palette.json',
              'scripts/speech_normalizer.py','scripts/speech_timeline.py',
              'scripts/audio_verifier.py','scripts/speech_pipeline.py',
              'scripts/tts/base.py','scripts/tts/espeak_backend.py',
              'scripts/tts/file_backend.py','references/pronunciation-gotchas.md',
              'references/speech-verifier.md','assets/math_pronunciation_zh.json']
    failures=[]
    for path in required:
        if not (ROOT/path).is_file():failures.append('missing: '+path)
    skill=(ROOT/'SKILL.md').read_text(encoding='utf8')
    if not re.match(r'^---\s*\nname:\s*pillow-ffmpeg-math-video\s*\ndescription:',skill):
        failures.append('invalid YAML frontmatter name/description')
    for doc in [ROOT/'README.md',ROOT/'SKILL.md',*list((ROOT/'references').glob('*.md'))]:
        contents=doc.read_text(encoding='utf8')
        # Local Markdown links only; remote links are informational.
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',contents):
            if target.startswith(('https://','http://','#','mailto:')):continue
            target=target.split('#')[0]
            if target and not (doc.parent/target).exists():failures.append(f'{doc.relative_to(ROOT)} -> {target}')
    prohibited=[str(f.relative_to(ROOT)) for f in ROOT.rglob('*')
                if f.is_file() and f.suffix.lower() in ('.ttf','.otf','.ttc','.woff','.woff2')]
    if prohibited:failures.append('bundled font binaries prohibited: '+', '.join(prohibited))
    return {'status':'pass' if not failures else 'fail','checks':len(required),'broken':failures}


if __name__=='__main__':
    result=run_checks()
    print(json.dumps(result,indent=2,ensure_ascii=False))
    raise SystemExit(0 if result['status']=='pass' else 1)