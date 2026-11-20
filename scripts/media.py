"""Safe in-memory RGB->H.264 encoding and ffprobe assertions.

No shell=True, no overwrite by default, no music replacement by default.
"""
from __future__ import annotations
from pathlib import Path
from subprocess import Popen,run,PIPE
import json
import shutil
from PIL import Image


class VideoEncodingError(RuntimeError):pass


def encode_rgb_frames(frames,output:str|Path,width:int,height:int,fps:int,crf:int=20,preset:str='medium',overwrite:bool=False):
    if not shutil.which('ffmpeg'):raise VideoEncodingError('ffmpeg not found')
    path=Path(output).resolve()
    if path.exists() and not overwrite:raise FileExistsError(path)
    if path.suffix.lower()!='.mp4':raise ValueError('expected .mp4 extension')
    if width<=0 or height<=0 or fps<=0 or not 0<=crf<=51:raise ValueError('bad media parameters')
    path.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','error', '-y' if overwrite else '-n',
         '-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}',
         '-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-crf',str(crf),
         '-preset',preset,'-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=Popen(cmd,stdin=PIPE,stderr=PIPE)
    count=0
    try:
        for frame in frames:
            if frame.size!=(width,height):raise VideoEncodingError(f'frame {count} dimension mismatch')
            if frame.mode!='RGB':raise VideoEncodingError(f'frame {count} not RGB')
            proc.stdin.write(frame.tobytes())
            count+=1
        if count==0:raise VideoEncodingError('empty frame iterator')
        proc.stdin.close()
        err=proc.stderr.read().decode('utf-8',errors='replace')
        rc=proc.wait()
        if rc:raise VideoEncodingError(f'ffmpeg exited {rc}: {err[-3000:]}')
        return {'frames':count,'output':str(path),'probe':probe_video(path)}
    except Exception:
        try:proc.stdin.close()
        except Exception:pass
        proc.kill();proc.wait()
        if path.exists():path.unlink()
        raise


def probe_video(path:str|Path):
    if not shutil.which('ffprobe'):raise VideoEncodingError('ffprobe not found')
    cmd=['ffprobe','-v','error','-show_entries',
         'stream=index,codec_type,codec_name,width,height,avg_frame_rate,nb_frames',
         '-show_entries','format=duration,size','-of','json',str(path)]
    result=run(cmd,capture_output=True,text=True,check=True,timeout=25)
    return json.loads(result.stdout)


def verify_media(path:str|Path,width:int,height:int,fps:int,duration:float,tolerance:float=.15,
                 expected_audio:bool=False):
    data=probe_video(path)
    video=[s for s in data['streams'] if s.get('codec_type')=='video']
    audio=[s for s in data['streams'] if s.get('codec_type')=='audio']
    if len(video)!=1:raise VideoEncodingError('expected exactly one video stream')
    v=video[0]
    if (v['width'],v['height'])!=(width,height):raise VideoEncodingError('resolution mismatch')
    num,den=map(int,v['avg_frame_rate'].split('/'))
    if abs(num/den-fps)>1e-6:raise VideoEncodingError('fps mismatch')
    if abs(float(data['format']['duration'])-duration)>tolerance:raise VideoEncodingError('duration mismatch')
    if bool(audio)!=expected_audio:raise VideoEncodingError('audio stream mismatch')
    return data