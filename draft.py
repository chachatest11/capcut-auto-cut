"""
CapCut draft builder (cross-platform: Windows + macOS).
Creates draft_content.json + draft_meta_info.json in the CapCut Projects folder.
"""
import json
import uuid
import time
import math
import sys
from pathlib import Path

US = 1_000_000  # microseconds per second
_IS_MAC = sys.platform == "darwin"


def _find_draft_root() -> Path:
    """Locate CapCut's draft folder for the current OS.

    macOS has two possible locations depending on install source
    (capcut.com direct download vs. Mac App Store sandbox).
    """
    home = Path.home()
    if _IS_MAC:
        candidates = [
            home / "Movies/CapCut/User Data/Projects/com.lveditor.draft",
            home / "Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft",
            home / "Library/Application Support/CapCut/User Data/Projects/com.lveditor.draft",
        ]
    else:  # Windows
        candidates = [
            home / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft",
        ]
    for c in candidates:
        if c.parent.exists():   # the Projects dir exists → this is the active one
            return c
    return candidates[0]         # fall back to the primary location


DRAFT_ROOT = _find_draft_root()


def _find_font() -> str:
    """Best-effort path to a CapCut/system font. Empty string → CapCut default."""
    home = Path.home()
    if _IS_MAC:
        for c in [
            Path("/Applications/CapCut.app/Contents/Resources/Font/SystemFont/en.ttf"),
            Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
            Path("/System/Library/Fonts/Helvetica.ttc"),
        ]:
            if c.exists():
                return str(c)
    else:  # Windows
        primary = home / "AppData/Local/CapCut/Apps/8.9.0.3794/Resources/Font/SystemFont/en.ttf"
        if primary.exists():
            return str(primary).replace("\\", "/")
        found = list((home / "AppData/Local/CapCut/Apps").glob("*/Resources/Font/SystemFont/en.ttf"))
        if found:
            return str(found[0]).replace("\\", "/")
    return ""   # CapCut falls back to its default font

PLATFORM = {
    "os": "mac" if _IS_MAC else "windows",
    "os_version": "13.0.0" if _IS_MAC else "10.0.26200",
    "app_id": 359289,
    "app_version": "8.9.0",
    "app_source": "cc",
    "device_id": "autocut0000000000000000000000000",
    "hard_disk_id": "",
    "mac_address": "000000000000000000000000000000",
}


def _uid() -> str:
    return str(uuid.uuid4()).upper()


def _us(sec: float) -> int:
    return int(round(sec * US))


def _video_material(video_path: str, duration_sec: float, width: int, height: int) -> dict:
    mid = _uid()
    p = Path(video_path)
    return {
        "id": mid,
        "unique_id": "",
        "type": "video",
        "duration": _us(duration_sec),
        "path": str(p).replace("\\", "/"),
        "media_path": "",
        "local_id": "",
        "has_audio": True,
        "reverse_path": "",
        "intensifies_path": "",
        "reverse_intensifies_path": "",
        "intensifies_audio_path": "",
        "cartoon_path": "",
        "width": width,
        "height": height,
        "category_id": "",
        "category_name": "local",
        "material_id": "",
        "material_name": p.name,
        "material_url": "",
        "crop": {
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
        },
        "crop_ratio": "free",
        "audio_fade": None,
        "crop_scale": 1.0,
        "extra_type_option": 0,
        "stable": {"stable_level": 0, "matrix_path": "", "time_range": {"start": 0, "duration": 0}},
        "matting": {
            "flag": 0, "path": "", "interactiveTime": [], "has_use_quick_brush": False,
            "strokes": [], "has_use_quick_eraser": False, "expansion": 0, "feather": 0,
            "reverse": False, "custom_matting_id": "", "enable_matting_stroke": False,
            "is_clould": False, "mask_video_path": "", "cloud_product_fps": 0.0,
        },
        "source": 0, "source_platform": 0, "formula_id": "",
        "check_flag": 62978047,
        "video_algorithm": {
            "algorithms": [], "time_range": None, "path": "", "gameplay_configs": [],
            "ai_in_painting_config": [], "complement_frame_config": None,
            "motion_blur_config": None, "deflicker": None, "noise_reduction": None,
            "quality_enhance": None, "super_resolution": None, "ai_background_configs": [],
            "smart_complement_frame": None, "aigc_generate": None, "aigc_generate_list": [],
            "mouth_shape_driver": None, "ai_expression_driven": None,
            "ai_motion_driven": None, "image_interpretation": None,
            "story_video_modify_video_config": {
                "task_id": "", "is_overwrite_last_video": False,
                "tracker_task_id": "", "generate_id": "", "generate_card_id": "",
            },
            "skip_algorithm_index": [],
        },
        "is_unified_beauty_mode": False,
        "is_set_beauty_mode": False,
        "object_locked": None,
        "smart_motion": None,
        "multi_camera_info": None,
        "freeze": None,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "team_id": "",
        "local_material_id": str(uuid.uuid4()),
        "origin_material_id": "",
        "request_id": "",
        "has_sound_separated": False,
        "is_text_edit_overdub": False,
        "is_ai_generate_content": False,
        "aigc_type": "none",
        "is_copyright": False,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "local_material_from": "",
        "smart_match_info": None,
        "beauty_face_preset_infos": [],
        "beauty_body_preset_id": "",
        "beauty_face_auto_preset": {"preset_id": "", "name": "", "rate_map": "", "scene": ""},
        "beauty_face_auto_preset_infos": [],
        "beauty_body_auto_preset": None,
        "live_photo_timestamp": -1,
        "live_photo_cover_path": "",
        "content_feature_info": None,
        "corner_pin": None,
        "surface_trackings": [],
        "video_mask_stroke": {
            "resource_id": "", "path": "", "type": "", "color": "",
            "size": 0.0, "alpha": 0.0, "distance": 0.0, "texture": 0.0,
            "horizontal_shift": 0.0, "vertical_shift": 0.0,
        },
        "video_mask_shadow": {
            "resource_id": "", "path": "", "color": "",
            "alpha": 0.0, "blur": 0.0, "distance": 0.0, "angle": 0.0,
        },
    }, mid


def _speed_material() -> tuple[dict, str]:
    sid = _uid()
    return {"id": sid, "type": "speed", "mode": 0, "speed": 1.0, "curve_speed": None}, sid


def _canvas_material() -> tuple[dict, str]:
    cid = _uid()
    return {
        "id": cid, "type": "canvas_color", "color": "", "blur": 0.0,
        "image": "", "album_image": "", "image_id": "", "image_name": "",
        "source_platform": 0, "team_id": "",
    }, cid


def _loudness_material() -> tuple[dict, str]:
    lid = _uid()
    return {
        "id": lid, "enable": False, "time_range": None, "file_id": "",
        "target_loudness": 0.0, "loudness_param": None,
    }, lid


def _vocal_sep_material() -> tuple[dict, str]:
    vid = _uid()
    return {
        "id": vid, "type": "vocal_separation", "choice": 0, "removed_sounds": [],
        "time_range": None, "production_path": "", "final_algorithm": "", "enter_from": "",
    }, vid


def _sound_channel_material() -> tuple[dict, str]:
    sid = _uid()
    return {
        "id": sid, "type": "none", "audio_channel_mapping": 0, "is_config_open": False,
    }, sid


def _placeholder_info_material() -> tuple[dict, str]:
    pid = _uid()
    return {
        "id": pid, "type": "placeholder_info", "meta_type": "none",
        "res_path": "", "res_text": "", "error_path": "", "error_text": "",
    }, pid


def _video_segment(
    mat_id: str,
    speed_id: str,
    canvas_id: str,
    loudness_id: str,
    vocal_id: str,
    sound_id: str,
    placeholder_id: str,
    source_start: float,
    source_dur: float,
    target_start: float,
    target_dur: float,
    render_index: int = 0,
    clip_scale: float = 1.0,
    transform_x: float = 0.0,
) -> dict:
    return {
        "id": _uid(),
        "source_timerange": {"start": _us(source_start), "duration": _us(source_dur)},
        "target_timerange": {"start": _us(target_start), "duration": _us(target_dur)},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "clip": {
            "scale": {"x": clip_scale, "y": clip_scale},
            "rotation": 0.0,
            "transform": {"x": transform_x, "y": 0.0},
            "flip": {"vertical": False, "horizontal": False},
            "alpha": 1.0,
        },
        "uniform_scale": {"on": True, "value": clip_scale},
        "material_id": mat_id,
        "extra_material_refs": [speed_id, canvas_id, loudness_id, vocal_id, sound_id, placeholder_id],
        "render_index": render_index,
        "keyframe_refs": [],
        "enable_lut": True,
        "enable_adjust": True,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": render_index,
        "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False, "target_follow": "", "size_layout": 0,
            "horizontal_pos_layout": 0, "vertical_pos_layout": 0,
        },
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }


def _text_material(text: str, font_path: str) -> tuple[dict, str]:
    tid = _uid()
    content = json.dumps({
        "text": text,
        "styles": [{
            "fill": {"content": {"render_type": "solid", "solid": {"color": [1, 1, 1]}}},
            "font": {"path": font_path, "id": ""},
            "size": 15,
            "range": [0, len(text)],
        }],
    }, ensure_ascii=False)
    return {
        "recognize_task_id": "",
        "id": tid,
        "name": "",
        "recognize_text": "",
        "recognize_model": "",
        "punc_model": "",
        "type": "text",
        "content": content,
        "base_content": "",
        "words": {"start_time": [], "end_time": [], "text": []},
        "current_words": {"start_time": [], "end_time": [], "text": []},
        "global_alpha": 1.0,
        "combo_info": {"text_templates": []},
        "caption_template_info": {
            "resource_id": "", "third_resource_id": "", "resource_name": "",
            "category_id": "", "category_name": "", "effect_id": "",
            "request_id": "", "path": "", "is_new": False, "source_platform": 0,
        },
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "text_curve": None,
        "text_loop_on_path": False,
        "offset_on_path": 0.0,
        "enable_path_typesetting": False,
        "text_exceeds_path_process_type": 0,
        "text_typesetting_paths": None,
        "text_typesetting_paths_file": "",
        "text_typesetting_path_index": 0,
        "line_spacing": 0.02,
        "has_shadow": False,
        "shadow_color": "",
        "shadow_alpha": 0.9,
        "shadow_smoothing": 0.45,
        "shadow_distance": 5.0,
        "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
        "shadow_angle": -45.0,
        "shadow_thickness_projection_enable": False,
        "shadow_thickness_projection_angle": 0.0,
        "shadow_thickness_projection_distance": 0.0,
        "border_alpha": 1.0,
        "border_color": "",
        "border_width": 0.08,
        "border_mode": 0,
        "style_name": "",
        "text_color": "#FFFFFF",
        "text_alpha": 1.0,
        "font_name": "",
        "font_title": "none",
        "font_size": 15.0,
        "font_path": font_path,
        "font_id": "",
        "font_resource_id": "",
        "initial_scale": 1.0,
        "font_url": "",
        "typesetting": 0,
        "alignment": 1,
        "line_feed": 1,
        "use_effect_default_color": True,
        "is_rich_text": False,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "ktv_color": "",
        "text_to_audio_ids": [],
        "bold_width": 0.0,
        "italic_degree": 0,
        "underline": False,
        "underline_width": 0.05,
        "underline_offset": 0.22,
        "sub_type": 0,
        "check_flag": 7,
        "text_size": 30,
        "font_category_name": "",
        "font_source_platform": 0,
        "font_third_resource_id": "",
        "font_category_id": "",
        "add_type": 0,
        "operation_type": 0,
        "recognize_type": 0,
        "fonts": [],
        "background_color": "",
        "background_alpha": 1.0,
        "background_style": 0,
        "background_round_radius": 0.0,
        "background_width": 0.14,
        "background_height": 0.14,
        "background_vertical_offset": 0.0,
        "background_horizontal_offset": 0.0,
        "background_fill": "",
        "single_char_bg_enable": False,
        "single_char_bg_color": "",
        "single_char_bg_alpha": 1.0,
        "single_char_bg_round_radius": 0.3,
        "single_char_bg_width": 0.0,
        "single_char_bg_height": 0.0,
        "single_char_bg_vertical_offset": 0.0,
        "single_char_bg_horizontal_offset": 0.0,
        "font_team_id": "",
        "tts_auto_update": False,
        "text_preset_resource_id": "",
        "group_id": "",
        "preset_id": "",
        "preset_name": "",
        "preset_category": "",
        "preset_category_id": "",
        "preset_index": 0,
        "preset_has_set_alignment": False,
        "force_apply_line_max_width": False,
        "language": "",
        "relevance_segment": [],
        "original_size": [],
        "fixed_width": -1.0,
        "fixed_height": -1.0,
        "line_max_width": 0.82,
        "oneline_cutoff": False,
        "cutoff_postfix": "",
        "subtitle_template_original_fontsize": 0.0,
        "subtitle_keywords": None,
        "inner_padding": -1.0,
        "multi_language_current": "none",
        "source_from": "",
        "is_lyric_effect": False,
        "lyric_group_id": "",
        "lyrics_template": {
            "resource_id": "", "resource_name": "", "panel": "", "effect_id": "",
            "path": "", "category_id": "", "category_name": "", "request_id": "",
        },
        "is_batch_replace": False,
        "is_words_linear": False,
        "ssml_content": "",
        "subtitle_keywords_config": None,
        "sub_template_id": -1,
        "translate_original_text": "",
    }, tid


def _text_segment(mat_id: str, target_start: float, target_dur: float, render_idx: int = 14001) -> dict:
    return {
        "id": _uid(),
        "source_timerange": None,
        "target_timerange": {"start": _us(target_start), "duration": _us(target_dur)},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "clip": {
            "scale": {"x": 1.0, "y": 1.0},
            "rotation": 0.0,
            "transform": {"x": 0.0, "y": 0.0},
            "flip": {"vertical": False, "horizontal": False},
            "alpha": 1.0,
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "material_id": mat_id,
        "extra_material_refs": [],
        "render_index": render_idx,
        "keyframe_refs": [],
        "enable_lut": False,
        "enable_adjust": False,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": 1,
        "hdr_settings": None,
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False, "target_follow": "", "size_layout": 0,
            "horizontal_pos_layout": 0, "vertical_pos_layout": 0,
        },
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }


def build_draft(
    video_path: str,
    keep_ranges: list[tuple[float, float]],
    total_duration: float,
    draft_name: str,
    subtitles: list[dict] | None = None,
    width: int = 1080,
    height: int = 1920,
    vertical: bool = False,
    seg_offsets: list[float] | None = None,
) -> Path:
    """
    Build a CapCut draft from keep_ranges.
    subtitles: [{"text": str, "start": float, "end": float}, ...]
                (times relative to original video)
    vertical:  if True, output a 9:16 (1080x1920) canvas but KEEP the source's
               original aspect ratio (contain-fit, centered). The video sits in
               the middle with empty space top/bottom — intended for a vertical
               template (fixed captions etc.). No cropping, no zoom.
    Returns the draft folder path.
    """
    draft_id = _uid()
    draft_dir = DRAFT_ROOT / draft_name
    draft_dir.mkdir(parents=True, exist_ok=True)

    if not keep_ranges:
        keep_ranges = [(0.0, total_duration)]

    # ── Canvas for 9:16 vertical output (original ratio preserved) ──
    src_w, src_h = width, height
    if vertical:
        # 9:16 canvas; CapCut contain-fits the clip (scale 1.0) so the original
        # aspect ratio is preserved and centered, leaving top/bottom space.
        canvas_w, canvas_h = 1080, 1920
        clip_scale = 1.0
    else:
        canvas_w, canvas_h = src_w, src_h
        clip_scale = 1.0

    # Materials
    video_mat, vid_mat_id = _video_material(video_path, total_duration, src_w, src_h)
    speeds, speed_ids = zip(*[_speed_material() for _ in keep_ranges])
    canvases, canvas_ids = zip(*[_canvas_material() for _ in keep_ranges])
    loudnesses, loudness_ids = zip(*[_loudness_material() for _ in keep_ranges])
    vocals, vocal_ids = zip(*[_vocal_sep_material() for _ in keep_ranges])
    sounds, sound_ids = zip(*[_sound_channel_material() for _ in keep_ranges])
    placeholders, placeholder_ids = zip(*[_placeholder_info_material() for _ in keep_ranges])

    # Video segments
    video_segments = []
    cursor = 0.0
    for i, (src_start, src_end) in enumerate(keep_ranges):
        src_dur = src_end - src_start
        tx = seg_offsets[i] if (seg_offsets and i < len(seg_offsets)) else 0.0
        seg = _video_segment(
            vid_mat_id, speed_ids[i], canvas_ids[i],
            loudness_ids[i], vocal_ids[i], sound_ids[i], placeholder_ids[i],
            src_start, src_dur, cursor, src_dur,
            render_index=i, clip_scale=clip_scale, transform_x=tx,
        )
        video_segments.append(seg)
        cursor += src_dur

    total_edit_duration = cursor

    # Text/subtitle segments
    text_segments = []
    text_mats = []

    font_path_str = _find_font()

    if subtitles:
        # Map original-time subtitles to edit-timeline times
        def original_to_edit(orig_t: float) -> float | None:
            edit_cursor = 0.0
            for src_start, src_end in keep_ranges:
                dur = src_end - src_start
                if src_start <= orig_t <= src_end:
                    return edit_cursor + (orig_t - src_start)
                edit_cursor += dur
            return None

        for sub in subtitles:
            edit_start = original_to_edit(sub["start"])
            edit_end = original_to_edit(sub["end"])
            if edit_start is None or edit_end is None:
                continue
            edit_dur = edit_end - edit_start
            if edit_dur < 0.05:
                continue
            mat, mat_id = _text_material(sub["text"], font_path_str)
            text_mats.append(mat)
            text_segments.append(_text_segment(mat_id, edit_start, edit_dur))

    # Build tracks
    tracks = [
        {
            "id": _uid(),
            "type": "video",
            "segments": video_segments,
            "flag": 0,
            "attribute": 0,
            "name": "",
            "is_default_name": True,
        }
    ]
    if text_segments:
        tracks.append({
            "id": _uid(),
            "type": "text",
            "segments": text_segments,
            "flag": 0,
            "attribute": 0,
            "name": "",
            "is_default_name": True,
        })

    content = {
        "id": draft_id,
        "version": 360000,
        "new_version": "175.0.0",
        "name": "",
        "duration": _us(total_edit_duration),
        "create_time": 0,
        "update_time": 0,
        "fps": 30.0,
        "is_drop_frame_timecode": False,
        "color_space": -1,
        "config": {
            "video_mute": False,
            "record_audio_last_index": 1,
            "extract_audio_last_index": 1,
            "original_sound_last_index": 1,
            "subtitle_recognition_id": "",
            "subtitle_taskinfo": [],
            "lyrics_recognition_id": "",
            "lyrics_taskinfo": [],
            "subtitle_sync": True,
            "lyrics_sync": True,
            "voice_change_sync": False,
            "sticker_max_index": 1,
            "adjust_max_index": 1,
            "material_save_mode": 0,
            "export_range": None,
            "maintrack_adsorb": True,
            "combination_max_index": 1,
            "attachment_info": [],
            "zoom_info_params": None,
            "system_font_list": [],
            "multi_language_mode": "none",
            "multi_language_main": "none",
            "multi_language_current": "none",
            "multi_language_list": [],
            "subtitle_keywords_config": None,
            "use_float_render": False,
        },
        "canvas_config": {
            "ratio": "original",
            "width": canvas_w,
            "height": canvas_h,
            "background": None,
        },
        "tracks": tracks,
        "group_container": None,
        "materials": {
            "flowers": [],
            "videos": [video_mat],
            "tail_leaders": [],
            "audios": [],
            "images": [],
            "texts": text_mats,
            "effects": [],
            "stickers": [],
            "canvases": list(canvases),
            "transitions": [],
            "audio_effects": [],
            "audio_fades": [],
            "beats": [],
            "material_animations": [],
            "placeholders": [],
            "placeholder_infos": list(placeholders),
            "speeds": list(speeds),
            "common_mask": [],
            "chromas": [],
            "text_templates": [],
            "realtime_denoises": [],
            "audio_pannings": [],
            "audio_pitch_shifts": [],
            "video_trackings": [],
            "hsl": [],
            "drafts": [],
            "color_curves": [],
            "hsl_curves": [],
            "primary_color_wheels": [],
            "log_color_wheels": [],
            "video_effects": [],
            "ai_text_effects": [],
            "audio_balances": [],
            "handwrites": [],
            "manual_deformations": [],
            "manual_beautys": [],
            "plugin_effects": [],
            "sound_channel_mappings": list(sounds),
            "green_screens": [],
            "shapes": [],
            "material_colors": [],
            "digital_humans": [],
            "digital_human_model_dressing": [],
            "smart_crops": [],
            "ai_translates": [],
            "audio_track_indexes": [],
            "loudnesses": list(loudnesses),
            "vocal_beautifys": [],
            "vocal_separations": list(vocals),
            "smart_relights": [],
            "time_marks": [],
            "multi_language_refs": [],
            "video_shadows": [],
            "video_strokes": [],
            "video_radius": [],
        },
        "keyframes": {
            "videos": [], "audios": [], "texts": [], "stickers": [],
            "filters": [], "adjusts": [], "handwrites": [], "effects": [],
        },
        "keyframe_graph_list": [],
        "platform": PLATFORM,
        "last_modified_platform": PLATFORM,
        "mutable_config": None,
        "cover": None,
        "retouch_cover": None,
        "extra_info": None,
        "relationships": [],
        "mixed_track_mode_on": False,
        "render_index_track_mode_on": True,
        "free_render_index_mode_on": False,
        "static_cover_image_path": "",
        "source": "default",
        "time_marks": None,
        "path": "",
        "lyrics_effects": [],
        "uneven_animation_template_info": {
            "composition": "", "content": "", "order": "", "sub_template_info_list": [],
        },
        "draft_type": "video",
        "smart_ads_info": {"page_from": "", "routine": "", "draft_url": ""},
        "function_assistant_info": {
            "smart_rec_applied": False, "fixed_rec_applied": False,
            "auto_adjust": False, "auto_adjust_segid_list": [],
            "color_correction": False, "color_correction_segid_list": [],
            "enhance_quality": False, "smooth_slow_motion": False,
            "deflicker_segid_list": [], "video_noise_segid_list": [],
            "enhance_quality_segid_list": [], "smart_segid_list": [],
            "retouch": False, "retouch_segid_list": [],
            "enhande_voice": False, "enhance_voice_segid_list": [],
            "audio_noise_segid_list": [], "auto_caption": False,
            "auto_caption_segid_list": [], "auto_caption_template_id": "",
            "caption_opt": False, "caption_opt_segid_list": [],
            "eye_correction": False, "eye_correction_segid_list": [],
            "normalize_loudness": False, "normalize_loudness_segid_list": [],
            "normalize_loudness_audio_denoise_segid_list": [],
            "auto_adjust_fixed": False, "auto_adjust_fixed_value": 50.0,
            "color_correction_fixed": False, "color_correction_fixed_value": 50.0,
            "normalize_loudness_fixed": False, "enhande_voice_fixed": False,
            "retouch_fixed": False, "enhance_quality_fixed": False,
            "smooth_slow_motion_fixed": False,
            "fps": {"num": 0, "den": 1},
        },
    }

    now_ms = int(time.time() * 1000)
    meta = {
        "draft_id": draft_id,
        "draft_name": draft_name,
        "draft_removable_storage_device": "",
        "draft_timeline_materials_size_": 0,
        "draft_cloud_last_action_download": False,
        "tm_draft_create": now_ms,
        "tm_draft_modified": now_ms,
        "tm_duration": _us(total_edit_duration),
        "draft_root_path": str(draft_dir).replace("\\", "/"),
        "draft_materials": [
            {
                "type": 0,
                "value": [str(Path(video_path)).replace("\\", "/")],
            }
        ],
        "draft_fold_path": str(DRAFT_ROOT).replace("\\", "/"),
        "draft_timeline_materials_size": 0,
        "draft_is_ai_packaging": False,
        "draft_is_article": False,
        "draft_business_info": {"draft_id": draft_id, "draft_name": draft_name},
    }

    (draft_dir / "draft_content.json").write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (draft_dir / "draft_meta_info.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # CapCut needs .locked to exist
    (draft_dir / ".locked").touch()

    return draft_dir
