"""Validated seconds-based narration timeline; exact claims and subtitle cues."""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class NarrationSegment:
    segment_id: str
    start: float
    end: float
    spoken_text: str
    claim_id: str
    subtitle: str = ''


def validate_timeline(rows: list[NarrationSegment], duration: float, gap: float=0.0) -> list[NarrationSegment]:
    if not rows:raise ValueError('empty narration timeline')
    if not math.isfinite(duration) or duration<=0:raise ValueError('invalid duration')
    last=0.0; ids=set()
    for r in rows:
        if not r.segment_id or r.segment_id in ids:raise ValueError('segment ID missing or duplicated')
        ids.add(r.segment_id)
        if not r.claim_id:raise ValueError('claim_id missing')
        if not r.spoken_text.strip():raise ValueError('blank narration')
        if not all(math.isfinite(x) for x in (r.start,r.end)):raise ValueError('non-finite time')
        if not (0<=r.start<r.end<=duration+0.001):raise ValueError('segment time out of range')
        if r.start < last+gap-0.000001:raise ValueError('overlap or insufficient gap')
        last=r.end
    return rows


def srt_timestamp(t:float)->str:
    milliseconds=round(t*1000)
    h,milliseconds=divmod(milliseconds,3600000)
    m,milliseconds=divmod(milliseconds,60000)
    s,ms=divmod(milliseconds,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def subtitle_srt(rows:list[NarrationSegment])->str:
    return '\n'.join(f'{i}\n{srt_timestamp(r.start)} --> {srt_timestamp(r.end)}\n{r.subtitle or r.spoken_text}\n'
                     for i,r in enumerate(rows,1))