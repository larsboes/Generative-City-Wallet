"""Fence-stripping JSON helper used by Ollama path."""

import json

import pytest

from spark.services.offer_generator import _parse_llm_json_blob


def test_parse_plain_json():
    raw = '{"content": {"headline": "a", "subtext": "b", "cta_text": "c", "emotional_hook": "d"}, "genui": {"color_palette": "warm_amber", "typography_weight": "medium", "background_style": "gradient", "imagery_prompt": "x", "urgency_style": "gentle_pulse", "card_mood": "cozy"}, "framing_band_used": "quiet_intentional"}'
    d = _parse_llm_json_blob(raw)
    assert d["content"]["headline"] == "a"


def test_parse_fenced_json():
    raw = '```json\n{"x": 1}\n```'
    assert _parse_llm_json_blob(raw) == {"x": 1}


def test_parse_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_llm_json_blob("not json")
