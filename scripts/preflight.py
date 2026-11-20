"""Report dependencies and actual media environment without downloading any assets.

Usage: python -m scripts.preflight [--json /tmp/preflight.json]
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
from .pillow_draw import resolve_font


def run_preflight():
    result={'status':'pass','packages':{},'tools':{},'font':None,'warnings':[]}
    for pkg in ['Pillow','sympy','shapely','matplotlib','pytest']:
        try:result['packages'][pkg]=importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            result['packages'][pkg]='blocked'
            result['status']='blocked'
    for name in ['ffmpeg','ffprobe']:
        path=shutil.which(name)
        if not path:
            result['tools'][name]='blocked';result['status']='blocked'
        else:
            cmd=subprocess.run([name,'-version'],capture_output=True,text=True,timeout=5)
            result['tools'][name]={'path':path,'version':cmd.stdout.splitlines()[0] if cmd.stdout else 'unknown'}
    try:
        result['font']=resolve_font()
        result['warnings'].append('Font path resolved; glyph coverage must still be visually reviewed.')
    except FileNotFoundError:
        result['font']='blocked';result['status']='blocked'
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--json',type=Path)
    args=ap.parse_args();result=run_preflight()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    raise SystemExit(0 if result['status']=='pass' else 2)

if __name__=='__main__':main()