"""Encode locally rendered, consecutive frame-000000.png files. No network."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(directory, output, fps=30, audio=None):
    from PIL import Image
    directory, output = Path(directory), Path(output)
    if output.exists():
        raise ValueError('Output already exists')
    if fps <= 0 or fps > 120:
        raise ValueError('FPS must be between 0 and 120')
    frames = sorted(directory.glob('frame-*.png'))
    if not frames or any(p.name != f'frame-{i:06d}.png' for i, p in enumerate(frames)):
        raise ValueError('Frames must be consecutive, starting at frame-000000.png')
    size = None
    for path in frames:
        with Image.open(path) as im:
            if size is None:
                size = im.size
            if im.size != size or any(n % 2 for n in im.size):
                raise ValueError('All frame dimensions must match and be even')
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise ValueError('Install FFmpeg separately before running')
    duration = len(frames) / fps
    if audio:
        result = subprocess.run([ffprobe, '-v', 'error', '-show_format', '-of', 'json', str(audio)], check=True, capture_output=True, text=True)
        if float(json.loads(result.stdout)['format']['duration']) > duration + .05:
            raise ValueError('Audio exceeds video duration; revise timing instead of cutting speech')
    args = [ffmpeg, '-v', 'error', '-n', '-framerate', str(fps), '-i', str(directory / 'frame-%06d.png')]
    if audio:
        args += ['-i', str(audio), '-af', 'apad', '-c:a', 'aac']
    args += ['-t', str(duration), '-c:v', 'libx264', '-threads', '2', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
    subprocess.run(args, check=True)
    return duration


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('frames')
    p.add_argument('output')
    p.add_argument('--fps', type=float, default=30)
    p.add_argument('--audio')
    a = p.parse_args()
    try:
        print(f'Encoded {run(a.frames, a.output, a.fps, a.audio):.3f} seconds')
    except (ValueError, subprocess.CalledProcessError) as e:
        p.exit(1, f'{e}\n')
