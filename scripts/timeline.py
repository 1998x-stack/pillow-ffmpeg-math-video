"""Deterministic keyframe animation and cached RGBA layer compositor."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
import math
from PIL import Image
from .pillow_draw import smoothstep


@dataclass(frozen=True)
class Keyframe:
    time: float
    value: float


@dataclass(frozen=True)
class NumericTrack:
    frames: tuple[Keyframe, ...]
    easing: Callable[[float], float] = smoothstep

    def __post_init__(self):
        if len(self.frames)<2: raise ValueError("need >=2 keyframes")
        if any(not math.isfinite(f.time) or not math.isfinite(f.value) for f in self.frames):
            raise ValueError("keyframes must be finite")
        if any(a.time >= b.time for a,b in zip(self.frames,self.frames[1:])):
            raise ValueError("keyframes must be strictly chronological")

    def value_at(self,t:float)->float:
        if t<=self.frames[0].time:return self.frames[0].value
        if t>=self.frames[-1].time:return self.frames[-1].value
        for a,b in zip(self.frames,self.frames[1:]):
            if a.time<=t<=b.time:
                u=self.easing((t-a.time)/(b.time-a.time))
                if not 0<=u<=1:raise ValueError("easing out of bounds")
                return a.value+(b.value-a.value)*u
        raise AssertionError("unreachable")


@dataclass
class LayerCache:
    """Static composite cache, with optional dirty rectangles.

    Dirty rectangles are a rendering optimization, not a semantic guarantee.
    Compares pixel equality against full recomposition in tests.
    """
    static: Image.Image
    _last_dynamic: Image.Image|None = field(default=None,init=False)
    _last_result: Image.Image|None = field(default=None,init=False)
    cache_hits: int=0
    frames_composited: int=0
    dirty_pixels: int=0

    def __post_init__(self):
        if self.static.mode!="RGBA":raise ValueError("static layer must be RGBA")

    def composite(self,dynamic:Image.Image,key:object|None=None,
                  dirty_bbox:tuple[int,int,int,int]|None=None)->Image.Image:
        if dynamic.mode!="RGBA" or dynamic.size!=self.static.size:
            raise ValueError("dynamic must be same-size RGBA")
        if key is not None and hasattr(self,'_last_key') and key==self._last_key:
            self.cache_hits+=1
            return self._last_result.copy()
        if dirty_bbox is not None and self._last_result is not None:
            x0,y0,x1,y1=dirty_bbox
            if not (0<=x0<=x1<=self.static.width and 0<=y0<=y1<=self.static.height):
                raise ValueError("dirty rectangle out of bounds")
            out=self._last_result.copy()
            # Rebuild BOTH source layers in crop; transparent removals work.
            crop=self.static.crop((x0,y0,x1,y1))
            crop.alpha_composite(dynamic.crop((x0,y0,x1,y1)))
            out.paste(crop,(x0,y0))
            self.dirty_pixels+=(x1-x0)*(y1-y0)
        else:
            out=self.static.copy();out.alpha_composite(dynamic)
            self.dirty_pixels+=out.width*out.height
        self._last_result=out
        self._last_dynamic=dynamic
        self._last_key=key
        self.frames_composited+=1
        return out.copy()


def bbox_union(boxes:list[tuple[int,int,int,int]],size:tuple[int,int],padding:int=3):
    if not boxes:return (0,0,0,0)
    return (max(0,min(b[0] for b in boxes)-padding),
            max(0,min(b[1] for b in boxes)-padding),
            min(size[0],max(b[2] for b in boxes)+padding),
            min(size[1],max(b[3] for b in boxes)+padding))


def frame_times(fps:int,duration:float):
    if fps<=0 or duration<=0:raise ValueError("invalid fps or duration")
    n=round(fps*duration)
    if not math.isclose(n,fps*duration,rel_tol=0,abs_tol=1e-8):
        raise ValueError("duration*fps must produce an integer number of frames")
    for i in range(n):yield i/fps