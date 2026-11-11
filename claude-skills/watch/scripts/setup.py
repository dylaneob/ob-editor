#!/usr/bin/env python3
"""Base preflight and backend configuration. OB copy 2026-10-22: Gemini and the managed WhisperX install are removed; whisper.cpp readiness is reported."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from config import (CONFIG_DIR, CONFIG_FILE, ConfigError, DETAILS, ENGINES, get_config,
                    load_api_key, read_env_file, write_settings)
import whispercpp
from runtime import configure_stdio, diagnostic, run_text

REQUIRED_BINARIES = ['ffmpeg', 'ffprobe', 'yt-dlp']
_PERM_WARNED: set[str] = set()
ENV_TEMPLATE = '''# /watch configuration. No shell interpolation; last assignment wins.
# Native captions always come first. Optional fallback: auto|whispercpp|groq|openai|none.
# auto tries a Groq, then OpenAI key; with no key, or if the cloud request fails, whisper.cpp runs locally.
# whispercpp never uploads audio. The first-run skill wizard sets WATCH_DETAIL and WATCH_WHISPER_BACKEND.
GROQ_API_KEY=
OPENAI_API_KEY=
'''


def _which(name):
    return shutil.which(name)


def _check_binaries():
    return [name for name in REQUIRED_BINARIES if not _which(name)]


def _check_file_permissions(path: Path) -> None:
    # Native Windows mode bits do not describe NTFS ACLs. WSL Linux homes do.
    if os.name == 'nt' or platform.system() == 'Windows' or str(path) in _PERM_WARNED:
        return
    try:
        if path.stat().st_mode & 0o044:
            _PERM_WARNED.add(str(path))
            print(f'[watch] WARNING: {path} is readable by other users. Run: chmod 600 "{path}"', file=sys.stderr)
    except OSError:
        pass


def _have_api_key():
    backend, key = load_api_key()
    return bool(key), backend


def is_first_run():
    return read_env_file(CONFIG_FILE).get('SETUP_COMPLETE') != 'true'


def _scaffold_env():
    if CONFIG_FILE.exists():
        read_env_file(CONFIG_FILE)  # Fail safely before modifying bad config.
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(ENV_TEMPLATE)
    return True


def _write_setup_complete():
    _scaffold_env()
    write_settings({'SETUP_COMPLETE': 'true'}, CONFIG_FILE)


def _brew_pkg(missing):
    return list(dict.fromkeys('ffmpeg' if name == 'ffprobe' else name for name in missing))


def _install_step(cmd, step):
    print(f"[setup] {step}: {' '.join(map(str, cmd))}", file=sys.stderr, flush=True)
    try:
        result = subprocess.run(list(map(str, cmd)))
    except OSError as exc:
        raise SystemExit(f'{step}: cannot run {cmd[0]} ({type(exc).__name__}); install or repair that executable, then retry.') from None
    if result.returncode:
        raise SystemExit(f'{step} failed (exit {result.returncode}): retry setup after checking the error above.')


def _install_macos(missing):
    if not _which('brew'):
        return False, 'Homebrew is missing. Install it from https://brew.sh, then rerun setup.'
    _install_step(['brew', 'install', *_brew_pkg(missing)], 'Install media dependencies')
    return True, 'Installed media dependencies with Homebrew.'


def _install_hint_linux(missing):
    hints = []
    if 'ffmpeg' in _brew_pkg(missing):
        hints.append('apt: sudo apt install ffmpeg (or the equivalent package for your distribution)')
    if 'yt-dlp' in missing:
        hints.append('Install pipx, then: pipx install "yt-dlp[default,curl-cffi]"; pipx ensurepath. For YouTube also install Deno: https://deno.com/')
    return '\n'.join(hints)


def _install_hint_windows(missing):
    hints = []
    if 'ffmpeg' in _brew_pkg(missing):
        hints.append('winget install --id Gyan.FFmpeg --exact')
    if 'yt-dlp' in missing:
        hints.extend(['winget install --id yt-dlp.yt-dlp --exact', 'winget install --id DenoLand.Deno --exact'])
    return '\n'.join(hints) + '\nReopen your terminal/agent after PATH changes.'


def _probe(cmd):
    try:
        result = run_text(cmd, timeout=20)
        output = result.stdout or result.stderr
        return {'ok': result.returncode == 0, 'version_line': output.splitlines()[0] if output else None, 'output': diagnostic(output, 2500)}
    except SystemExit as exc:
        return {'ok': False, 'output': str(exc)}


def _whispercpp_status(cfg):
    binary, model = whispercpp.find_binary(cfg), whispercpp.find_model(cfg)
    return {'ready': bool(binary and model and _which('ffmpeg')), 'bin': binary, 'model': str(model) if model else None}


def _status(detailed=False):
    missing = _check_binaries()
    _check_file_permissions(CONFIG_FILE)
    cfg = get_config()
    engine = 'local'  # OB copy: the Gemini engine is removed
    binaries_required = True
    has_key, detected = _have_api_key()
    chosen = cfg['whisper_backend']
    backend = (detected or 'whispercpp') if chosen == 'auto' else chosen
    local = _whispercpp_status(cfg)
    if chosen == 'whispercpp':
        backend_ready = local['ready']
    elif backend in ('groq', 'openai'):
        # A key that is present can still be invalid; whisper.cpp catches a failed request.
        backend_ready = bool(load_api_key(backend)[1]) or local['ready']
    else:
        backend_ready = chosen == 'none' or local['ready']
    blocked = bool(missing) and binaries_required
    result = {'status': 'needs_install' if blocked else 'ready', 'can_proceed': not blocked,
              'engine': engine, 'configured_engine': cfg['engine'], 'binaries_required': binaries_required,
              'first_run': is_first_run(), 'setup_complete': not is_first_run(),
              'missing_binaries': missing, 'whisper_backend': backend, 'configured_backend': chosen,
              'has_api_key': has_key, 'backend_ready': backend_ready,
              'whispercpp_ready': local['ready'], 'whispercpp_bin': local['bin'],
              'whispercpp_model': local['model'], 'config_file': str(CONFIG_FILE),
              'watch_detail': cfg['detail'], 'platform': platform.system()}
    if detailed:
        tools = {}
        for name in REQUIRED_BINARIES:
            path = _which(name)
            tools[name] = {'path': path, **(_probe([path, '--version' if name == 'yt-dlp' else '-version']) if path else {'ok': False})}
        tools['whisper-cli'] = {'path': local['bin'], 'model': local['model'], 'ok': local['ready']}
        ytdlp = _which('yt-dlp')
        result['tools'] = tools
        result['youtube'] = {
            'deno': _which('deno'), 'node': _which('node'),
            'ejs': 'unknown (inspect the owning yt-dlp installation; no network probe)',
            'impersonation': _probe([ytdlp, '--ignore-config', '--list-impersonate-targets']) if ytdlp else None,
            'update_hint': 'Update the owning package: brew upgrade yt-dlp; pipx upgrade yt-dlp; or winget upgrade --id yt-dlp.yt-dlp --exact. Verify the executable path above.',
        }
    return result


def cmd_check():
    # Optional credentials and local-model readiness never block base watch.
    status = _status()
    if status['can_proceed']:
        return 0
    print(f"[watch] Missing {', '.join(status['missing_binaries'])}. Run python3 \"{Path(__file__).resolve()}\".", file=sys.stderr)
    return 2


def cmd_json():
    print(json.dumps(_status(detailed=True), indent=2))
    return 0


def cmd_install(backend=None, detail=None, engine=None):
    if engine:
        _scaffold_env()
        write_settings({'WATCH_ENGINE': engine}, CONFIG_FILE)
    missing = _check_binaries()
    if missing:
        system = platform.system()
        if system == 'Darwin':
            ok, message = _install_macos(missing)
            print(f'[setup] {message}', file=sys.stderr)
            if not ok or _check_binaries():
                return 2
        else:
            print(_install_hint_windows(missing) if system == 'Windows' else _install_hint_linux(missing), file=sys.stderr)
            return 2
    _scaffold_env()
    if detail:
        write_settings({'WATCH_DETAIL': detail}, CONFIG_FILE)
    if backend == 'whispercpp' and not _whispercpp_status(get_config())['ready']:
        print('[setup] whisper.cpp is not ready: install it (brew install whisper-cpp) and put a ggml model '
              'such as ggml-base.en.bin in ~/.whisper-models/, then rerun --backend whispercpp.', file=sys.stderr)
        return 3
    if backend:
        write_settings({'WATCH_WHISPER_BACKEND': backend}, CONFIG_FILE)
        if backend in ('groq', 'openai') and not load_api_key(backend)[1]:
            print(f'[setup] Base watch is ready. Add {backend.upper()}_API_KEY privately to {CONFIG_FILE}, then rerun --backend {backend}.', file=sys.stderr)
            return 3
        _write_setup_complete()
    print(f'[setup] Base watch is ready. Configuration: {CONFIG_FILE}')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--json', action='store_true')
    parser.add_argument('--backend', choices=['auto', 'whispercpp', 'groq', 'openai', 'none'])
    parser.add_argument('--detail', choices=sorted(DETAILS))
    parser.add_argument('--engine', choices=sorted(ENGINES))
    args = parser.parse_args()
    try:
        if args.check:
            return cmd_check()
        if args.json:
            return cmd_json()
        return cmd_install(args.backend, args.detail, args.engine)
    except (ConfigError, OSError, ValueError) as exc:
        print(f'[setup] {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    configure_stdio()
    raise SystemExit(main())
