import math
import pytest
from PIL import Image
from scripts.pillow_draw import (Viewport,Painter,create_canvas,resolve_font,boxes_overlap,smoothstep,supersample,compose_rgba)
from scripts.geometry import centroid,polygon_signed_area,transform_point
from scripts.verify import verify_reserved_regions,verify_right_angle,verify_pythagoras,VerificationFailure


def p():
    v=Viewport(640,360,xlim=(-8,8),ylim=(-4.5,4.5))
    return Painter(create_canvas(v),v)


def test_cartesian_roundtrip_and_y_inversion():
    v=Viewport(640,360,xlim=(-8,8),ylim=(-4.5,4.5))
    assert v.xy((0,2))[1]<v.xy((0,0))[1]
    for pt in [(0,0),(-7,-3),(6,2)]:
        assert v.cartesian(v.xy(pt))==pytest.approx(pt)


def test_unmatched_viewport_is_rejected():
    with pytest.raises(ValueError):Painter(Image.new('RGBA',(2,2)),Viewport(640,360))


def test_primitives_and_labels():
    d=p();d.axes(2,2)
    d.polygon([(-3,-2),(0,-2),(-3,2)])
    d.arrow((0,0),(3,0));d.right_angle((-3,-2),(0,-2),(-3,2))
    d.segment_ticks((-3,-2),(0,-2),2)
    d.angle_arc((0,0),(1,0),(0,1))
    d.point((0,0));d.circle((2,1),.5)
    d.polyline([(0,2),(1,3),(2,2)])
    d.segment_label('a',(-3,-2),(0,-2),name='a')
    assert len(d.recorded_labels)==1


def test_right_angle_marker_fail_closed():
    d=p()
    with pytest.raises(ValueError,match='not 90'): d.right_angle((0,0),(2,0),(1,1))
    with pytest.raises(ValueError,match='zero-length'): d.arrow((0,0),(0,0))
    with pytest.raises(ValueError,match='degenerate'): d.segment_ticks((0,0),(0,0))


def test_label_bbox_and_collision():
    d=p()
    d.label('A',(0,0),name='A',forbid_overlap=True)
    with pytest.raises(ValueError,match='collision'):
        d.label('B',(0,0),name='B',forbid_overlap=True)
    with pytest.raises(ValueError,match='duplicate'):
        d.label('else',(5,0),name='A')
    with pytest.raises(ValueError,match='clipped'):
        d.label('outside',(10,0),name='x')


def test_reserved_title_detection():
    d=p();d.label('C',(0,3.5),name='vertex_c')
    with pytest.raises(VerificationFailure,match='reserved'):
        verify_reserved_regions(d.recorded_labels,{'top_title':(0,0,640,65)})
    assert verify_reserved_regions(d.recorded_labels,{'footer':(0,330,640,360)})['labels_checked']==1


def test_function_plot_breaks_at_asymptote():
    d=p();n=d.function_curve(lambda x:1/x,-3,3,samples=600)
    assert n>=2
    with pytest.raises(ValueError):d.function_curve(lambda x:x,2,2)


def test_color_composition_and_smoothstep():
    a=Image.new('RGBA',(10,10),(0,0,0,255))
    b=Image.new('RGBA',(10,10),(255,0,0,128))
    c=compose_rgba(a,b)
    assert c.getpixel((4,4))[0] in (127,128)
    assert a.getpixel((4,4))[0]==0
    assert smoothstep(0)==0 and smoothstep(1)==1


def test_centroid_not_vertex_average_for_arbitrary_polygon():
    pts=[(0,0),(4,0),(4,1),(1,1),(1,4),(0,4)]
    center=centroid(pts)
    assert center[0]<1.5 and center[1]<1.5
    assert abs(polygon_signed_area(pts)-7)<1e-10
    assert centroid([(0,0),(2,0),(0,2)])==pytest.approx((2/3,2/3))
    with pytest.raises(ValueError):centroid([(0,0),(1,0),(2,0)])


def test_geometry_proof_and_transform():
    assert verify_pythagoras(3,4)['c']==5
    assert verify_right_angle((3,0),(0,0),(0,4))
    assert transform_point((1,0),angle=math.pi/2)==pytest.approx((0,1),abs=1e-12)
    with pytest.raises(VerificationFailure):verify_right_angle((2,0),(0,0),(1,1))


def test_extras_cover_math_objects():
    from scripts.math_primitives import (dashed_segment,bezier_curve,parametric_curve,
        dimension_line,tangent_and_normal,labeled_number_line,callout,polygon_highlight)
    d=p()
    assert dashed_segment(d,(-2,0),(2,0))>0
    assert len(bezier_curve(d,(-2,-1),(-1,2),(1,2),(2,-1)))==81
    assert parametric_curve(d,lambda t:(t,math.sin(t)),-3,3)>0
    dimension_line(d,(-2,-2),(2,-2),'4',name='measure')
    tang=tangent_and_normal(d,(0,0),slope=1)
    u=tang['tangent'][1];v=tang['normal'][1]
    assert u[0]*v[0]+u[1]*v[1]==pytest.approx(0,abs=1e-10)
    assert labeled_number_line(d,-3,3,-.3,labels=False)
    assert callout(d,'Peak',(2,2.5),(2,0))
    polygon_highlight(d,[(-2,-1),(2,-1),(0,0)])


def test_extras_refuse_degenerate_cases():
    from scripts.math_primitives import dashed_segment,dimension_line,tangent_and_normal
    d=p()
    with pytest.raises(ValueError):dashed_segment(d,(0,0),(0,0))
    with pytest.raises(ValueError):dimension_line(d,(0,0),(0,0),'0')
    with pytest.raises(ValueError):tangent_and_normal(d,(0,0),float('nan'))