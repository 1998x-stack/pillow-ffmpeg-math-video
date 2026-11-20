"""Inspect eSpeak IPA/diagnostic output; NEVER marks pronunciation as correct.

Example: python -m scripts.pronunciation_probe '切线与焦距'
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def probe(text:str, engine:str|None=None, voice:str|None=None)->dict:
    if not text.strip():raise ValueError('empty text')
    engine=engine or shutil.which('espeak-ng') or shutil.which('espeak')
    if not engine:raise RuntimeError('eSpeak engine unavailable')
    voice=voice or ('cmn' if 'espeak-ng' in Path(engine).name else 'zh')
    p=subprocess.run([engine,'-v',voice,'--ipa','-q',text],capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError(f'phoneme command failed: {p.stderr[-1000:]}')
    return {'engine':engine,'voice':voice,'text':text,
            'ipa_candidate':p.stdout.strip(),'warning':p.stderr.strip(),
            'human_pronunciation':'not_run','note':'IPA candidate cannot certify Mandarin correctness'}


def main():
    p=argparse.ArgumentParser();p.add_argument('text');p.add_argument('--engine');p.add_argument('--voice')
    a=p.parse_args();print(json.dumps(probe(a.text,a.engine,a.voice),ensure_ascii=False,indent=2))
if __name__=='__main__':main()