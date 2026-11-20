from __future__ import annotations
import math
from pathlib import Path
import pytest
from scripts.speech_normalizer import normalize_math, MathSpeechError, require_reviewed_narration
from scripts.speech_timeline import NarrationSegment, validate_timeline, subtitle_srt
from scripts.audio_verifier import fit_speech, AudioVerificationError, inspect_pcm16_wav, release_audio_gates
from scripts.tts import ReviewedWavBackend, EspeakBackend

@pytest.mark.parametrize('src,exp',[
    ('x^2','x的平方'),
    ('a^2+b^2=c^2','a的平方加b的平方等于c的平方'),
    (r'\frac{x^2}{16}+\frac{y^2}{9}=1','（x的平方）除以（十六）加（y的平方）除以（九）等于一'),
    (r'c=\sqrt{7}','c等于根号下（七）'),
    ('F_1','F下标一'),
    ('y=-3','y等于负三'),
    ('x^3=27','x的立方等于二十七'),
])
def test_math_reading(src,exp):assert normalize_math(src)==exp

@pytest.mark.parametrize('bad',[r'\unknown{7}',r'\frac{1}',r'\sqrt', '{x', '',r'\begin{matrix}1\end{matrix}', '4∑2'])
def test_fail_closed_unhandled_math(bad):
    with pytest.raises(MathSpeechError):normalize_math(bad)

def test_spoken_review_contract():
    assert require_reviewed_narration({'claim_id':'ell-1','spoken_text':'到焦点距离之和保持不变'})
    for row in ({'claim_id':'ell-1','spoken_text':r'\frac{1}{2}'},{'spoken_text':'完整句子'},{}):
        with pytest.raises(MathSpeechError):require_reviewed_narration(row)

def test_timeline_valid_and_srt():
    rows=[NarrationSegment('1',0,2,'第一步','p1'),NarrationSegment('2',2,4,'第二步','p2','字幕二')]
    assert validate_timeline(rows,4)==rows
    assert '00:00:02,000 --> 00:00:04,000' in subtitle_srt(rows)

@pytest.mark.parametrize('items',[
    [NarrationSegment('a',0,2,'一句','x'),NarrationSegment('b',1.9,3,'二句','x')],
    [NarrationSegment('a',0,1,'一句','x'),NarrationSegment('a',1,2,'二句','x')],
    [NarrationSegment('a',math.nan,1,'一句','x')],
    [NarrationSegment('a',0,1,'一句','')],
])
def test_timeline_reject(items):
    with pytest.raises(ValueError):validate_timeline(items,3)

def test_tempo_reject_cuts():
    with pytest.raises(AudioVerificationError):fit_speech(9,4)
    ok=fit_speech(2,4)
    assert ok['tempo']==1 and ok['fits']

def test_audio_gates_do_not_autopass():
    g=release_audio_gates(technical_pass=True)
    assert g['audio_technical']['status']=='pass'
    assert g['audio_pronunciation']['status']=='not_run'

def test_pcm16_analysis(tmp_path):
    import wave,struct
    sample_rate=8000
    p=tmp_path/'sound.wav'
    with wave.open(str(p),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sample_rate)
        w.writeframes(b''.join(struct.pack('<h', int(10000*math.sin(2*math.pi*440*i/sample_rate)))
                               for i in range(sample_rate)))
    data=inspect_pcm16_wav(p)
    assert data['technical_pass'] and data['duration_s']==1.0
    with wave.open(str(tmp_path/'silent.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sample_rate)
        w.writeframes(b'\0\0'*sample_rate)
    assert not inspect_pcm16_wav(tmp_path/'silent.wav')['technical_pass']

def test_external_backend_review_status(tmp_path):
    original=tmp_path/'a.wav';original.write_bytes(b'RIFF'+b'0'*100)
    provider=ReviewedWavBackend({'a':str(original)},frozenset({'a'}),'licensed',license_note='owned')
    r=provider.synthesize('hello',tmp_path/'out.wav',segment_id='a')
    assert r.pronunciation_approved
    assert r.wav_path.read_bytes()==original.read_bytes()
    with pytest.raises(KeyError):provider.synthesize('bad',tmp_path/'other.wav',segment_id='missing')

def test_espeak_bad_controls():
    with pytest.raises(ValueError):EspeakBackend(executable='espeak',speed=1)

def test_audio_required_release_gate():
    from scripts.release_gate import evaluate,REQUIRED,AUDIO_REQUIRED
    orig={k:{'status':'pass'} for k in REQUIRED}
    assert evaluate(orig)['publishable']
    assert not evaluate(orig,audio_requested=True)['publishable']
    assert evaluate({**orig,**{k:{'status':'pass'} for k in AUDIO_REQUIRED}},audio_requested=True)['publishable']

def test_glossary_schema():
    import json
    f=Path(__file__).resolve().parents[1]/'assets/math_pronunciation_zh.json'
    data=json.loads(f.read_text(encoding='utf8'))
    assert len(data['terms'])>=8
    assert len({x['written'] for x in data['terms']})==len(data['terms'])
    assert all(x['review_required'] and x['spoken'] for x in data['terms'])


def test_end_to_end_audio_over_silent_video(tmp_path):
    import shutil
    if not (shutil.which('ffmpeg') and shutil.which('ffprobe') and (shutil.which('espeak') or shutil.which('espeak-ng'))):
        pytest.skip('offline audio prerequisites unavailable')
    from scripts.demo import render
    from scripts.speech_pipeline import produce_narrated_video
    from scripts.tts import EspeakBackend
    root=Path(__file__).resolve().parents[1]
    src=tmp_path/'silent.mp4'
    render(src,12)
    final=tmp_path/'with_audio.mp4'
    result=produce_narrated_video(src,root/'assets/narration.example.json',final,backend=EspeakBackend())
    assert result['status']=='technical_pass_review_pending'
    assert not result['publishable']
    assert final.exists() and final.with_suffix('.srt').exists()
    assert final.with_suffix('.verification.json').exists()
    assert abs(float(result['media']['format']['duration'])-6.0)<.15
    with pytest.raises(ValueError,match='silent video'):
        produce_narrated_video(final,root/'assets/narration.example.json',tmp_path/'invalid.mp4',backend=EspeakBackend())