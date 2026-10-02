"""Export supplied aligned segments or words to UTF-8 SRT. No ASR or translation."""
import argparse
import json
import math
from pathlib import Path


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def convert(data, max_words=3):
    if max_words < 1:
        raise ValueError('max_words must be positive')
    words = 'words' in data
    entries = data.get('words' if words else 'segments', [])
    if not entries:
        raise ValueError('Provide non-empty segments or words')
    valid, previous = [], 0.0
    for item in entries:
        start, end = float(item['start']), float(item['end'])
        text = str(item.get('text', item.get('word', ''))).strip()
        if not math.isfinite(start) or not math.isfinite(end) or start < previous or end <= start or not text:
            raise ValueError('Timings must be finite, non-negative, non-overlapping and non-empty')
        valid.append((start, end, text))
        previous = end
    groups = []
    if words:
        for i in range(0, len(valid), max_words):
            group = valid[i:i + max_words]
            groups.append((group[0][0], group[-1][1], ' '.join(x[2] for x in group)))
    else:
        groups = valid
    return '\n'.join(f'{i}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n' for i, (start, end, text) in enumerate(groups, 1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('timings')
    p.add_argument('output')
    p.add_argument('--max-words', type=int, default=3)
    a = p.parse_args()
    try:
        result = convert(json.loads(Path(a.timings).read_text(encoding='utf-8')), a.max_words)
        with Path(a.output).open('x', encoding='utf-8') as file:
            file.write(result)
    except (ValueError, KeyError, OSError) as e:
        p.exit(1, f'{e}\n')
