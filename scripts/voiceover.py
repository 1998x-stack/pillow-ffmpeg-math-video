"""Reusable offline eSpeak -> FFmpeg teaching-video narration.

Example:
  python -m scripts.voiceover --video sample.mp4 --segments narration.json \
      --output sample_narrated.mp4

JSON: [{"start":0,"end":5,"text":"中文讲解"}, ...]

Quality note: eSpeak offline zh voice may have an incomplete Chinese dictionary.
This engine is for technical proofs-of-concept, NOT a certified Mandarin voice.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def call(args):
    proc=subprocess.run(args,capture_output=True,text=True)
    if proc.returncode:raise RuntimeError(f'{args[0]} failed: {proc.stderr[-1000:]}')
    return proc


def probe(path):
    return json.loads(call(['ffprobe','-v','error','-show_entries',
        'stream=codec_type,codec_name,sample_rate:format=duration,size','-of','json',str(path)]).stdout)


def validate_segments(rows,duration):
    if not isinstance(rows,list) or not rows:raise ValueError('nonempty segments list required')
    last=0.
    for i,s in enumerate(rows):
        if not all(k in s for k in ('start','end','text')):raise ValueError(f'fields missing at segment {i}')
        start,end=float(s['start']),float(s['end'])
        if not 0<=start<end<=duration+0.03:raise ValueError(f'bad timing {i}')
        if start<last-1e-6:raise ValueError(f'overlapping narration segments {i}')
        if not isinstance(s['text'],str) or not s['text'].strip():raise ValueError(f'empty narration {i}')
        last=end
    return True


def timestamp(t):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def create_offline(video,segments,output,*,voice='zh',speed=170,overwrite=False):
    video,output=Path(video).resolve(),Path(output).resolve()
    for exe in ('espeak','ffmpeg','ffprobe'):
        if not shutil.which(exe):raise RuntimeError(f'{exe} executable unavailable')
    if not video.is_file():raise FileNotFoundError(video)
    if output.exists() and not overwrite:raise FileExistsError(output)
    if output==video:raise ValueError('Never overwrite source video')
    media_before=probe(video)
    if any(s.get('codec_type')=='audio' for s in media_before.get('streams', [])):
        raise ValueError('Input already contains audio. Preserve the original track; mix separately after explicit review.')
    duration=float(media_before['format']['duration'])
    rows=json.loads(Path(segments).read_text(encoding='utf-8'))
    validate_segments(rows,duration)
    output.parent.mkdir(exist_ok=True,parents=True)
    evidence=[]
    with tempfile.TemporaryDirectory(prefix='math-tts-') as tmp:
        temp=Path(tmp);files=[];filters=[]
        for i,row in enumerate(rows):
            w=temp/f'{i:02d}.wav'
            r=call(['espeak','-v',voice,'-s',str(speed),'-a','175','-w',str(w),row['text']]);files.append(w)
            raw_duration=float(probe(w)['format']['duration'])
            target=float(row['end'])-float(row['start'])-.7
            if target<=.4:raise ValueError(f'Segment {i} too short')
            tempo=max(1.,raw_duration/target)
            if tempo>1.8:raise ValueError(f'Segment {i} needs {tempo:.2f}x speed: rewrite a shorter text')
            delay=round((float(row['start'])+.25)*1000)
            filters.append(f'[{i}:a]atempo={tempo:.6f},aresample=48000,adelay={delay},volume=0.75[a{i}]')
            evidence.append({**row,'raw_seconds':raw_duration,'tempo':round(tempo,3),
                'estimated_ending':round(row['start']+.25+raw_duration/tempo,3),
                'fits':row['start']+.25+raw_duration/tempo<=row['end']+.015,
                'tts_warning':r.stderr.strip()})
        out_audio=temp/'narration.m4a';target_inputs=''.join(f'[a{i}]' for i in range(len(rows)))
        filters.append(f'{target_inputs}amix=inputs={len(rows)}:duration=longest:normalize=0,atrim=duration={duration:.3f},apad[aout]')
        inputs=[p for path in files for p in ('-i',str(path))]
        call(['ffmpeg','-y','-loglevel','error',*inputs,'-filter_complex',';'.join(filters),'-map','[aout]',
              '-ar','48000','-ac','1','-t',f'{duration:.3f}','-c:a','aac','-b:a','128k',str(out_audio)])
        call(['ffmpeg','-y','-loglevel','error','-i',str(video),'-i',str(out_audio),'-map','0:v:0','-map','1:a:0',
              '-c:v','copy','-c:a','copy','-t',f'{duration:.3f}','-movflags','+faststart',str(output)])
    details=probe(output)
    stream_types={s['codec_type'] for s in details.get('streams',[])}
    passed=stream_types=={'video','audio'} and abs(float(details['format']['duration'])-duration)<.1 and all(s['fits'] for s in evidence)
    srt='\n'.join(f"{i}\n{timestamp(float(s['start']))} --> {timestamp(float(s['end']))}\n{s['text']}\n" for i,s in enumerate(rows,1))
    output.with_suffix('.srt').write_text(srt,encoding='utf-8')
    output.with_suffix('.verification.json').write_text(json.dumps({
        'technical_pass':passed,'pronunciation_review':'not_run','quality':'offline espeak demo only',
        'media':details,'segments':evidence},ensure_ascii=False,indent=2),encoding='utf-8')
    if not passed:raise RuntimeError('Audio/video media verification failed')
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',required=True);p.add_argument('--segments',required=True);p.add_argument('--output',required=True)
    p.add_argument('--voice',default='zh');p.add_argument('--speed',type=int,default=170);p.add_argument('--overwrite',action='store_true')
    a=p.parse_args();print(create_offline(a.video,a.segments,a.output,voice=a.voice,speed=a.speed,overwrite=a.overwrite))

if __name__=='__main__':main()