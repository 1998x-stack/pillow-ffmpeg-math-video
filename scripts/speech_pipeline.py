"""Fail-closed offline narration composition onto an existing silent MP4.

Run: python -m scripts.speech_pipeline --video input.mp4 \
  --segments assets/narration.example.json --output narrated.mp4

The output is a technical preview. Human Mandarin pronunciation review remains
mandatory and is never silently marked as passed.
"""
from __future__ import annotations
import argparse
import wave
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .audio_verifier import AudioVerificationError, fit_speech, inspect_pcm16_wav, release_audio_gates
from .speech_normalizer import require_reviewed_narration
from .speech_timeline import NarrationSegment, validate_timeline, subtitle_srt
from .tts import EspeakBackend, ReviewedWavBackend


def _run(args:list[str], *, timeout:int=180)->subprocess.CompletedProcess:
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)


def _probe(src:Path)->dict:
    p=_run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(src)])
    return json.loads(p.stdout)


def _wav_seconds(src:Path)->float:
    import wave
    with wave.open(str(src),'rb') as w:
        return w.getnframes()/w.getframerate()


def _parse_rows(path:Path,duration:float)->list[NarrationSegment]:
    obj=json.loads(path.read_text(encoding='utf8'))
    if not isinstance(obj,list):raise ValueError('JSON requires a list of narration segments')
    rows=[]
    for i,o in enumerate(obj):
        require_reviewed_narration(o)
        rows.append(NarrationSegment(str(o.get('id',f'segment-{i:02d}')),
            float(o['start']),float(o['end']),o['spoken_text'],str(o['claim_id']),
            o.get('subtitle','')))
    return validate_timeline(rows,duration)


def produce_narrated_video(video:Path,segments_json:Path,output:Path,
    *,backend=None,max_tempo:float=1.25,lead_s:float=.15,tail_s:float=.25,
    overwrite:bool=False)->dict:
    """Create a new MP4 using a deterministic narration timeline.

    Does not approve pronunciation. Does not mix over existing audio. Existing
    video output is protected unless overwrite is explicitly requested.
    """
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('ffmpeg and ffprobe are required')
    video,segments_json,output=map(lambda p:Path(p).resolve(),(video,segments_json,output))
    if not video.is_file():raise FileNotFoundError(video)
    if not segments_json.is_file():raise FileNotFoundError(segments_json)
    if output==video:raise ValueError('cannot replace the source video')
    if output.suffix.lower()!='.mp4':raise ValueError('output must have .mp4 suffix')
    if output.exists() and not overwrite:raise FileExistsError(output)
    source=_probe(video)
    videos=[s for s in source['streams'] if s['codec_type']=='video']
    audios=[s for s in source['streams'] if s['codec_type']=='audio']
    if len(videos)!=1 or audios:
        raise ValueError('requires exactly one silent video stream; original audio cannot be replaced implicitly')
    duration=float(source['format']['duration'])
    rows=_parse_rows(segments_json,duration)
    if backend is None:backend=EspeakBackend()
    output.parent.mkdir(parents=True,exist_ok=True)
    evidence=[]
    with tempfile.TemporaryDirectory(prefix='.speech-build-',dir=output.parent) as tmp:
        root=Path(tmp);wavfiles=[]
        for i,r in enumerate(rows):
            result=backend.synthesize(r.spoken_text,root/f'{i:03d}.wav',segment_id=r.segment_id)
            inspection=inspect_pcm16_wav(result.wav_path,max_silence_seconds=max(8.,r.end-r.start))
            if not inspection['technical_pass']:
                raise AudioVerificationError(f'WAV {r.segment_id} failed acoustic verifier: {inspection}')
            length=_wav_seconds(result.wav_path)
            fit=fit_speech(length,r.end-r.start,lead=lead_s,tail=tail_s,max_tempo=max_tempo)
            wavfiles.append(result.wav_path)
            evidence.append({'segment_id':r.segment_id,'claim_id':r.claim_id,
                'backend':result.backend,'voice':result.voice,'wav':inspection,
                'timing':fit,'tts_stderr':result.stderr[-800:],
                'pronunciation_approved':result.pronunciation_approved,
                'provenance':result.provenance})
        # Build a sample-accurate mono PCM timeline. Mixing via FFmpeg's amix
        # with delayed tracks can exhibit timestamp/timebase surprises on some
        # builds. This conservative, non-overlapping placement avoids that bug.
        sample_rate=48000
        total_frames=round(duration*sample_rate)
        pcm=bytearray(total_frames*2)
        for i,r in enumerate(rows):
            tempo=evidence[i]['timing']['tempo']
            mono=root/f'{i:03d}.s16le'
            _run(['ffmpeg','-y','-v','error','-i',str(wavfiles[i]),
                '-af',f'atempo={tempo:.7f},aresample=48000,volume=0.75',
                '-f','s16le','-ac','1','-ar','48000',str(mono)],timeout=180)
            clip=mono.read_bytes()
            insert_at=round((r.start+lead_s)*sample_rate)*2
            limit=round((r.end-tail_s)*sample_rate)*2
            if insert_at+len(clip)>limit+4:
                raise AudioVerificationError(f'PCM {r.segment_id} violates reserved tail')
            pcm[insert_at:insert_at+len(clip)]=clip
        timeline_wav=root/'timeline.wav'
        with wave.open(str(timeline_wav),'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm)
        narration=root/'narration.m4a'
        _run(['ffmpeg','-y','-v','error','-i',str(timeline_wav),
              '-c:a','aac','-b:a','160k',str(narration)],timeout=300)
        encoded=root/'final.mp4'
        _run(['ffmpeg','-y','-v','error','-i',str(video),'-i',str(narration),
              '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','copy',
              '-t',f'{duration:.6f}','-movflags','+faststart',str(encoded)],timeout=300)
        final_probe=_probe(encoded)
        if len([s for s in final_probe['streams'] if s['codec_type']=='audio'])!=1:
            raise AudioVerificationError('encoded MP4 missing audio stream')
        if abs(float(final_probe['format']['duration'])-duration)>.15:
            raise AudioVerificationError(f'encoded MP4 duration mismatch: output={final_probe["format"]["duration"]} source={duration}')
        os.replace(encoded,output)
    # Media operations passed, but review gates remain explicitly pending.
    result={'status':'technical_pass_review_pending','video':str(output),
        'input_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
        'segments':evidence,'media':final_probe,
        'gates':release_audio_gates(technical_pass=True,
            pronunciation_review='not_run',human_av_sync='not_run',license_verified=False),
        'publishable':False,'note':'Human Mandarin, math-claim and A/V sync approval required'}
    output.with_suffix('.srt').write_text(subtitle_srt(rows),encoding='utf8')
    output.with_suffix('.verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--segments',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--provider',choices=('espeak','reviewed-wav'),default='espeak')
    p.add_argument('--clips',type=Path,help='JSON mapping segment IDs to reviewed WAV paths')
    p.add_argument('--reviewed-ids',default='',help='Comma-separated IDs that passed human audio review')
    p.add_argument('--max-tempo',type=float,default=1.25)
    p.add_argument('--overwrite',action='store_true')
    a=p.parse_args()
    if a.provider=='espeak':backend=EspeakBackend()
    else:
        if not a.clips:raise SystemExit('--clips is required for reviewed-wav')
        backend=ReviewedWavBackend(json.loads(a.clips.read_text()),frozenset(x for x in a.reviewed_ids.split(',') if x))
    report=produce_narrated_video(a.video,a.segments,a.output,
                                  backend=backend,max_tempo=a.max_tempo,overwrite=a.overwrite)
    print(json.dumps({'output':report['video'],'status':report['status'],'publishable':False},ensure_ascii=False))

if __name__=='__main__':main()