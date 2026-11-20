"""Acoustic and timeline gate checks. Never claims pronunciation correctness."""
from __future__ import annotations
from pathlib import Path
import array
import math
import sys
import wave

class AudioVerificationError(RuntimeError):pass


def inspect_pcm16_wav(path:str|Path, *, min_rms:float=0.001,max_silence_seconds:float=8)->dict:
    """Compute full-clip peak, RMS, longest near-silence interval.

    Validates 16-bit PCM; rejects compressed WAV and unsupported widths.
    """
    path=Path(path)
    with wave.open(str(path),'rb') as w:
        sr=w.getframerate();channels=w.getnchannels();frames=w.getnframes();width=w.getsampwidth()
        if w.getcomptype()!='NONE' or width!=2 or channels not in (1,2) or sr<=0:
            raise AudioVerificationError('expected mono/stereo uncompressed 16-bit PCM WAV')
        peak=0;power=0.0;samples=0;silent_run=0;max_silent=0;threshold=0.002*32768
        while True:
            data=w.readframes(8192)
            if not data:break
            values=array.array('h');values.frombytes(data)
            if sys.byteorder!='little':values.byteswap()
            for v in values:
                peak=max(peak,abs(v));power+=v*v;samples+=1
                if abs(v)<=threshold:
                    silent_run+=1;max_silent=max(max_silent,silent_run)
                else:silent_run=0
        if not samples:raise AudioVerificationError('empty WAV')
        peak_norm=peak/32768
        rms=math.sqrt(power/samples)/32768
        duration=frames/sr
        sil=max_silent/(sr*channels)
        return {'duration_s':round(duration,3),'sample_rate':sr,'channels':channels,
                'peak':round(peak_norm,6),'rms':round(rms,6),'max_silence_s':round(sil,3),
                'silent':rms<min_rms,'clipping_risk':peak_norm>=0.999,
                'long_silence':sil>max_silence_seconds,
                'technical_pass':rms>=min_rms and peak_norm<0.999 and sil<=max_silence_seconds}


def fit_speech(raw_seconds:float, segment_seconds:float, *, lead:float=0.15,
               tail:float=0.25,max_tempo:float=1.25)->dict:
    if not all(math.isfinite(x) for x in (raw_seconds,segment_seconds,lead,tail,max_tempo)):
        raise ValueError('nonfinite timing')
    if raw_seconds<=0 or segment_seconds<=lead+tail or max_tempo<1:
        raise ValueError('invalid durations or pacing')
    usable=segment_seconds-lead-tail
    tempo=max(1.0,raw_seconds/usable)
    if tempo>max_tempo+1e-9:
        raise AudioVerificationError(f'needs tempo {tempo:.3f} > cap {max_tempo}; shorten script or extend scene')
    return {'tempo':tempo,'starts_after_s':lead,'speech_ends_by_s':lead+raw_seconds/tempo,
            'fits':lead+raw_seconds/tempo<=segment_seconds-tail+1e-8}


def release_audio_gates(*,technical_pass:bool,pronunciation_review:str='not_run',
                        human_av_sync:str='not_run',license_verified:bool=False)->dict:
    return {'audio_technical':{'status':'pass' if technical_pass else 'fail'},
            'audio_pronunciation':{'status':'pass' if pronunciation_review=='pass' else pronunciation_review},
            'audio_av_sync':{'status':'pass' if human_av_sync=='pass' else human_av_sync},
            'audio_license':{'status':'pass' if license_verified else 'not_run'}}