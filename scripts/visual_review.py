"""Decode REAL MP4 frames, generate deterministic storyboard contact sheet.

No OCR is used. Screenshot selection is only sample evidence, not a proof of
all video pixels. Manual sign-off should record findings against exact frames.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .media import probe_video
from .pillow_draw import resolve_font,font_at


def pick_timestamps(duration:float,n:int,seed:int=20261120,segments:int|None=None)->list[float]:
    if duration<=0 or n<1:raise ValueError('invalid time/sample count')
    segments = segments or n
    # Exactly n balanced segments + deterministic uniform jitter, no timestamps after final frame.
    rng=random.Random(seed)
    return sorted(((i+rng.uniform(.12,.88))/n)*duration for i in range(n))


def extract_frame(video:Path,t:float,destination:Path):
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',f'{t:.4f}','-i',str(video),
         '-frames:v','1','-y',str(destination)]
    subprocess.run(cmd,check=True,timeout=25)
    if not destination.exists() or destination.stat().st_size==0:
        raise RuntimeError('empty decoded screenshot')


def contact_sheet(video:Path,outdir:Path,n:int=8,seed:int=20261120,cols:int=2,
                  thumb:tuple[int,int]=(480,270))->dict:
    video=video.resolve();outdir=outdir.resolve()
    if not video.exists():raise FileNotFoundError(video)
    meta=probe_video(video);duration=float(meta['format']['duration'])
    outdir.mkdir(parents=True,exist_ok=True)
    ts=pick_timestamps(duration,n,seed)
    rows=(n+cols-1)//cols
    sheet=Image.new('RGB',(cols*thumb[0],rows*(thumb[1]+34)),'#f0f3f8')
    draw=ImageDraw.Draw(sheet)
    try:ft=font_at(resolve_font(),16)
    except FileNotFoundError:ft=ImageFont.load_default()
    manifest=[]
    for i,t in enumerate(ts):
        frame=outdir/f'frame_{i+1:02d}_{t:06.2f}s.png'
        extract_frame(video,t,frame)
        with Image.open(frame) as im:
            im=im.convert('RGB').resize(thumb,Image.Resampling.LANCZOS)
            x=(i%cols)*thumb[0];y=(i//cols)*(thumb[1]+34)
            sheet.paste(im,(x,y))
        label=f'Frame {i+1:02d}  |  t={t:.2f}s'
        draw.text((x+12,y+thumb[1]+8),label,font=ft,fill='#17354c')
        manifest.append({'index':i+1,'t':round(t,4),'path':frame.name,
                        'sha256':hashlib.sha256(frame.read_bytes()).hexdigest()})
    sheet_path=outdir/'contact_sheet.png';sheet.save(sheet_path)
    result={'video_relative_to_review':os.path.relpath(video,outdir),
            'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'duration':duration,'random_seed':seed,
            'selection':'stratified uniform with fixed seed','screenshots':manifest,
            'contact_sheet':str(sheet_path),
            'status':'screenshots_generated; human_review_required'}
    (outdir/'review_manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path)
    p.add_argument('--outdir',type=Path,default=Path('visual_review'))
    p.add_argument('--count',type=int,default=8)
    p.add_argument('--seed',type=int,default=20261120)
    args=p.parse_args()
    res=contact_sheet(args.video,args.outdir,args.count,args.seed)
    print(json.dumps(res,indent=2,ensure_ascii=False))

if __name__=='__main__':main()