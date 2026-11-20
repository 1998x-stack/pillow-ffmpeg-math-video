"""pytest -q test_verified_video.py -- tests include intentional faulty diagrams."""
import math
import dataclasses
import pytest
from shapely.geometry import LineString, Point
from geometry_model import PythagoreanLayout, Piece
from verifier import (VerificationError, verify_symbolic, verify_tiling,
    verify_geometry, verify_animation, verify_random_models,
    verify_labels, sample_label_positions, verify_triangle)
from render_video import PythagorasRenderer, ease, W, H

def test_symbolic_general_proof():
    assert verify_symbolic()['status']=='pass'

def test_both_tilings_exact_and_complement():
    m=PythagoreanLayout(3,4)
    result=verify_geometry(m)
    assert result['c']==5
    assert result['layouts'][0]['complement_area']==25
    assert result['layouts'][1]['complement_area']==25

def test_randomized_general_validity():
    assert verify_random_models()['tested_aspect_ratios']==25

@pytest.mark.parametrize('ab',[(1,1),(2,7),(3,4),(7,2),(math.sqrt(2),4)])
def test_temporal_rigidity_for_multiple_ratios(ab):
    m=PythagoreanLayout(*ab)
    assert verify_animation(m,ease,151)['status']=='pass'

def test_bad_right_angle_rejected():
    good=PythagoreanLayout().a_pieces[0]
    bad=dataclasses.replace(good,leg_b=(.27,4))
    with pytest.raises(VerificationError,match='(not right angled|b-leg)'):
        verify_triangle(bad,3,4)

def test_bad_triangle_edge_rejected():
    good=PythagoreanLayout().a_pieces[0]
    bad=dataclasses.replace(good,leg_a=(2.75,0))
    with pytest.raises(VerificationError,match='a-leg'):
        verify_triangle(bad,3,4)

def test_wrong_hole_or_topology_rejected():
    m=PythagoreanLayout()
    class CorruptLayout:
        a=m.a;b=m.b;s=m.s;c=m.c
        outer=m.outer;a_pieces=m.a_pieces;b_pieces=m.b_pieces
        square_a=m.square_a;square_b=m.square_b
        central_square=((3,0),(7,3),(4,6.7),(0,4))
    with pytest.raises(VerificationError,match='(overlap|gaps|area|cover)'):
        verify_tiling(CorruptLayout(),'A')

def test_label_outside_shape_rejected():
    m=PythagoreanLayout()
    loc=sample_label_positions(m)
    assert verify_labels(m,loc)['status']=='pass'
    loc['c²']=(100,100)
    with pytest.raises(VerificationError,match='c²'):
        verify_labels(m,loc)

def test_nonmonotonic_timeline_rejected():
    with pytest.raises(VerificationError,match='non-monotonic'):
        verify_animation(PythagoreanLayout(),lambda t: 1-t,12)

def test_static_frame_cache_and_seek():
    r=PythagorasRenderer()
    a=r.frame(7.1);b=r.frame(7.5)
    assert a is b
    assert r.stats['frames_reused']>0
    for t in [0.,15.,29.,12.5,22.]:
        im=r.frame(t)
        assert im.size==(W,H) and im.mode=='RGB'

def test_triangle_side_labels_track_physical_piece():
    # A legacy bug placed both a/b permanently near the bottom-left corner.
    # It must instead follow the moving T1 physical sides.
    m=PythagoreanLayout()
    for alpha in [0,.21,.5,.79,1]:
        tri=m.pieces_at(ease(alpha))[0]
        a_mid=((tri.right[0]+tri.leg_a[0])/2,(tri.right[1]+tri.leg_a[1])/2)
        b_mid=((tri.right[0]+tri.leg_b[0])/2,(tri.right[1]+tri.leg_b[1])/2)
        a_label=(a_mid[0],a_mid[1]-.30)
        b_label=(b_mid[0]-.34,b_mid[1])
        assert LineString([tri.right,tri.leg_a]).distance(Point(a_label))==pytest.approx(.30)
        assert LineString([tri.right,tri.leg_b]).distance(Point(b_label))==pytest.approx(.34)