"""Seed three sample harbor signals (uses files under data/)."""
from pathlib import Path
import pixeltable as pxt

ROOT = Path(__file__).resolve().parent
AUDIO, IMAGES = ROOT / 'data' / 'audio', ROOT / 'data' / 'images'

ROWS = [
    {
        'callsign': 'WXY-1', 'harbor': 'seattle', 'band': 'vhf',
        'transcript': 'Harbor pilot reports inbound tanker at buoy three. Visibility is good. Stand by for berth assignment.',
        'clip': str(AUDIO / 'alpha.wav'), 'cover': str(IMAGES / 'alpha.png'),
        'gt_boxes': [[40, 30, 120, 100], [20, 20, 60, 60]],
        'pred_boxes': [[38, 28, 122, 102], [18, 18, 62, 62]],
        'box_labels': ['tanker', 'buoy'], 'duration_s': 1.5,
    },
    {
        'callsign': 'K7SEA', 'harbor': 'tacoma', 'band': 'mf',
        'transcript': 'Fog bank forming south of the narrows. Advise reduced speed. Next update in five minutes.',
        'clip': str(AUDIO / 'bravo.wav'), 'cover': str(IMAGES / 'bravo.png'),
        'gt_boxes': [[10, 50, 90, 140], [100, 10, 150, 70]],
        'pred_boxes': [[12, 48, 88, 138], [98, 12, 148, 68]],
        'box_labels': ['fog', 'bridge'], 'duration_s': 2.0,
    },
    {
        'callsign': 'N0RTH', 'harbor': 'seattle', 'band': 'hf',
        'transcript': 'Weather relay from offshore buoy. Squall line approaching from the west.',
        'clip': str(AUDIO / 'charlie.wav'), 'cover': str(IMAGES / 'charlie.png'),
        'gt_boxes': [[50, 40, 140, 110]],
        'pred_boxes': [[48, 42, 138, 112]],
        'box_labels': ['squall'], 'duration_s': 1.2,
    },
]

def main() -> None:
    signals = pxt.get_table('harbor.signals')
    if signals.count():
        signals.delete()
    signals.insert(ROWS)
    print(f'seeded {signals.count()} signals')

if __name__ == '__main__':
    main()
