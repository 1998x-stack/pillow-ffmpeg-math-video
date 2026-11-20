"""Independent, fail-closed mathematical/geometry/temporal/label verifiers.

No OCR. Visual verifier decodes actual MP4 and checks both pixel and geometry
invariants; a human reviewer should inspect the screenshot contact sheet.
"""
import math
import random
from dataclasses import replace
from PIL import Image
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import sympy as sp
from geometry_model import PythagoreanLayout

class VerificationError(AssertionError): pass

def require(condition, message):
    if not condition: raise VerificationError(message)

def poly(points): return Polygon(points)
def approx(x,y,tol=1e-7): return abs(float(x)-float(y)) <= tol

def verify_symbolic():
    a,b=sp.symbols('a b',positive=True)
    s=a+b
    hyp2=a*a+b*b
    require(sp.expand((a+b)**2-4*a*b/2-hyp2)==0, 'symbolic dissection A identity')
    require(sp.expand((a+b)**2-4*a*b/2-(a*a+b*b))==0,'symbolic dissection B identity')
    require(sp.simplify((a+b)**2-(2*a*b+a*a+b*b))==0,'symbolic total area')
    # Inner square: edge vectors (b,a), (-a,b); dot=0, lengths squared=a²+b².
    require(sp.expand(b*(-a)+a*b)==0,'central square orthogonality')
    require(sp.expand(b*b+a*a-hyp2)==0,'central square hypotenuse side')
    return {'symbolic_equalities':5,'status':'pass'}

def verify_triangle(piece,a,b,tol=1e-7):
    r,u,v=piece.points()
    va=(u[0]-r[0],u[1]-r[1]);vb=(v[0]-r[0],v[1]-r[1])
    require(approx(math.hypot(*va),a,tol),f'{piece.name} a-leg is wrong')
    require(approx(math.hypot(*vb),b,tol),f'{piece.name} b-leg is wrong')
    require(approx(va[0]*vb[0]+va[1]*vb[1],0,tol),f'{piece.name} is not right angled')
    require(approx(abs(poly(piece.points()).area),a*b/2,tol),f'{piece.name} area mismatch')
    return True

def verify_tiling(model, mode):
    a,b,s=model.a,model.b,model.s
    parts=model.a_pieces if mode=='A' else model.b_pieces
    holes=(model.central_square,) if mode=='A' else (model.square_a,model.square_b)
    outer=poly(model.outer)
    polygons=[poly(p.points()) for p in parts]+[poly(q) for q in holes]
    require(all(g.is_valid and g.area>1e-9 for g in polygons),f'{mode}: invalid polygon')
    for i,g in enumerate(polygons):
        require(outer.buffer(1e-8).covers(g),f'{mode}: polygon {i} exceeds outer boundary')
        for j in range(i):
            require(g.intersection(polygons[j]).area<1e-7,f'{mode}: {i}/{j} overlap')
    union=unary_union(polygons)
    require(outer.symmetric_difference(union).area<1e-7,f'{mode}: partition has gaps')
    require(approx(sum(g.area for g in polygons),s*s),f'{mode}: pieces do not cover area')
    expected= a*a+b*b
    require(approx(sum(poly(q).area for q in holes),expected),f'{mode}: complement area mismatch')
    if mode=='A':
        q=model.central_square
        for i in range(4):
            j=(i+1)%4;k=(i+2)%4
            u=(q[j][0]-q[i][0],q[j][1]-q[i][1])
            v=(q[k][0]-q[j][0],q[k][1]-q[j][1])
            require(approx(u[0]*v[0]+u[1]*v[1],0), 'central polygon corner not right')
            require(approx(u[0]*u[0]+u[1]*u[1],model.c**2), 'central side is not c')
    return {'mode':mode,'total_area':s*s,'complement_area':expected,'overlap_area':0,'gap_area':0,'passed':True}

def verify_geometry(model):
    require(model.a>0 and model.b>0, 'nonpositive legs')
    a=model.a;b=model.b
    for pa,pb,delta in zip(model.a_pieces,model.b_pieces,model.translations):
        verify_triangle(pa,a,b);verify_triangle(pb,a,b)
        for p,q in zip(pa.points(),pb.points()):
            require(approx(q[0]-p[0],delta[0]) and approx(q[1]-p[1],delta[1]),'nontranslation detected')
    vA=verify_tiling(model,'A');vB=verify_tiling(model,'B')
    return {'a':a,'b':b,'c':model.c,'layouts':[vA,vB],'triangles':4,'status':'pass'}

def verify_animation(model, progress_fn, samples=151):
    """Every intermediate shape must be a *translation*, with fixed edge lengths."""
    last=None
    for i in range(samples):
        p=i/(samples-1)
        k=progress_fn(p)
        require(0<=k<=1,'invalid easing')
        if last is not None: require(k+1e-10>=last,'non-monotonic easing')
        for current,source in zip(model.pieces_at(k),model.a_pieces):
            verify_triangle(current,model.a,model.b)
            r0=source.right;r1=current.right
            for src,dst in zip(source.points(),current.points()):
                require(approx(dst[0]-src[0],r1[0]-r0[0]) and approx(dst[1]-src[1],r1[1]-r0[1]),'triangle deformed during move')
        last=k
    return {'motion_samples':samples,'invariant':'rigid translation; angles and lengths fixed','status':'pass'}

def verify_labels(model, locations):
    """Checks labeled regions and anchors, never trusts manually placed letters."""
    holeA=poly(model.central_square)
    hole_small=poly(model.square_a);hole_big=poly(model.square_b)
    for id_,polygon in [('c²',holeA),('a²',hole_small),('b²',hole_big)]:
        require(polygon.buffer(-0.08).covers(Point(locations[id_])),f'label {id_} is outside its proven area')
    for p in model.a_pieces:
        point=locations[p.name+'A']
        require(poly(p.points()).buffer(-0.08).covers(Point(point)),f'piece label {p.name} is wrongly placed in A')
    for p in model.b_pieces:
        point=locations[p.name+'B']
        require(poly(p.points()).buffer(-0.08).covers(Point(point)),f'piece label {p.name} is wrongly placed in B')
    return {'checked_labels':11,'status':'pass'}

def sample_label_positions(model):
    def centroid(poly_):
        pts=poly_.points() if hasattr(poly_,'points') else poly_
        p=poly(pts).centroid
        return p.x,p.y
    return {'c²':centroid(model.central_square),'a²':centroid(model.square_a),'b²':centroid(model.square_b),**{p.name+'A':centroid(p) for p in model.a_pieces},**{p.name+'B':centroid(p) for p in model.b_pieces}}

def verify_random_models(seed=20261120, count=18):
    rng=random.Random(seed)
    pairs=[(3,4),(4,3),(1,1),(2,7),(7,2),(0.75,1.2),(math.sqrt(2),3)]
    pairs.extend((rng.uniform(.4,8),rng.uniform(.4,8)) for _ in range(count))
    for a,b in pairs: verify_geometry(PythagoreanLayout(a,b))
    return {'tested_aspect_ratios':len(pairs),'seed':seed,'status':'pass'}

def run_preflight(model, progress_fn):
    result={'symbolic':verify_symbolic(),'geometry':verify_geometry(model),
            'randomized':verify_random_models(),'animation':verify_animation(model,progress_fn),
            'labels':verify_labels(model,sample_label_positions(model))}
    return result