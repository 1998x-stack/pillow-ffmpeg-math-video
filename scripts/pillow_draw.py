"""Pillow-native math primitives, with Cartesian coordinates and stable IDs.

IMPORTANT: every position is calculated from the actual geometric data, not
from a screenshot.  Pixel alpha is composited in RGBA before conversion to RGB.

Coordinate convention: geometry x-right/y-up; Pillow x-right/y-DOWN.
No font binaries are shipped; resolve locally installed font files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Sequence
import math
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageFilter

Point = tuple[float, float]
Color = str | tuple[int, int, int] | tuple[int, int, int, int]


def _finite(*numbers: float) -> None:
    if not all(math.isfinite(float(v)) for v in numbers):
        raise ValueError("non-finite drawing coordinate")


def smoothstep(u: float) -> float:
    if not math.isfinite(u):
        raise ValueError("non-finite progress")
    u = max(0.0, min(1.0, u))
    return u*u*(3 - 2*u)


def lerp(a: float, b: float, u: float) -> float:
    return a + (b-a) * u


def point_lerp(a: Point, b: Point, u: float) -> Point:
    return (lerp(a[0], b[0], u), lerp(a[1], b[1], u))


@dataclass(frozen=True)
class Viewport:
    width: int = 1280
    height: int = 720
    xlim: tuple[float, float] = (-7.5, 7.5)
    ylim: tuple[float, float] = (-4.21875, 4.21875)
    margin: int = 0

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0 or self.margin < 0:
            raise ValueError("invalid canvas size")
        if self.width <= 2*self.margin or self.height <= 2*self.margin:
            raise ValueError("margin exhausts viewport")
        if not self.xlim[0] < self.xlim[1] or not self.ylim[0] < self.ylim[1]:
            raise ValueError("invalid cartesian bounds")
        _finite(*self.xlim, *self.ylim)

    def xy(self, p: Point) -> tuple[float, float]:
        _finite(*p)
        x = self.margin + (p[0]-self.xlim[0]) / (self.xlim[1]-self.xlim[0]) * (self.width-2*self.margin)
        y = self.height-self.margin - (p[1]-self.ylim[0]) / (self.ylim[1]-self.ylim[0]) * (self.height-2*self.margin)
        return x, y

    def cartesian(self, pixel: Point) -> Point:
        _finite(*pixel)
        x = self.xlim[0] + (pixel[0]-self.margin)/(self.width-2*self.margin)*(self.xlim[1]-self.xlim[0])
        y = self.ylim[0] + (self.height-self.margin-pixel[1])/(self.height-2*self.margin)*(self.ylim[1]-self.ylim[0])
        return x, y

    def inside(self, p: Point, inset: int = 0) -> bool:
        x,y=self.xy(p)
        return inset <= x < self.width-inset and inset <= y < self.height-inset


@lru_cache(maxsize=4)
def resolve_font(preferred: str | None = None) -> str:
    candidates = ([preferred] if preferred else []) + [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if p and Path(p).is_file():
            return str(p)
    # Explicit fallback discovery; do not silently rely on PIL bitmap font for CJK.
    try:
        result = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans CJK SC"],
                                capture_output=True, text=True, timeout=5, check=True)
        p = result.stdout.strip()
        if Path(p).is_file():
            return p
    except (OSError, subprocess.SubprocessError):
        pass
    raise FileNotFoundError("Install a CJK-capable font or pass --font-path")


@lru_cache(maxsize=128)
def font_at(path: str, size: int) -> ImageFont.FreeTypeFont:
    if size <= 0: raise ValueError("font size must be positive")
    return ImageFont.truetype(path, size)


def text_box(draw: ImageDraw.ImageDraw, xy: Point, text: str, font: ImageFont.FreeTypeFont,
             anchor: str = "mm", pad: float = 0) -> tuple[float,float,float,float]:
    """Pillow textbbox computed for actual anchor, including glyph bearings."""
    b = draw.textbbox(xy, text, font=font, anchor=anchor)
    return (b[0]-pad, b[1]-pad, b[2]+pad, b[3]+pad)


def boxes_overlap(a: tuple[float,float,float,float], b: tuple[float,float,float,float],
                  tolerance: float = 0) -> bool:
    return min(a[2],b[2])-max(a[0],b[0])>tolerance and min(a[3],b[3])-max(a[1],b[1])>tolerance


@dataclass
class Painter:
    """Lightweight raster drawing facade. all primitives use cartesian coords."""
    image: Image.Image
    viewport: Viewport
    font_path: str | None = None
    recorded_labels: dict[str,tuple[float,float,float,float]] = field(default_factory=dict)

    def __post_init__(self):
        if self.image.mode != "RGBA":
            raise ValueError("Painter requires RGBA image; compose before RGB")
        if self.image.size != (self.viewport.width,self.viewport.height):
            raise ValueError("viewport/image size mismatch")
        self.draw = ImageDraw.Draw(self.image)
        if self.font_path is None:
            self.font_path=resolve_font()

    def px(self, p: Point) -> tuple[int,int]:
        return tuple(round(v) for v in self.viewport.xy(p))

    def line(self,a: Point,b: Point,fill: Color="#A5C9ED",width: int=3):
        _finite(*a,*b)
        if width<1:raise ValueError("width must be >= 1")
        self.draw.line([self.px(a),self.px(b)],fill=fill,width=width)

    def polyline(self,points: Sequence[Point],fill: Color="#A5C9ED",width: int=3,close: bool=False):
        if len(points)<2:raise ValueError("at least 2 points required")
        px=[self.px(p) for p in points]
        self.draw.line(px + ([px[0]] if close else []), fill=fill,width=width,joint="curve")

    def polygon(self,points: Sequence[Point],fill: Color="#31506A",outline: Color|None="#86C6EC",width: int=2):
        if len(points)<3:raise ValueError("at least 3 points required")
        px=[self.px(p) for p in points]
        self.draw.polygon(px,fill=fill)
        if outline:self.draw.line(px+[px[0]],fill=outline,width=width,joint="curve")

    def point(self,p: Point,radius: int=6,fill: Color="#FFD166",outline: Color|None=None,width: int=2):
        if radius<=0:raise ValueError("radius must be positive")
        x,y=self.px(p)
        self.draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill,outline=outline,width=width)

    def circle(self,center: Point,radius: float,fill: Color|None=None,
               outline: Color="#66D9E8",width: int=3):
        if radius<=0:raise ValueError("radius must be positive")
        cx,cy=self.px(center)
        rx=abs(self.viewport.xy((center[0]+radius,center[1]))[0]-cx)
        ry=abs(self.viewport.xy((center[0],center[1]+radius))[1]-cy)
        self.draw.ellipse((round(cx-rx),round(cy-ry),round(cx+rx),round(cy+ry)),
                          fill=fill,outline=outline,width=width)

    def arrow(self,start: Point,end: Point,color: Color="#B0E4FF",width: int=3,head_px: int=13,angle_deg:float=25):
        x0,y0=self.px(start);x1,y1=self.px(end)
        dx=x1-x0;dy=y1-y0
        length=math.hypot(dx,dy)
        if length < 1e-8: raise ValueError("zero-length arrow")
        if head_px<=0 or head_px>length: raise ValueError("arrowhead longer than arrow")
        self.draw.line((x0,y0,x1,y1),fill=color,width=width)
        direction=math.atan2(dy,dx)
        angle=math.radians(angle_deg)
        for theta in [direction+math.pi-angle,direction+math.pi+angle]:
            tip=(round(x1+head_px*math.cos(theta)),round(y1+head_px*math.sin(theta)))
            self.draw.line((x1,y1,*tip),fill=color,width=width)

    def angle_arc(self,vertex: Point,ray1: Point,ray2: Point,radius_px:int=27,
                  color:Color="#FFD166",width:int=3,reflex:bool=False):
        """Draw mathematically CCW from ray1 toward ray2 unless reflex=True.

        PIL angles are image-clockwise; sample in Cartesian for predictable direction.
        """
        vx,vy=vertex
        u=(ray1[0]-vx,ray1[1]-vy);v=(ray2[0]-vx,ray2[1]-vy)
        if math.hypot(*u)==0 or math.hypot(*v)==0:raise ValueError("degenerate angle")
        a=math.atan2(u[1],u[0]); b=math.atan2(v[1],v[0]); delta=(b-a)%(2*math.pi)
        if not reflex and delta>math.pi:delta-=2*math.pi
        if reflex and abs(delta)<=math.pi:delta=delta-2*math.pi if delta>0 else delta+2*math.pi
        # circle in pixel space so the mark remains circular even with uneven units.
        cx,cy=self.px(vertex)
        pts=[]
        for i in range(max(12,int(abs(delta)*32))+1):
            theta=a+delta*i/max(12,int(abs(delta)*32))
            pts.append((round(cx+radius_px*math.cos(theta)),round(cy-radius_px*math.sin(theta))))
        self.draw.line(pts,fill=color,width=width,joint="curve")

    def right_angle(self,vertex:Point,edge1:Point,edge2:Point,size_px:int=19,
                    color:Color="#F8D878",width:int=3,tol:float=1e-6):
        u=(edge1[0]-vertex[0],edge1[1]-vertex[1]);v=(edge2[0]-vertex[0],edge2[1]-vertex[1])
        lu=math.hypot(*u);lv=math.hypot(*v)
        if min(lu,lv)<1e-12:raise ValueError("degenerate right angle")
        cos=(u[0]*v[0]+u[1]*v[1])/(lu*lv)
        if abs(cos)>tol:raise ValueError(f"angle not 90 degrees: cos={cos}")
        x,y=self.px(vertex)
        # actual geometry direction, mapped to pixel, normalized to px.
        p1=self.px(edge1);p2=self.px(edge2)
        def unit(px):
            d=(px[0]-x,px[1]-y); length=math.hypot(*d)
            return (d[0]/length,d[1]/length)
        a=unit(p1);b=unit(p2)
        q1=(round(x+size_px*a[0]),round(y+size_px*a[1]))
        q2=(round(q1[0]+size_px*b[0]),round(q1[1]+size_px*b[1]))
        q3=(round(x+size_px*b[0]),round(y+size_px*b[1]))
        self.draw.line((q1,q2,q3),fill=color,width=width)

    def segment_ticks(self,a:Point,b:Point,count:int=1,size_px:int=9,color:Color="#F8D878",width:int=2):
        if count<1 or count>5:raise ValueError("expected 1–5 congruence ticks")
        x0,y0=self.px(a);x1,y1=self.px(b)
        dx=x1-x0;dy=y1-y0;L=math.hypot(dx,dy)
        if L<1: raise ValueError("degenerate segment")
        perp=(-dy/L,dx/L)
        for k in range(count):
            t=0.5+(k-(count-1)/2)*min(0.14,12/L)
            x=x0+dx*t;y=y0+dy*t
            u=(round(x-perp[0]*size_px),round(y-perp[1]*size_px))
            v=(round(x+perp[0]*size_px),round(y+perp[1]*size_px))
            self.draw.line((u,v),fill=color,width=width)

    def label(self,text:str,at:Point,*,name:str|None=None,size:int=26,color:Color="#EAF3FF",
              anchor:str="mm",stroke:int=1,offset_px:Point=(0,0),
              forbid_overlap:bool=False)->tuple[float,float,float,float]:
        x,y=self.px(at);x+=offset_px[0];y+=offset_px[1]
        font=font_at(self.font_path,size)
        b=text_box(self.draw,(x,y),text,font,anchor,pad=stroke)
        if b[0]<0 or b[1]<0 or b[2]>self.viewport.width or b[3]>self.viewport.height:
            raise ValueError(f"label clipped: {name or text}")
        if forbid_overlap:
            for key, prior in self.recorded_labels.items():
                if boxes_overlap(b,prior):
                    raise ValueError(f"label collision: {name or text} overlaps {key}")
        self.draw.text((x,y),text,font=font,fill=color,anchor=anchor,
                       stroke_width=stroke,stroke_fill="#061221")
        if name:
            if name in self.recorded_labels:raise ValueError(f"duplicate label ID: {name}")
            self.recorded_labels[name]=b
        return b

    def segment_label(self,text:str,a:Point,b:Point,offset_px:float=18,**kwargs):
        x0,y0=self.px(a);x1,y1=self.px(b)
        dx=x1-x0;dy=y1-y0;L=math.hypot(dx,dy)
        if L<1:raise ValueError("degenerate side cannot be labeled")
        perp=(-dy/L,dx/L)
        center=((a[0]+b[0])/2,(a[1]+b[1])/2)
        return self.label(text,center,offset_px=(perp[0]*offset_px,perp[1]*offset_px),**kwargs)

    def axes(self,x_step:float=1,y_step:float=1,grid:Color="#223A55",axis:Color="#93B5D5"):
        v=self.viewport
        if x_step<=0 or y_step<=0:raise ValueError("non-positive tick size")
        def multiples(start,stop,step):
            i=math.ceil(start/step)
            while i*step <= stop+1e-10:
                yield i*step;i+=1
        for x in multiples(*v.xlim,x_step):
            self.line((x,v.ylim[0]),(x,v.ylim[1]),fill=grid,width=1)
        for y in multiples(*v.ylim,y_step):
            self.line((v.xlim[0],y),(v.xlim[1],y),fill=grid,width=1)
        if v.xlim[0]<=0<=v.xlim[1]:self.line((0,v.ylim[0]),(0,v.ylim[1]),fill=axis,width=2)
        if v.ylim[0]<=0<=v.ylim[1]:self.line((v.xlim[0],0),(v.xlim[1],0),fill=axis,width=2)

    def function_curve(self,f:Callable[[float],float],start:float,stop:float,
                       samples:int=600,color:Color="#65D6FC",width:int=3,
                       max_pixel_jump:float=90):
        """Break across infinities/discontinuities or suspicious jumps.

        This heuristic is NOT proof that a discontinuity is identified; verify
        analytic domain/asymptotes in the mathematical model separately.
        """
        if not start < stop or samples < 2:raise ValueError("invalid plot interval")
        previous=None;sections=[];current=[]
        for i in range(samples+1):
            x=start+(stop-start)*i/samples
            try:
                y=float(f(x))
                if not math.isfinite(y):raise ValueError("not finite")
                if not (self.viewport.ylim[0]<=y<=self.viewport.ylim[1]):raise ValueError("off viewport")
                pt=self.px((x,y))
                if previous is not None and math.dist(previous,pt)>max_pixel_jump:
                    if len(current)>=2:sections.append(current)
                    current=[]
                current.append(pt);previous=pt
            except (ValueError,ZeroDivisionError,OverflowError):
                if len(current)>=2:sections.append(current)
                current=[];previous=None
        if len(current)>=2:sections.append(current)
        for sec in sections:self.draw.line(sec,fill=color,width=width,joint="curve")
        return len(sections)

    def polygon_centroid_label(self,text:str,points:Sequence[Point],**kwargs):
        if len(points)<3:raise ValueError("invalid polygon")
        # This is vertex average, reliable for TRIANGLES; not polygon area centroid.
        if len(points)!=3:raise ValueError("use area centroid for non-triangles")
        center=(sum(p[0] for p in points)/3,sum(p[1] for p in points)/3)
        return self.label(text,center,**kwargs)


def compose_rgba(base: Image.Image, overlay: Image.Image, dest=(0,0)) -> Image.Image:
    if base.mode!="RGBA" or overlay.mode!="RGBA":raise ValueError("compose in RGBA, not RGB")
    out=base.copy();out.alpha_composite(overlay,dest=dest);return out


def supersample(render: Callable[[int],Image.Image],scale:int=2) -> Image.Image:
    """Caller must scale coordinates, font size, and stroke widths consistently."""
    if scale not in (1,2,3,4):raise ValueError("expected supersampling 1–4")
    big=render(scale)
    if big.width%scale or big.height%scale:raise ValueError("size not divisible by scale")
    return big.resize((big.width//scale,big.height//scale),Image.Resampling.LANCZOS)


def glow_layer(layer:Image.Image,radius:int=9,strength:float=.35)->Image.Image:
    if layer.mode!="RGBA":raise ValueError("expected RGBA")
    alpha=layer.getchannel("A").filter(ImageFilter.GaussianBlur(radius=radius))
    alpha=alpha.point(lambda x:round(x*max(0,min(1,strength))))
    glow=layer.copy();glow.putalpha(alpha)
    return Image.alpha_composite(glow,layer)


def create_canvas(view:Viewport,background:Color="#081626")->Image.Image:
    return Image.new("RGBA",(view.width,view.height),background)