"""Pure geometry helpers shared by label placement, layout and verifiers."""
from __future__ import annotations
from math import atan2, hypot, isfinite, pi


def unit(p,q):
    x=q[0]-p[0];y=q[1]-p[1];n=hypot(x,y)
    if n<=1e-12:raise ValueError('coincident points')
    return x/n,y/n


def polygon_signed_area(points):
    if len(points)<3:raise ValueError('not a polygon')
    return .5*sum(points[i][0]*points[(i+1)%len(points)][1]-
                     points[(i+1)%len(points)][0]*points[i][1]
                     for i in range(len(points)))


def centroid(points):
    """Area centroid for a SIMPLE non-self-intersecting polygon."""
    signed=polygon_signed_area(points)
    if abs(signed)<1e-12:raise ValueError('degenerate polygon')
    cx=sum((points[i][0]+points[(i+1)%len(points)][0])*
           (points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1])
           for i in range(len(points)))/(6*signed)
    cy=sum((points[i][1]+points[(i+1)%len(points)][1])*
           (points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1])
           for i in range(len(points)))/(6*signed)
    return cx,cy


def side_lengths(points):
    if len(points)<2:raise ValueError('not enough vertices')
    return [hypot(points[(i+1)%len(points)][0]-p[0],
                  points[(i+1)%len(points)][1]-p[1]) for i,p in enumerate(points)]


def project_to_segment(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];d2=dx*dx+dy*dy
    if d2<1e-18:raise ValueError('degenerate segment')
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d2))
    return a[0]+t*dx,a[1]+t*dy


def transform_point(p,angle:float=0,scale:float=1,translation=(0,0),center=(0,0)):
    """Uniform scaling+rotation+translation in mathematical XY coordinates."""
    from math import cos,sin
    if not isfinite(angle) or not isfinite(scale) or scale<=0:
        raise ValueError('invalid transform')
    x=(p[0]-center[0])*scale;y=(p[1]-center[1])*scale
    return (center[0]+x*cos(angle)-y*sin(angle)+translation[0],
            center[1]+x*sin(angle)+y*cos(angle)+translation[1])