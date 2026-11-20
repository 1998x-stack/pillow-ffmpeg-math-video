"""Drawing-only benchmark of full redraw vs static-layer caching.

Run: python -m scripts.benchmark --samples 100 --output /tmp/bench.json
No FFmpeg involved; comparisons are frame-exact RGBA before H.264.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from .demo import build_base,state_frame
from .timeline import LayerCache


def benchmark(samples:int=120):
    if samples<=1:raise ValueError('samples >1')
    times=[i*6/samples for i in range(samples)]
    t=time.perf_counter()
    original=[]
    for at in times:
        frame=build_base();frame.alpha_composite(state_frame(at,frame))
        original.append(frame)
    baseline=time.perf_counter()-t

    base=build_base();cache=LayerCache(base)
    t=time.perf_counter()
    optimized=[]
    for at in times:
        key=('static_start',) if at<1 else (('static_end',) if at>=3 else ('moving',round(at,6)))
        if key==getattr(cache,'_last_key',None):
            dyn=cache._last_dynamic
        else:
            dyn=state_frame(at,base)
        optimized.append(cache.composite(dyn,key=key))
    cached=time.perf_counter()-t
    equality=all(a.tobytes()==b.tobytes() for a,b in zip(original,optimized))
    if not equality:raise AssertionError('optimized output differs from full redraw')
    return {'samples':samples,'baseline_draw_s':round(baseline,5),
            'cached_draw_s':round(cached,5),'speedup_x':round(baseline/cached,3),
            'cache_hits':cache.cache_hits,'pixel_equality':'pass',
            'scope':'Pillow drawing ONLY; excludes FFmpeg encoding'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=120)
    p.add_argument('--output',type=Path)
    a=p.parse_args();r=benchmark(a.samples)
    print(json.dumps(r,indent=2,ensure_ascii=False))
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf8')

if __name__=='__main__':main()