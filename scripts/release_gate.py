"""Fail-closed gate evaluation. Never auto-approve human review.

Usage: python -m scripts.release_gate --input gates.json --output release_manifest.json
Release does not actually upload, publish or overwrite anything.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED=('proof','geometry','topology','labels','temporal','raster','media','decoded_frames','human_review')
AUDIO_REQUIRED=('audio_technical','audio_pronunciation','audio_av_sync','audio_license')


def evaluate(gates:dict, *, audio_requested:bool=False)->dict:
    required=REQUIRED + (AUDIO_REQUIRED if audio_requested else ())
    statuses={k:gates.get(k,{'status':'not_run'}) for k in required}
    invalid=[k for k,st in statuses.items() if not isinstance(st,dict) or
             st.get('status') not in ('pass','fail','not_run','blocked')]
    if invalid:raise ValueError(f'invalid gate statuses: {invalid}')
    return {'status':'pass' if all(statuses[k]['status']=='pass' for k in required) else 'blocked',
            'publishable':all(statuses[k]['status']=='pass' for k in required),
            'gates':statuses,'not_passed':[k for k in required if statuses[k]['status']!='pass']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--audio-required',action='store_true',help='require independent audio gates')
    args=p.parse_args()
    data=json.loads(args.input.read_text(encoding='utf8'))
    outcome=evaluate(data.get('gates',{}),audio_requested=args.audio_required)
    outcome['source_file_sha256']=hashlib.sha256(args.input.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(outcome,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(outcome,indent=2,ensure_ascii=False))
    raise SystemExit(0 if outcome['publishable'] else 2)

if __name__=='__main__':main()