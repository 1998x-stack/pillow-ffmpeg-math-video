import pytest
from scripts.voiceover import validate_segments, timestamp

def test_valid_timeline():
    assert validate_segments([{'start':0,'end':2,'text':'起点'},{'start':2,'end':4,'text':'结束'}],4)

@pytest.mark.parametrize('rows',[
    [{'start':0,'end':3,'text':'ok'},{'start':2,'end':4,'text':'oops'}],
    [{'start':2,'end':1,'text':'oops'}],
    [{'start':0,'end':2,'text':''}],
    [{'start':0,'end':2}],
])
def test_reject_bad_segments(rows):
    with pytest.raises(ValueError):validate_segments(rows,5)

def test_timestamp():
    assert timestamp(62.099)=='00:01:02,099'


def test_existing_soundtrack_needs_explicit_mixing(tmp_path):
    from pathlib import Path
    from scripts.voiceover import create_offline
    p=Path(__file__).resolve().parents[1]
    src=p/'assets/demo_geometry_with_offline_audio.mp4'
    seg=p/'assets/demo_narration_segments.json'
    if src.is_file():
        with pytest.raises(ValueError,match='already contains audio'):
            create_offline(src,seg,tmp_path/'should_not_be_created.mp4')