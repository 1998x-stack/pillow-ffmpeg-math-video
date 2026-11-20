import shutil
import pytest
from scripts.demo import TRI,VP,DURATION,state_frame,build_base
from scripts.verify import verify_right_angle,verify_reserved_regions
from scripts.media import verify_media,VideoEncodingError
from scripts.pillow_draw import Painter,create_canvas


def test_demo_labels_do_not_cover_reserved_title_any_motion():
    # The demo's geometry and labels are bound to the translated triangle.
    # Check actual C label geometry at the start, midpoint and end.
    for u in (0,.25,.5,.75,1):
        shift=(u*.8,u*.3)
        v=(TRI[2][0]+shift[0],TRI[2][1]+shift[1])
        p=Painter(create_canvas(VP),VP)
        p.label('C',v,size=23,offset_px=(-14,-13),name='C')
        verify_reserved_regions(p.recorded_labels,{'title':(28,20,772,78)})


def test_demo_raster_frames():
    base=build_base()
    assert state_frame(0,base).size==(800,450)
    assert state_frame(2,base).mode=='RGBA'


@pytest.mark.skipif(not shutil.which('ffprobe'),reason='ffprobe unavailable')
def test_generated_demo_mp4(tmp_path):
    from scripts.demo import render
    path=tmp_path/'demo.mp4'
    render(path,15)
    assert verify_media(path,800,450,15,DURATION,expected_audio=False)