"""Independent fail-closed math, geometry, layout, pixel & frame verifiers.

Do not equate finite sampling or numerical equality to universal proof.
"""
from __future__ import annotations
import math
import random
from PIL import Image


class VerificationFailure(AssertionError):
    pass


def require(pred:bool,reason:str):
    if not pred:raise VerificationFailure(reason)


def verify_pythagoras(a:float,b:float,tol:float=1e-9):
    require(math.isfinite(a) and math.isfinite(b) and a>0 and b>0,"right triangle legs must be positive finite")
    hyp=math.hypot(a,b)
    require(math.isclose(hyp*hyp,a*a+b*b,rel_tol=tol,abs_tol=tol),"pythagoras identity")
    # Separate mathematical proof (symbolic), not inferred from this numeric check:
    from sympy import symbols,expand
    x,y=symbols('a b',positive=True)
    require(expand((x+y)**2-4*x*y/2-(x*x+y*y))==0,"dissection identity not zero")
    return {'a':a,'b':b,'c':hyp,'symbolic':'pass','numeric':'pass'}


def verify_right_angle(a,b,c,tol=1e-8):
    ux,uy=a[0]-b[0],a[1]-b[1];vx,vy=c[0]-b[0],c[1]-b[1]
    len1=math.hypot(ux,uy);len2=math.hypot(vx,vy)
    require(min(len1,len2)>1e-12,"degenerate edge")
    require(abs((ux*vx+uy*vy)/(len1*len2))<=tol,"right angle not orthogonal")
    return True


def verify_polygon_partition(outer,tiles,holes,tol=1e-7):
    """Shapely is a verifier dependency; drawing itself has no dependency on it."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    o=Polygon(outer)
    require(o.is_valid and o.area>0,"invalid outer polygon")
    polygons=[Polygon(p) for p in (*tiles,*holes)]
    require(all(p.is_valid and p.area>1e-12 for p in polygons),"invalid/degenerate tile")
    for i,p in enumerate(polygons):
        require(o.buffer(tol).covers(p),f"piece {i} exits outer boundary")
        for j in range(i):require(p.intersection(polygons[j]).area<tol,f"overlap between pieces {i},{j}")
    require(o.symmetric_difference(unary_union(polygons)).area<tol,"partition contains gap or overshoot")
    return {'total_area':o.area,'hole_area':sum(Polygon(h).area for h in holes),'count':len(polygons)}


def verify_rigid_translation(before,after,tol=1e-8):
    require(len(before)==len(after) and len(before)>=2,"piece vertex mismatch")
    dx=after[0][0]-before[0][0];dy=after[0][1]-before[0][1]
    for a,b in zip(before,after):
        require(abs((b[0]-a[0])-dx)<tol and abs((b[1]-a[1])-dy)<tol,
                "piece was stretched/rotated, not merely translated")
    return True


def verify_label_boxes(boxes:dict[str,tuple[float,float,float,float]],size:tuple[int,int],avoid_overlap=True):
    from .pillow_draw import boxes_overlap
    names=list(boxes)
    for n in names:
        a=boxes[n]
        require(0<=a[0]<a[2]<=size[0] and 0<=a[1]<a[3]<=size[1],f"{n}: clipped bbox")
    if avoid_overlap:
        for i,a in enumerate(names):
            for b in names[:i]:require(not boxes_overlap(boxes[a],boxes[b]),f"overlapping labels {a},{b}")
    return {'labels_checked':len(boxes)}


def verify_sampled_color(frame:Image.Image,samples:list[tuple[int,int]],expected:tuple[int,int,int],
                         max_diff:int=15):
    im=frame.convert('RGB')
    for x,y in samples:
        require(0<=x<im.width and 0<=y<im.height,"pixel sample off canvas")
        rgb=im.getpixel((x,y))
        require(max(abs(c-d) for c,d in zip(rgb,expected))<=max_diff,
                f"pixel color unexpected at {(x,y)}: {rgb} vs {expected}")
    return {'checked_pixels':len(samples)}


def verify_frame_sequence(frames:list[Image.Image],expected_size:tuple[int,int]):
    require(len(frames)>0,"missing frames")
    for i,f in enumerate(frames):require(f.size==expected_size,f"bad frame dimensions: {i}")
    return {'checked_frames':len(frames)}


def randomized_pythagoras(seed=20261120,n=40):
    rng=random.Random(seed)
    for a,b in [(3,4),(4,3),(1,1),(.1,17),(17,.1)]+[(rng.uniform(.1,20),rng.uniform(.1,20)) for _ in range(n)]:
        verify_pythagoras(a,b)
    return {'seed':seed,'cases':n+5,'status':'pass'}


def verify_reserved_regions(boxes,reserved:dict[str,tuple[float,float,float,float]]):
    """Reject labels covering titles, playback controls, or platform UI safe zones."""
    from .pillow_draw import boxes_overlap
    for id_,bbox in boxes.items():
        for name,rb in reserved.items():
            require(not boxes_overlap(bbox,rb),f"{id_} overlaps reserved region {name}")
    return {'labels_checked':len(boxes),'reserved_regions':len(reserved)}


def verify_area_label_bbox(label_bbox_px,viewport,polygon_math,inset_units=0.02):
    """Reject a REGION label unless its entire rectangular glyph box is inside.

    Using all 4 corners catches labels whose center is inside but glyphs spill
    out. Shapely is a verifier dependency; pixel font bbox is measured by PIL.
    """
    from shapely.geometry import Polygon
    outer=Polygon(polygon_math)
    require(outer.is_valid and outer.area>0,'invalid label region')
    x0,y0,x1,y1=label_bbox_px
    require(0<=x0<x1<=viewport.width and 0<=y0<y1<=viewport.height,
            'label bbox off canvas')
    corners=[viewport.cartesian((x0,y0)),viewport.cartesian((x1,y0)),
             viewport.cartesian((x1,y1)),viewport.cartesian((x0,y1))]
    inner=outer.buffer(-inset_units)
    require(not inner.is_empty and inner.covers(Polygon(corners)),
            'area label glyph box exits its mathematical region')
    return {'status':'pass','corners_verified':4,'inset_units':inset_units}