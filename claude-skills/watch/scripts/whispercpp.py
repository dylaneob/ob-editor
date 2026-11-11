#!/usr/bin/env python3
"""Local whisper.cpp transcription for /watch (OB's addition, 2026-10-22; not part of upstream).

Runs whisper.cpp's `whisper-cli` on a 16 kHz mono WAV made by ffmpeg. Everything stays on this
machine: no network, no API key. Standard library only.

It is used when native captions are missing and either `WATCH_WHISPER_BACKEND=whispercpp`,
no cloud key exists, or the cloud request fails (see whisper.transcribe_video).

Settings (environment, then ~/.config/watch/.env, then the defaults below):
  WATCH_WHISPERCPP_BIN       path to whisper-cli          default: `whisper-cli` on PATH
  WATCH_WHISPERCPP_MODEL     model path or file name      default: first of PREFERRED_MODELS found in MODEL_DIRS
  WATCH_WHISPERCPP_LANGUAGE  spoken language              default: en for *.en models, else auto
  WATCH_WHISPERCPP_THREADS   CPU threads                  default: 4
  WATCH_WHISPERCPP_TIMEOUT   seconds                      default: max(300, 3 x audio length)

Standalone check:  python3 whispercpp.py <media file>   (prints JSON segments)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from config import ConfigError, get_config
from runtime import configure_stdio, diagnostic, run_text
from transcribe import Segments, normalize_segments

MODEL_DIRS = [Path.home() / '.whisper-models', Path.home() / '.cache' / 'whisper']
# Fast English model first: watch needs a readable transcript, not final-caption accuracy.
PREFERRED_MODELS = ['ggml-large-v3-turbo.bin', 'ggml-base.en.bin', 'ggml-small.en.bin', 'ggml-base.bin', 'ggml-small.bin',
                    'ggml-medium.en.bin', 'ggml-medium.bin']
NON_SPEECH = re.compile(r'^\s*[\[\(][^\]\)]*[\]\)]\s*$')  # [BLANK_AUDIO], (music) and the like


def _cfg(cfg: dict | None) -> dict:
    return cfg if cfg is not None else get_config()


def find_binary(cfg: dict | None = None) -> str | None:
    value = (_cfg(cfg).get('whispercpp_bin') or '').strip()
    if value:
        path = Path(value).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    for name in ('whisper-cli', 'whisper-cpp'):
        found = shutil.which(name)
        if found:
            return found
    return None


def find_model(cfg: dict | None = None) -> Path | None:
    value = (_cfg(cfg).get('whispercpp_model') or '').strip()
    if value:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path if path.is_file() else None
        for folder in MODEL_DIRS:
            if (folder / value).is_file():
                return folder / value
        return None
    for name in PREFERRED_MODELS:
        for folder in MODEL_DIRS:
            if (folder / name).is_file():
                return folder / name
    return None


def available(cfg: dict | None = None) -> bool:
    try:
        cfg = _cfg(cfg)
    except ConfigError:
        return False
    return bool(find_binary(cfg) and find_model(cfg) and shutil.which('ffmpeg'))


def model_label(cfg: dict | None = None) -> str:
    try:
        model = find_model(cfg)
    except ConfigError:
        model = None
    return model.name if model else 'no model'


def _segments_from_json(data: dict) -> Segments:
    rows = []
    for item in data.get('transcription') or []:
        if not isinstance(item, dict):
            continue
        text = (item.get('text') or '').strip()
        offsets = item.get('offsets') or {}
        start, end = offsets.get('from'), offsets.get('to')
        if not text or NON_SPEECH.match(text):
            continue
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        start, end = max(0.0, start / 1000.0), max(0.0, end / 1000.0)
        rows.append({'start': start, 'end': max(start, end), 'text': text})
    rows.sort(key=lambda row: row['start'])
    return normalize_segments({'segments': rows})


def transcribe_media(media_path: str, work_dir: Path, cfg: dict | None = None) -> Segments:
    """Extract 16 kHz mono audio and transcribe it with whisper-cli. Raises SystemExit on failure."""
    cfg = _cfg(cfg)
    binary, model = find_binary(cfg), find_model(cfg)
    if not binary:
        raise SystemExit('whisper.cpp is not installed (no whisper-cli). Install with: brew install whisper-cpp')
    if not model:
        raise SystemExit('No whisper.cpp model found. Put ggml-base.en.bin in ~/.whisper-models/ '
                         'or set WATCH_WHISPERCPP_MODEL.')
    if shutil.which('ffmpeg') is None:
        raise SystemExit('ffmpeg is not installed. Install with: brew install ffmpeg')

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    wav = work_dir / 'audio-16k.wav'
    result = run_text(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                       '-i', str(Path(media_path).resolve()), '-vn', '-ac', '1', '-ar', '16000',
                       '-c:a', 'pcm_s16le', str(wav)])
    if result.returncode != 0 or not wav.exists() or wav.stat().st_size <= 44:
        raise SystemExit(f'ffmpeg audio extraction for whisper.cpp failed: {diagnostic(result.stderr, 500)}')
    seconds = (wav.stat().st_size - 44) / 32000.0  # 16-bit mono at 16 kHz

    language = (cfg.get('whispercpp_language') or '').strip() or ('en' if model.name.endswith('.en.bin') else 'auto')
    threads = (cfg.get('whispercpp_threads') or '4').strip()
    if not threads.isdigit() or int(threads) < 1:
        raise SystemExit('WATCH_WHISPERCPP_THREADS must be a positive whole number.')
    timeout_value = (cfg.get('whispercpp_timeout') or '').strip()
    try:
        timeout = float(timeout_value) if timeout_value else max(300.0, seconds * 3)
    except ValueError:
        raise SystemExit('WATCH_WHISPERCPP_TIMEOUT must be a number of seconds.') from None

    prefix = work_dir / 'whispercpp'
    out_json = work_dir / 'whispercpp.json'
    out_json.unlink(missing_ok=True)
    print(f'[watch] whisper.cpp ({model.name}, language {language}) transcribing '
          f'{seconds / 60:.1f} min of audio on this machine…', file=sys.stderr)
    result = run_text([binary, '-m', str(model), '-f', str(wav), '-l', language, '-t', threads,
                       '-oj', '-of', str(prefix), '-np'], timeout=timeout)
    if result.returncode != 0 or not out_json.exists():
        raise SystemExit(f'whisper.cpp failed (exit {result.returncode}): {diagnostic(result.stderr, 500)}')
    try:
        data = json.loads(out_json.read_text(encoding='utf-8', errors='replace'))
        segments = _segments_from_json(data)
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit(f'whisper.cpp returned unreadable JSON: {exc}') from None
    if not segments:
        print('[watch] whisper.cpp detected no speech', file=sys.stderr)
    print(f'[watch] transcribed {len(segments)} segments via whisper.cpp', file=sys.stderr)
    return segments


if __name__ == '__main__':
    import tempfile
    configure_stdio()
    if len(sys.argv) != 2:
        raise SystemExit('usage: whispercpp.py <media file>')
    with tempfile.TemporaryDirectory(prefix='watch-whispercpp-') as tmp:
        segs = transcribe_media(sys.argv[1], Path(tmp))
    print(json.dumps({'backend': 'whispercpp', 'model': model_label(), 'segments': segs}, indent=2))
