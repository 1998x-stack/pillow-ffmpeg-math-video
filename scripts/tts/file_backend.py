"""Use already reviewed WAV clips from any licensed TTS engine.

Does not implement or assume access to a cloud speech API.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil
from .base import TTSResult

@dataclass
class ReviewedWavBackend:
    clips: dict[str, str]
    reviewed_ids: frozenset[str]
    voice: str = 'externally-provided'
    license_note: str = ''
    def synthesize(self,text:str,output:Path,*,segment_id:str)->TTSResult:
        if segment_id not in self.clips:raise KeyError(f'missing WAV clip {segment_id}')
        source=Path(self.clips[segment_id])
        if not source.is_file():raise FileNotFoundError(source)
        if source.suffix.lower()!='.wav':raise ValueError('WAV required for deterministic audio input')
        output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,output)
        return TTSResult(output,'reviewed-wav',self.voice,'',segment_id in self.reviewed_ids,
                         {'source':str(source),'license_note':self.license_note,'text_expected':text})