"""OTIO タイムライン・クリップ構築"""

import html

FPS = 24.0

DEFAULT_STYLE = {
    "font": "Al Bayan",
    "fontSize": "80",
    "fontColor": "#ffffff",
    "bold": "1",
    "lineSpacing": "-50",
    "strokeColor": "#000000",
    "strokeSize": 16,
    "position": [0.5, 0.1],
    "shadowColor": "#000000",
    "shadowOffset": [0.0052, -0.0111],
    "shadowBlur": 1,
    "shadowOpacity": 100,
}


# ── OTIO ヘルパー ─────────────────────────────────────


def _rational_time(value, rate=FPS):
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": rate, "value": float(value)}


def _time_range(start, duration):
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": _rational_time(start),
        "duration": _rational_time(duration),
    }


def _resolve_effect(name, effect_type, parameters=None):
    return {
        "OTIO_SCHEMA": "Effect.1",
        "metadata": {
            "Resolve_OTIO": {
                "Effect Name": name,
                "Enabled": True,
                "Name": name,
                "Parameters": parameters or [],
                "Type": effect_type,
            }
        },
        "name": "",
        "effect_name": "Resolve Effect",
    }


def _build_track(name, kind, children, locked=False, **extra_meta):
    metadata = {"Resolve_OTIO": {"Locked": locked, **extra_meta}}
    return {
        "OTIO_SCHEMA": "Track.1",
        "metadata": metadata,
        "name": name,
        "source_range": None,
        "effects": [],
        "markers": [],
        "enabled": True,
        "children": children,
        "kind": kind,
    }


# ── クリップ生成 ──────────────────────────────────────


def _create_gap(duration_frames):
    return {
        "OTIO_SCHEMA": "Gap.1",
        "metadata": {},
        "name": "",
        "source_range": _time_range(0, duration_frames),
        "effects": [],
        "markers": [],
        "enabled": True,
    }


def _build_title_html(text, style):
    font_weight = "600" if style["bold"] == "1" else "400"
    escaped = html.escape(text)
    return (
        f'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" '
        f'"http://www.w3.org/TR/REC-html40/strict.dtd">\n'
        f'<html><head><meta name="qrichtext" content="1" />'
        f'<style type="text/css">\n'
        f"p, li {{ white-space: pre-wrap; }}\n"
        f"</style></head>"
        f"<body style=\" font-family:'.AppleSystemUIFont'; "
        f'font-size:13pt; font-weight:400; font-style:normal;">\n'
        f'<p align="center" style=" margin-top:0px; margin-bottom:0px; '
        f"margin-left:0px; margin-right:0px; -qt-block-indent:0; "
        f'text-indent:0px; line-height:{style["lineSpacing"]}; '
        f'-qt-line-height-type: line-distance;">'
        f"<span style=\" font-family:'{style['font']}'; "
        f'font-size:{style["fontSize"]}pt; font-weight:{font_weight}; '
        f'color:{style["fontColor"]};">'
        f"{escaped}</span></p></body></html>"
    )


def _create_text_clip(clip, style):
    title_html = _build_title_html(clip["text"], style)

    return {
        "OTIO_SCHEMA": "Clip.2",
        "metadata": {"Resolve_OTIO": {}},
        "name": "Text",
        "source_range": _time_range(0, clip["duration_frames"]),
        "effects": [
            _resolve_effect("Transform", 2),
            _resolve_effect("Cropping", 3),
            _resolve_effect("Composite", 1),
            _resolve_effect("Video Faders", 36),
        ],
        "markers": [],
        "enabled": True,
        "media_references": {
            "DEFAULT_MEDIA": {
                "OTIO_SCHEMA": "GeneratorReference.1",
                "metadata": {"Resolve_OTIO": {"Generator Type": "Rich"}},
                "name": "Text",
                "available_range": None,
                "available_image_bounds": None,
                "generator_kind": "Rich",
                "parameters": {
                    "Resolve_OTIO": [
                        {
                            "Effect Name": "Rich Text",
                            "Enabled": True,
                            "Name": "Rich Text",
                            "Parameters": [
                                {
                                    "Default Parameter Value": "Title",
                                    "Parameter ID": "rich text",
                                    "Parameter Value": "Title",
                                    "Variant Type": "String",
                                },
                                {
                                    "Parameter ID": "title blob",
                                    "Title HTML": title_html,
                                },
                                {
                                    "Default Parameter Value": 4,
                                    "Parameter ID": "anchor",
                                    "Parameter Value": 4,
                                    "Variant Type": "UInt",
                                },
                                {
                                    "Default Parameter Value": [0.5, 0.5],
                                    "Key Frames": {},
                                    "Parameter ID": "position",
                                    "Parameter Value": style["position"],
                                    "Variant Type": "POINTF",
                                },
                                {
                                    "Default Parameter Value": 1.0,
                                    "Key Frames": {},
                                    "Parameter ID": "transformationZoomX",
                                    "Parameter Value": 1.0,
                                    "Variant Type": "Double",
                                    "maxValue": 4.0,
                                    "minValue": 0.25,
                                },
                                {
                                    "Default Parameter Value": 1.0,
                                    "Key Frames": {},
                                    "Parameter ID": "transformationZoomY",
                                    "Parameter Value": 1.0,
                                    "Variant Type": "Double",
                                    "maxValue": 4.0,
                                    "minValue": 0.25,
                                },
                                {
                                    "Default Parameter Value": True,
                                    "Parameter ID": "transformationZoomLink",
                                    "Parameter Value": True,
                                    "Variant Type": "Bool",
                                },
                                {
                                    "Default Parameter Value": 0.0,
                                    "Key Frames": {},
                                    "Parameter ID": "transformationRotationAngle",
                                    "Parameter Value": 0.0,
                                    "Variant Type": "Double",
                                    "maxValue": 100000.0,
                                    "minValue": -100000.0,
                                },
                            ],
                            "Type": 24,
                        },
                        {
                            "Effect Name": "Drop Shadow",
                            "Enabled": True,
                            "Name": "Drop Shadow",
                            "Parameters": [
                                {
                                    "Default Parameter Value": "#000000",
                                    "Parameter ID": "shadow color",
                                    "Parameter Value": style["shadowColor"],
                                    "Variant Type": "Color",
                                },
                                {
                                    "Default Parameter Value": [0.0, 0.0],
                                    "Key Frames": {},
                                    "Parameter ID": "shadow offset",
                                    "Parameter Value": style["shadowOffset"],
                                    "Variant Type": "POINTF",
                                },
                                {
                                    "Default Parameter Value": 20,
                                    "Key Frames": {},
                                    "Parameter ID": "shadow",
                                    "Parameter Value": style["shadowBlur"],
                                    "Variant Type": "Int",
                                    "maxValue": 100.0,
                                    "minValue": 1.0,
                                },
                                {
                                    "Default Parameter Value": 75,
                                    "Key Frames": {},
                                    "Parameter ID": "shadow opacity",
                                    "Parameter Value": style["shadowOpacity"],
                                    "Variant Type": "Int",
                                    "maxValue": 100.0,
                                    "minValue": 0.0,
                                },
                            ],
                            "Type": 8,
                        },
                        {
                            "Effect Name": "Stroke",
                            "Enabled": True,
                            "Name": "Stroke",
                            "Parameters": [
                                {
                                    "Default Parameter Value": "#ffffff",
                                    "Parameter ID": "strokeColor",
                                    "Parameter Value": style["strokeColor"],
                                    "Variant Type": "Color",
                                },
                                {
                                    "Default Parameter Value": 1,
                                    "Parameter ID": "strokeSize",
                                    "Parameter Value": style["strokeSize"],
                                    "Variant Type": "Int",
                                    "maxValue": 16.0,
                                    "minValue": 0.0,
                                },
                                {
                                    "Default Parameter Value": False,
                                    "Parameter ID": "strokeOutsideOnly",
                                    "Parameter Value": True,
                                    "Variant Type": "Bool",
                                },
                            ],
                            "Type": 28,
                        },
                    ]
                },
            }
        },
        "active_media_reference_key": "DEFAULT_MEDIA",
    }


def _create_audio_clip(clip):
    return {
        "OTIO_SCHEMA": "Clip.2",
        "metadata": {"Resolve_OTIO": {}},
        "name": clip["filename"],
        "source_range": _time_range(0, clip["duration_frames"]),
        "effects": [],
        "markers": [],
        "enabled": True,
        "media_references": {
            "DEFAULT_MEDIA": {
                "OTIO_SCHEMA": "ExternalReference.1",
                "metadata": {},
                "name": clip["filename"],
                "available_range": _time_range(0, clip["duration_frames"]),
                "available_image_bounds": None,
                "target_url": clip["abs_path"],
            }
        },
        "active_media_reference_key": "DEFAULT_MEDIA",
    }


# ── タイムライン構築 ──────────────────────────────────


def build_timeline(project_name, clips, chars, total_frames, style_templates):
    """OTIO タイムライン全体を構築する"""
    video_tracks = {char: [] for char in chars}
    audio_children = []

    for clip in clips:
        style = DEFAULT_STYLE.copy()
        if clip["char"] in style_templates:
            style.update(style_templates[clip["char"]])

        text_clip = _create_text_clip(clip, style)

        for char in chars:
            if char == clip["char"]:
                video_tracks[char].append(text_clip)
            else:
                video_tracks[char].append(_create_gap(clip["duration_frames"]))

        audio_children.append(_create_audio_clip(clip))

    track_children = []

    track_children.append(
        _build_track("Background", "Video", [_create_gap(total_frames)])
    )

    for char in chars:
        track_children.append(
            _build_track(f"Subtitle - {char}", "Video", video_tracks[char])
        )

    track_children.append(
        _build_track(
            "Audio 1",
            "Audio",
            audio_children,
            **{"Audio Type": "Mono", "SoloOn": False},
        )
    )

    return {
        "OTIO_SCHEMA": "Timeline.1",
        "metadata": {"Resolve_OTIO": {"Resolve OTIO Meta Version": "1.0"}},
        "name": project_name,
        "global_start_time": _rational_time(86400.0),
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "metadata": {},
            "name": "",
            "source_range": None,
            "effects": [],
            "markers": [],
            "enabled": True,
            "children": track_children,
        },
    }
