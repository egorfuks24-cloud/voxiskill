import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'vox-animation' / 'scripts' / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Helpers(unittest.TestCase):
    def test_multilingual_captions(self):
        result = module('captions_srt').convert({'segments': [{'start': 0, 'end': 1, 'text': 'Über Frankreich — déjà vu.'}]})
        self.assertIn('Über Frankreich — déjà vu.', result)
        self.assertIn('00:00:00,000 --> 00:00:01,000', result)

    def test_bad_times(self):
        for start, end in [(-1, 2), (1, 1), (float('nan'), 2)]:
            with self.assertRaises(ValueError):
                module('captions_srt').convert({'segments': [{'start': start, 'end': end, 'text': 'Test'}]})

    def test_word_groups(self):
        result = module('captions_srt').convert({'words': [{'start': i, 'end': i + .5, 'word': w} for i, w in enumerate(['One', 'two', 'three', 'four'])]})
        self.assertIn('One two three', result)
        self.assertIn('four', result)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg unavailable')
    def test_encode_decode_and_reject_overwrite(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            frames = folder / 'frames'
            frames.mkdir()
            for i in range(12):
                Image.new('RGB', (180, 320), (i * 20, 30, 50)).save(frames / f'frame-{i:06d}.png')
            audio = folder / 'audio.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', str(audio)], check=True)
            output = folder / 'fixture.mp4'
            module('render_frames').run(frames, output, 6, audio)
            report = module('verify_video').verify(output, 180, 320, 1.9, 2.1, True, folder / 'samples')
            self.assertEqual(report['errors'], [])
            self.assertTrue(report['fullDecode'])
            self.assertFalse(report['visualReviewPerformed'])
            self.assertEqual(len(list((folder / 'samples').glob('*.png'))), 2)
            with self.assertRaises(ValueError):
                module('render_frames').run(frames, output, 6)
            (frames / 'frame-000003.png').unlink()
            with self.assertRaises(ValueError):
                module('render_frames').run(frames, folder / 'bad.mp4', 6)


if __name__ == '__main__':
    unittest.main()
