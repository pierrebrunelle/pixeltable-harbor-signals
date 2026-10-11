"""Harbor Signals media pipeline built with Pixeltable.

Ingest short VHF/MF/HF radio clips with a cover still and a transcript. Pixeltable
derives audio metadata, peak-normalized / faded / volume-scaled copies, draws
annotated cover boxes via vision helpers, and fans the transcript into a
sentence view with StringSplitter. UDFs tag band lane, callsign, and duration.

Layout: UDFs live in udfs.py; this file holds table models and @pxt.query functions.
No HTTP router — drive the pipeline with `python run.py`.

Run locally:
    pxt schema update app.py harbor
    python run.py
"""
from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf

from udfs import band_lane, callsign_tag, duration_bucket, transcript_word_count

TableModel = pxt.model_base()


class Signals(TableModel, name='signals', has_default_idxs=False):
    """One harbor radio transmission: clip + cover still + transcript."""

    signal_id = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    callsign: pxt.String
    harbor: pxt.String
    band: pxt.String  # vhf / mf / hf
    transcript: pxt.String
    clip: pxt.Audio
    cover: pxt.Image
    # ground-truth and predicted boxes on the cover (xyxy ints)
    gt_boxes: pxt.Json  # list[list[int]]
    pred_boxes: pxt.Json
    box_labels: pxt.Json  # list[str]

    # --- fn.audio primary ---
    meta = pxtf.audio.get_metadata(clip)
    normalized = pxtf.audio.normalize(clip)
    faded_in = pxtf.audio.fade_in(normalized, duration=0.25)
    faded = pxtf.audio.fade_out(faded_in, duration=0.25)
    quiet = pxtf.audio.multiply_volume(clip, factor=0.4)

    # duration from metadata (seconds); nested json path is best-effort
    duration_s: pxt.Float | None

    # --- fn.vision secondary ---
    annotated = pxtf.vision.bboxes_draw(
        cover,
        pred_boxes,
        labels=box_labels,
        color='lime',
        width=2,
    )
    padded_pred = pxtf.vision.bboxes_pad(pred_boxes, 'xyxy', x=4, y=4)

    # UDF chain
    lane = band_lane(band)
    tag = callsign_tag(callsign, harbor, band)
    words = transcript_word_count(transcript)
    dur_bucket = duration_bucket(duration_s)

    __indexes__ = [
        pxt.BtreeIndex(harbor),
        pxt.BtreeIndex(band),
        pxt.BtreeIndex(lane),
    ]


class Sentences(
    TableModel,
    name='sentences',
    base=Signals,
    iterator=pxtf.string.string_splitter(Signals.transcript, separators='sentence'),
):
    """Component view: one row per sentence from each signal transcript."""

    # 'text' is an output column of string_splitter
    length = pxtf.string.len(text)  # type: ignore[name-defined]  # noqa: F821
    upper = pxtf.string.upper(text)  # type: ignore[name-defined]  # noqa: F821


@pxt.query
def by_harbor(harbor: str):
    """Signals for one harbor (harbor index)."""
    return (
        Signals.where(Signals.harbor == harbor)
        .select(
            Signals.signal_id,
            Signals.callsign,
            Signals.band,
            Signals.tag,
            Signals.lane,
            Signals.words,
            Signals.dur_bucket,
        )
        .order_by(Signals.callsign)
    )


@pxt.query
def by_lane(lane: str):
    """Signals in an ops lane (lane index)."""
    return (
        Signals.where(Signals.lane == lane)
        .select(Signals.signal_id, Signals.callsign, Signals.harbor, Signals.band, Signals.tag)
        .order_by(Signals.harbor)
    )


@pxt.query
def long_sentences(min_len: int):
    """Sentences at least min_len characters (StringSplitter view)."""
    return (
        Sentences.where(Sentences.length >= min_len)
        .select(Sentences.callsign, Sentences.harbor, Sentences.text, Sentences.length)
        .order_by(Sentences.length, asc=False)
    )
