"""Probe and fully decode a local video; optional first-30-second frame samples."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def verify(video, width=None, height=None, min_seconds=None, max_seconds=None, require_audio=False, samples_dir=None):
    ffprobe, ffmpeg = shutil.which('ffprobe'), shutil.which('ffmpeg')
    if not ffprobe or not ffmpeg:
        raise ValueError('FFmpeg and ffprobe must be installed separately')
    result = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)], check=True, capture_output=True, text=True)
    metadata = json.loads(result.stdout)
    stream = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    duration = float(metadata['format']['duration'])
    audio = any(s['codec_type'] == 'audio' for s in metadata['streams'])
    errors = []
    if width and stream['width'] != width:
        errors.append('Unexpected width')
    if height and stream['height'] != height:
        errors.append('Unexpected height')
    if min_seconds is not None and duration < min_seconds:
        errors.append('Video too short')
    if max_seconds is not None and duration > max_seconds:
        errors.append('Video too long')
    if require_audio and not audio:
        errors.append('Missing audio')
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True, capture_output=True)
    report = {'duration': duration, 'width': stream['width'], 'height': stream['height'], 'frameRate': stream['avg_frame_rate'], 'hasAudio': audio, 'fullDecode': True, 'errors': errors, 'visualReviewPerformed': False, 'audioListeningPerformed': False}
    if samples_dir:
        folder = Path(samples_dir)
        folder.mkdir(parents=True, exist_ok=False)
        subprocess.run([ffmpeg, '-v', 'error', '-n', '-i', str(video), '-t', '30', '-vf', 'fps=1,scale=270:-2', str(folder / 'sample-%03d.png')], check=True)
        with (folder / 'technical-report.json').open('x', encoding='utf-8') as file:
            json.dump(report, file, indent=2)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video')
    p.add_argument('--width', type=int)
    p.add_argument('--height', type=int)
    p.add_argument('--min-seconds', type=float)
    p.add_argument('--max-seconds', type=float)
    p.add_argument('--require-audio', action='store_true')
    p.add_argument('--samples-dir')
    a = p.parse_args()
    try:
        report = verify(**vars(a))
        print(json.dumps(report, indent=2))
        if report['errors']:
            p.exit(1)
    except (ValueError, StopIteration, OSError, subprocess.CalledProcessError) as e:
        p.exit(1, f'{e}\n')
