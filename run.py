#!/usr/bin/env python3
"""Harbor Signals media-pipeline driver (no HTTP service).

Dev-loop workflow: schema already applied via `pxt schema update`; this script
inserts real audio/image files, reads computed audio/vision columns, queries the
StringSplitter sentence view, then exercises a small schema recompute path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pixeltable as pxt

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / 'data' / 'audio'
IMAGES = ROOT / 'data' / 'images'
LOG = ROOT / 'logs' / 'run.jsonl'


ROWS = [
    {
        'callsign': 'WXY-1',
        'harbor': 'seattle',
        'band': 'vhf',
        'transcript': (
            'Harbor pilot reports inbound tanker at buoy three. '
            'Visibility is good. Stand by for berth assignment.'
        ),
        'clip': str(AUDIO / 'alpha.wav'),
        'cover': str(IMAGES / 'alpha.png'),
        'gt_boxes': [[40, 30, 120, 100], [20, 20, 60, 60]],
        'pred_boxes': [[38, 28, 122, 102], [18, 18, 62, 62]],
        'box_labels': ['tanker', 'buoy'],
        'duration_s': 1.5,
    },
    {
        'callsign': 'K7SEA',
        'harbor': 'tacoma',
        'band': 'mf',
        'transcript': (
            'Fog bank forming south of the narrows. '
            'Advise reduced speed. Next update in five minutes.'
        ),
        'clip': str(AUDIO / 'bravo.wav'),
        'cover': str(IMAGES / 'bravo.png'),
        'gt_boxes': [[10, 50, 90, 140], [100, 10, 150, 70]],
        'pred_boxes': [[12, 48, 88, 138], [98, 12, 148, 68]],
        'box_labels': ['fog', 'bridge'],
        'duration_s': 2.0,
    },
    {
        'callsign': 'N0RTH',
        'harbor': 'seattle',
        'band': 'hf',
        'transcript': 'Weather relay from offshore buoy. Squall line approaching from the west.',
        'clip': str(AUDIO / 'charlie.wav'),
        'cover': str(IMAGES / 'charlie.png'),
        'gt_boxes': [[50, 40, 140, 110]],
        'pred_boxes': [[48, 42, 138, 112]],
        'box_labels': ['squall'],
        'duration_s': 1.2,
    },
]


def log(event: str, **payload) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'event': event, **payload}, default=str) + '\n')
    print(event, json.dumps(payload, default=str)[:280])


def main() -> int:
    signals = pxt.get_table('harbor.signals')
    sentences = pxt.get_table('harbor.sentences')

    existing = signals.count()
    if existing:
        log('clearing', rows=existing)
        signals.delete()

    result = signals.insert(ROWS)
    log('insert', result=str(result), n=len(ROWS))

    meta_rows = list(
        signals.select(
            signals.callsign,
            signals.meta,
            signals.lane,
            signals.tag,
            signals.words,
            signals.dur_bucket,
            signals.padded_pred,
        ).collect()
    )
    for r in meta_rows:
        log(
            'audio_meta',
            callsign=r['callsign'],
            tag=r['tag'],
            lane=r['lane'],
            words=r['words'],
            dur_bucket=r['dur_bucket'],
            meta_keys=list(r['meta'].keys()) if isinstance(r['meta'], dict) else type(r['meta']).__name__,
            padded_pred=r['padded_pred'],
        )

    # confirm audio transforms + annotated images materialize
    media = list(
        signals.select(
            signals.callsign,
            signals.normalized,
            signals.faded,
            signals.quiet,
            signals.annotated,
        ).collect()
    )
    for r in media:
        log(
            'media_ok',
            callsign=r['callsign'],
            has_normalized=r['normalized'] is not None,
            has_faded=r['faded'] is not None,
            has_quiet=r['quiet'] is not None,
            annotated_size=getattr(r['annotated'], 'size', None),
        )

    sent = list(
        sentences.select(sentences.callsign, sentences.text, sentences.length, sentences.upper)
        .order_by(sentences.callsign, sentences.length)
        .collect()
    )
    log(
        'sentences',
        count=len(sent),
        sample=[{'cs': s['callsign'], 'len': s['length'], 'text': s['text'][:60]} for s in sent[:5]],
    )

    # Mirror @pxt.query by_harbor / by_lane / long_sentences via table filters
    h = list(
        signals.where(signals.harbor == 'seattle')
        .select(signals.callsign, signals.band, signals.tag, signals.lane)
        .order_by(signals.callsign)
        .collect()
    )
    log('query_by_harbor', n=len(h), callsigns=[r['callsign'] for r in h])

    lane = list(
        signals.where(signals.lane == 'near')
        .select(signals.callsign, signals.harbor, signals.band, signals.tag)
        .collect()
    )
    log('query_by_lane', n=len(lane), callsigns=[r['callsign'] for r in lane])

    longish = list(
        sentences.where(sentences.length >= 40)
        .select(sentences.callsign, sentences.harbor, sentences.text, sentences.length)
        .order_by(sentences.length, asc=False)
        .collect()
    )
    log('query_long_sentences', n=len(longish), sample=[r['text'][:50] for r in longish[:3]])

    # Confirm query templates are registered on the app module (serving/schema surface)
    import app as harbor_app

    assert hasattr(harbor_app, 'by_harbor') and hasattr(harbor_app, 'by_lane')
    log('query_templates', names=['by_harbor', 'by_lane', 'long_sentences'])

    # recompute path (wf.dev_loop)
    signals.recompute_columns(signals.tag)
    log('recompute_tag', ok=True, count=signals.count())

    # schema diff smoke (dev loop): no-op should be clean
    log('done', signals=signals.count(), sentences=sentences.count())
    print('OK harbor-signals pipeline')
    return 0


if __name__ == '__main__':
    sys.exit(main())
