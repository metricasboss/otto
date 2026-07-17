from __future__ import annotations

from otto.engine.reporters import json_out, sarif, text

_RENDERERS = {"text": text.render, "json": json_out.render, "sarif": sarif.render}


def get_renderer(fmt: str):
    if fmt not in _RENDERERS:
        raise ValueError(f"Unknown format: {fmt!r} (use text, json or sarif)")
    return _RENDERERS[fmt]
