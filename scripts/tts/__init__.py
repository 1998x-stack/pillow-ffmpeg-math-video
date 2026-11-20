"""Deterministic TTS backends; no implicit network access."""
from .base import TTSResult, TTSProvider
from .espeak_backend import EspeakBackend
from .file_backend import ReviewedWavBackend
__all__ = ['TTSResult','TTSProvider','EspeakBackend','ReviewedWavBackend']