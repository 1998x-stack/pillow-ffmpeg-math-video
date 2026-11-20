"""Additional Pillow-specific composable 2-D math teaching primitives.

These helpers require scripts.pillow_draw.Painter and make no claim of
performing symbolic proofs. All geometry is supplied in math coordinates.
"""
from __future__ import annotations
import math
from typing import Callable
from PIL import ImageDraw
from .pillow_draw import Painter, Point, Color


def dashed_segment(p:Painter,a:Point,b:Point,*,dash_px:float=14,gap_px:float=8,
                   color:Color='#9ED8F7',width:int=3)->int:
    """Dash lengths are pixel widths; segment position is from math coords."""
    if dash_px<=0 or gap_px<0 or width<1:raise ValueError('invalid dash style')
    x0,y0=p.px(a);x1,y1=p.px(b)
    dx=x1-x0;dy=y1-y0;total=math.hypot(dx,dy)
    if total<1:raise ValueError('degenerate dashed segment')
    covered=0;count=0;unit=(dx/total,dy/total)
    while covered<total:
        end=min(total,covered+dash_px)
        aa=(round(x0+covered*unit[0]),round(y0+covered*unit[1]))
        bb=(round(x0+end*unit[0]),round(y0+end*unit[1]))
        p.draw.line([aa,bb],fill=color,width=width)
        covered=end+gap_px;count+=1
    return count


def bezier_curve(p:Painter,p0:Point,p1:Point,p2:Point,p3:Point,*,samples:int=80,
                 color:Color='#62D5F6',width:int=3):
    """Draw a world-coordinate cubic Bezier; mathematical control points."""
    if samples<2:raise ValueError('sample count too small')
    def q(t):
        u=1-t
        return tuple(u*u*u*p0[d]+3*u*u*t*p1[d]+3*u*t*t*p2[d]+t*t*t*p3[d]
                     for d in (0,1))
    coords=[q(i/samples) for i in range(samples+1)]
    p.polyline(coords,fill=color,width=width)
    return coords


def parametric_curve(p:Painter,f:Callable[[float],Point],start:float,end:float,*,samples:int=500,
                     color:Color='#6CD6ED',width:int=3,max_jump_px:float=110):
    """Break paths on domain errors, non-finite values, or large screen jumps.

    This is *not* proof of mathematical continuity or domain completeness.
    """
    if not start<end or samples<2:raise ValueError('invalid parametric interval')
    chunks=[];chunk=[];last=None
    for i in range(samples+1):
        t=start+(end-start)*i/samples
        try:
            at=f(t)
            x,y=float(at[0]),float(at[1])
            if not math.isfinite(x) or not math.isfinite(y):raise ValueError('nonfinite')
            if not p.viewport.inside((x,y)):raise ValueError('off screen')
            current=p.px((x,y))
            if last is not None and math.dist(current,last)>max_jump_px:
                if len(chunk)>1:chunks.append(chunk)
                chunk=[]
            chunk.append((x,y));last=current
        except (OverflowError,ValueError,ZeroDivisionError,IndexError,TypeError):
            if len(chunk)>1:chunks.append(chunk)
            chunk=[];last=None
    if len(chunk)>1:chunks.append(chunk)
    for pts in chunks:p.polyline(pts,fill=color,width=width)
    return len(chunks)


def dimension_line(p:Painter,a:Point,b:Point,label:str,*,offset_px:float=30,
                   color:Color='#F9D481',font_size:int=20,name:str|None=None):
    """Dimension/length annotation offset normal to the *actual* segment.

    The display is a visual annotation; check measured length independently.
    """
    x0,y0=p.px(a);x1,y1=p.px(b)
    dx=x1-x0;dy=y1-y0;length=math.hypot(dx,dy)
    if length<2:raise ValueError('degenerate dimension line')
    nx,ny=-dy/length,dx/length
    a1=(round(x0+nx*offset_px),round(y0+ny*offset_px))
    b1=(round(x1+nx*offset_px),round(y1+ny*offset_px))
    p.draw.line([a1,b1],fill=color,width=2)
    # Witness lines from exact object endpoints to offset dimension line.
    p.draw.line([(x0,y0),a1],fill=color,width=1)
    p.draw.line([(x1,y1),b1],fill=color,width=1)
    for x,y,side in [(a1[0],a1[1],1),(b1[0],b1[1],-1)]:
        tx,ty=dx/length*side,dy/length*side
        p.draw.line([(x,y),(round(x+tx*10+nx*5),round(y+ty*10+ny*5))],fill=color,width=2)
        p.draw.line([(x,y),(round(x+tx*10-nx*5),round(y+ty*10-ny*5))],fill=color,width=2)
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    return p.label(label,mid,name=name,size=font_size,color=color,
                   offset_px=(nx*(offset_px+17),ny*(offset_px+17)))


def tangent_and_normal(p:Painter,point:Point,slope:float,*,half_length:float=1.1,
                       tangent_color:Color='#F0C86E',normal_color:Color='#8BD8F2',width:int=2):
    """Draw tangent and normal at a point using mathematical slope.

    For a vertical tangent use math.inf. A finite tangent and its normal are
    orthogonal in the model regardless of pixel aspect ratio.
    """
    if half_length<=0 or math.isnan(slope):raise ValueError('invalid tangent')
    if math.isinf(slope):u=(0.,1.)
    else:
        s=1/math.hypot(1,slope);u=(s,s*slope)
    v=(-u[1],u[0]);x,y=point
    t0=(x-half_length*u[0],y-half_length*u[1]);t1=(x+half_length*u[0],y+half_length*u[1])
    n0=(x-half_length*v[0],y-half_length*v[1]);n1=(x+half_length*v[0],y+half_length*v[1])
    p.line(t0,t1,fill=tangent_color,width=width)
    p.line(n0,n1,fill=normal_color,width=width)
    p.point(point,radius=5)
    return {'tangent':(t0,t1),'normal':(n0,n1)}


def labeled_number_line(p:Painter,start:float,end:float,y:float,*,tick:float=1.0,
                        labels:bool=True, tick_px:int=8,color:Color='#C2DDF1'):
    if not start<end or tick<=0:raise ValueError('invalid number line')
    p.arrow((start,y),(end,y),color=color,width=2,head_px=10)
    first=math.ceil(start/tick)
    positions=[]
    j=first
    while j*tick<end-1e-8:
        x=j*tick;px,py=p.px((x,y))
        p.draw.line((px,py-tick_px,px,py+tick_px),fill=color,width=2)
        if labels:
            txt=f'{x:g}'
            p.label(txt,(x,y),size=17,anchor='mt',offset_px=(0,13),color=color,
                    name=f'tick-{j}')
        positions.append(x);j+=1
        if j-first>500:raise ValueError('too many ticks')
    return positions


def callout(p:Painter,text:str,at:Point,target:Point,*,font_size:int=19,
            foreground:Color='#EAF5FF',background:Color='#173C58',
            outline:Color='#5BBEDD',padding:int=9,name:str|None=None):
    """Pixel rounded label balloon with pointer to model point; checked bbox."""
    x,y=p.px(at)
    from .pillow_draw import font_at
    f=font_at(p.font_path,font_size)
    b=p.draw.textbbox((x,y),text,font=f,anchor='mm')
    r=(b[0]-padding,b[1]-padding,b[2]+padding,b[3]+padding)
    if r[0]<0 or r[1]<0 or r[2]>p.viewport.width or r[3]>p.viewport.height:
        raise ValueError('callout outside safe canvas')
    # Arrow belongs underneath the balloon.
    tip=p.px(target)
    p.draw.line([(x,y),tip],fill=outline,width=2)
    p.draw.rounded_rectangle(r,radius=8,fill=background,outline=outline,width=2)
    p.draw.text((x,y),text,font=f,anchor='mm',fill=foreground)
    if name:
        if name in p.recorded_labels:raise ValueError(f'duplicate callout {name}')
        p.recorded_labels[name]=r
    return r


def polygon_highlight(p:Painter,points:list[Point],*,color:Color=(255,215,110,70),
                      outline:Color='#E9D386',width:int=3):
    """Draw translucent highlighted region; use RGBA canvas, no RGB pasting."""
    if p.image.mode!='RGBA':raise ValueError('polygon_highlight needs RGBA')
    p.polygon(points,fill=color,outline=outline,width=width)