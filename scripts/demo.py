"""Renders a self-contained drawing-primitives demo to MP4.

Usage (from skill root): python -m scripts.demo --output /tmp/skill-demo.mp4
This is an engineering demonstration, NOT a replacement for a Pythagoras proof.
"""
from __future__ import annotations
import argparse
import math
from pathlib import Path
from PIL import Image,ImageDraw
from .pillow_draw import (Viewport,Painter,create_canvas,smoothstep,resolve_font)
from .timeline import LayerCache,NumericTrack,Keyframe,frame_times
from .media import encode_rgb_frames,verify_media
from .verify import verify_right_angle,verify_pythagoras

WIDTH,HEIGHT=800,450
VP=Viewport(WIDTH,HEIGHT,xlim=(-1.6,11.6),ylim=(-3.0,4.2),margin=14)
DURATION=6.0
TRI=((0.,-2.),(3.,-2.),(0.,2.))


def build_base():
    im=create_canvas(VP,'#071728')
    painter=Painter(im,VP)
    painter.axes(1,1,grid='#14334A',axis='#42728F')
    # Title in pixel space: even captions must use true measured glyph bboxes.
    d=ImageDraw.Draw(im)
    from .pillow_draw import font_at
    d.rounded_rectangle((28,20,772,78),radius=12,fill='#14334A',outline='#3C708A',width=2)
    d.text((48,37),'Pillow + FFmpeg 数学绘图演示',font=font_at(painter.font_path,25),fill='#F3FAFF')
    return im


def state_frame(t,base):
    triangle=TRI
    progress=smoothstep((t-1.0)/2.0)
    # Demonstrate translation-only; geometry remains right-angled.
    shift=(progress*.8,progress*.3)
    current=tuple((p[0]+shift[0],p[1]+shift[1]) for p in triangle)
    layer=Image.new('RGBA',base.size,(0,0,0,0))
    p=Painter(layer,VP)
    p.polygon(current,fill='#275A71',outline='#6BE2F9',width=4)
    p.right_angle(current[0],current[1],current[2],size_px=22)
    p.segment_ticks(current[0],current[1],1,color='#FFCE72')
    p.segment_ticks(current[0],current[2],2,color='#FFCE72')
    p.point(current[0],radius=5,fill='#FFE09E')
    for letter,vertex,off in [('A',current[0],(-16,13)),('B',current[1],(12,12)),('C',current[2],(-14,-13))]:
        p.label(letter,vertex,name='vertex_'+letter,size=23,offset_px=off)
    p.segment_label('a = 3',current[0],current[1],offset_px=24,name='leg_a',size=18)
    p.segment_label('b = 4',current[0],current[2],offset_px=-35,name='leg_b',size=18)
    p.segment_label('c = 5',current[1],current[2],offset_px=25,name='hyp',size=18)
    p.arrow((5.3,2.7),(6.5,2.7),color='#F7D079',width=3,head_px=14)
    p.label('平移不改变长度与角度',(8.1,2.0),size=18)
    p.label('3² + 4² = 5²',(8.1,1.0),size=25,color='#FFD977')
    p.label('示例：非完整证明',(8.1,0.2),size=17,color='#9CB8C9')
    return layer


def render(output:Path,fps:int=15):
    verify_pythagoras(3,4);verify_right_angle(TRI[1],TRI[0],TRI[2])
    base=build_base();cache=LayerCache(base)
    times=list(frame_times(fps,DURATION))
    def frames():
        for t in times:
            # Cache constant periods with deterministic keys; no stale moving layers.
            key=('start',) if t<1.0 else (('end',) if t>=3.0 else ('moving',round(t,5)))
            overlay=state_frame(t,base) if getattr(cache,'_last_key',None)!=key else cache._last_dynamic
            yield cache.composite(overlay,key=key).convert('RGB')
    result=encode_rgb_frames(frames(),output,WIDTH,HEIGHT,fps)
    verify_media(output,WIDTH,HEIGHT,fps,DURATION)
    return {'duration':DURATION,'size':[WIDTH,HEIGHT], 'fps':fps,
            'cache_hits':cache.cache_hits,'frames':result['frames'],'video':str(output)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=Path('assets/demo_geometry.mp4'))
    p.add_argument('--fps',type=int,default=15)
    args=p.parse_args()
    import json
    print(json.dumps(render(args.output,args.fps),ensure_ascii=False,indent=2))

if __name__=='__main__':main()