"""Audio provider contract, independent of rendering/FFmpeg."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

@dataclass(frozen=True)
class TTSResult:
    wav_path: Path
    backend: str
    voice: str
    stderr: str = ''
    pronunciation_approved: bool = False
    provenance: dict = field(default_factory=dict)

class TTSProvider(Protocol):
    def synthesize(self, text: str, output: Path, *, segment_id: str) -> TTSResult: ...