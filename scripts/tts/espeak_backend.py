"""eSpeak NG (cmn) / legacy eSpeak (zh) offline speech backend."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from .base import TTSResult

@dataclass
class EspeakBackend:
    executable: str | None = None
    voice: str | None = None
    speed: int = 145
    pitch: int = 45
    amplitude: int = 120
    def __post_init__(self):
        if not 80 <= self.speed <= 350: raise ValueError('speed out of allowed range')
        if not 0 <= self.pitch <= 99: raise ValueError('pitch out of allowed range')
        if not 0 <= self.amplitude <= 200: raise ValueError('amplitude out of allowed range')
        if self.executable is None:
            self.executable = shutil.which('espeak-ng') or shutil.which('espeak')
        if self.executable is None: raise RuntimeError('Neither espeak-ng nor espeak is installed')
        if self.voice is None:
            self.voice='cmn' if 'espeak-ng' in Path(self.executable).name else 'zh'
    def synthesize(self,text:str,output:Path,*,segment_id:str)->TTSResult:
        if not text.strip():raise ValueError('cannot synthesize blank text')
        output=Path(output)
        output.parent.mkdir(parents=True,exist_ok=True)
        cmd=[self.executable,'-v',self.voice,'-s',str(self.speed),'-p',str(self.pitch),
            '-a',str(self.amplitude),'-w',str(output),text]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        if p.returncode:raise RuntimeError(f'eSpeak failed ({p.returncode}): {p.stderr[-2000:]}')
        if not output.is_file() or output.stat().st_size < 44:
            raise RuntimeError('eSpeak returned no WAV audio')
        return TTSResult(output,'espeak',self.voice,p.stderr,False,{'segment_id':segment_id,'command':'espeak offline'})