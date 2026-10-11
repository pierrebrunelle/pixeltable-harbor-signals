"""Pixeltable UDFs for the harbor-signals media pipeline (module path e.g. `udfs.band_lane`)."""

import pixeltable as pxt


@pxt.udf
def band_lane(band: str) -> str:
    """Map radio band to an ops lane: vhf→near, mf→mid, hf→far, else unknown."""
    b = (band or '').strip().lower()
    return {'vhf': 'near', 'mf': 'mid', 'hf': 'far'}.get(b, 'unknown')


@pxt.udf
def callsign_tag(callsign: str, harbor: str, band: str) -> str:
    """Compact tag like 'WXY-seattle-vhf'."""
    cs = (callsign or 'UNK').strip().upper().replace(' ', '')
    hb = (harbor or 'port').strip().lower().replace(' ', '-')
    bd = (band or 'na').strip().lower()
    return f'{cs}-{hb}-{bd}'


@pxt.udf
def transcript_word_count(text: str) -> int:
    """Naive whitespace word count for a radio transcript."""
    return len((text or '').split())


@pxt.udf
def duration_bucket(seconds: float | None) -> str:
    """Bucket media duration: short (<1.5s), medium, long (>=3s), or unknown."""
    if seconds is None:
        return 'unknown'
    if seconds < 1.5:
        return 'short'
    if seconds < 3.0:
        return 'medium'
    return 'long'
