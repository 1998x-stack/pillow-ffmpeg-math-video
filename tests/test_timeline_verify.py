import pytest
from PIL import Image
from scripts.timeline import NumericTrack,Keyframe,LayerCache,frame_times
from scripts.verify import verify_polygon_partition,verify_rigid_translation,verify_label_boxes,VerificationFailure,randomized_pythagoras
from scripts.formulas import FormulaToken,matching_token_states
from scripts.visual_review import pick_timestamps


def test_track_and_non_monotonic():
    tr=NumericTrack((Keyframe(0,0),Keyframe(2,10)))
    assert tr.value_at(-1)==0 and tr.value_at(1)==5 and tr.value_at(5)==10
    with pytest.raises(ValueError):NumericTrack((Keyframe(1,1),Keyframe(0,2)))


def test_layer_dirty_vs_full():
    base=Image.new('RGBA',(80,50),'#102233')
    overlay=Image.new('RGBA',base.size,(0,0,0,0))
    overlay.paste((255,0,0,200),(0,0,20,20))
    c=LayerCache(base)
    c.composite(overlay,key='a')
    overlay2=Image.new('RGBA',base.size,(0,0,0,0))
    overlay2.paste((0,255,0,200),(0,0,20,20))
    cropped=c.composite(overlay2,key='b',dirty_bbox=(0,0,20,20))
    full=base.copy();full.alpha_composite(overlay2)
    assert cropped.tobytes()==full.tobytes()
    c.composite(overlay2,key='b');assert c.cache_hits==1


def test_geometry_negative_overlap_gap():
    outer=[(0,0),(2,0),(2,2),(0,2)]
    tiles=[[(0,0),(2,0),(2,1),(0,1)],[(0,1),(2,1),(2,2),(0,2)]]
    assert verify_polygon_partition(outer,tiles,[])['total_area']==4
    with pytest.raises(VerificationFailure,match='gap'):
        verify_polygon_partition(outer,tiles[:1],[])
    with pytest.raises(VerificationFailure,match='overlap'):
        verify_polygon_partition(outer,tiles+[tiles[0]],[])


def test_translation_only_and_labels():
    p=[(0,0),(3,0),(0,4)]
    assert verify_rigid_translation(p,[(x+2,y-1) for x,y in p])
    with pytest.raises(VerificationFailure,match='stretched'):
        verify_rigid_translation(p,[(0,0),(4,0),(0,4)])
    assert verify_label_boxes({'A':(1,1,20,20)},(100,80))['labels_checked']==1
    with pytest.raises(VerificationFailure):verify_label_boxes({'A':(90,1,120,20)},(100,80))


def test_semantic_formula_ids():
    a=[FormulaToken('x','x',(0,0)),FormulaToken('plus','+',(.2,0))]
    b=[FormulaToken('x','x',(2,0)),FormulaToken('eq','=',(3,0))]
    middle=matching_token_states(a,b,.5)
    x=next(t for t in middle if t[0]=='x')
    assert x[2]==pytest.approx((1,0))
    assert {t[0] for t in middle}=={'x','plus','eq'}
    with pytest.raises(ValueError,match='duplicate'):
        matching_token_states([a[0],a[0]],b,.3)
    with pytest.raises(ValueError,match='meaning'):
        matching_token_states([a[0]],[FormulaToken('x','y',(1,0))],.3)


def test_frame_sampling_time_bounds():
    assert len(list(frame_times(15,6)))==90
    with pytest.raises(ValueError):list(frame_times(30,.12))
    ts=pick_timestamps(10,7,20261120)
    assert ts==pick_timestamps(10,7,20261120)
    assert all(0<t<10 for t in ts)


def test_randomized_proofs():
    assert randomized_pythagoras(n=15)['cases']==20


def test_actual_mathtext_rgba():
    from scripts.formulas import math_sprite,paste_math
    img=math_sprite(r'\frac{a}{b}',fontsize=20,dpi=120)
    assert img.mode=='RGBA' and img.width>3 and img.height>3
    canvas=Image.new('RGBA',(500,300),(10,10,10,255))
    paste_math(canvas,img,(40,20),opacity=180)
    assert canvas.getbbox() is not None


def test_area_label_entire_bbox_not_just_center():
    from scripts.verify import verify_area_label_bbox
    from scripts.pillow_draw import Viewport
    v=Viewport(100,100,xlim=(0,10),ylim=(0,10))
    region=[(2,2),(8,2),(8,8),(2,8)]
    assert verify_area_label_bbox((35,35,65,65),v,region)['status']=='pass'
    with pytest.raises(VerificationFailure,match='glyph box exits'):
        verify_area_label_bbox((15,35,65,65),v,region)


def test_release_gate_never_implies_human_approval():
    from scripts.release_gate import evaluate,REQUIRED
    partial={k:{'status':'pass'} for k in REQUIRED if k!='human_review'}
    out=evaluate(partial)
    assert not out['publishable']
    assert out['gates']['human_review']['status']=='not_run'
    assert evaluate({k:{'status':'pass'} for k in REQUIRED})['publishable']


def test_skill_links_and_structure():
    from scripts.check_skill import run_checks
    assert run_checks()['status']=='pass'