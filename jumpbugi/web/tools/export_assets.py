"""Export the existing Pygame's prepared frames and collision masks into web/.

Run from any directory with ``python -B web/tools/export_assets.py``. Only the
export step needs Pygame and the parent project; the resulting web game does not.
No score files are loaded and no files outside web/assets are written.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

WEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = WEB_ROOT.parent
OUTPUT = (WEB_ROOT / "assets").resolve()
if not OUTPUT.is_relative_to(WEB_ROOT):
    raise RuntimeError("Asset output must stay inside the web project")
sys.path.insert(0, str(PROJECT_ROOT))

import pygame  # noqa: E402
from desktop_prototype import assets as pygame_assets  # noqa: E402
from desktop_prototype import config  # noqa: E402


def write_surface(surface: pygame.Surface, relative: str) -> dict:
    """Write a PNG under the fixed output directory, never to a source path."""
    target = (OUTPUT / relative).resolve()
    if not target.is_relative_to(OUTPUT):
        raise ValueError(f"Unsafe asset path: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(target))
    return {
        "file": target.relative_to(WEB_ROOT).as_posix(),
        "width": surface.get_width(),
        "height": surface.get_height(),
    }


def mask_data(mask: pygame.mask.Mask) -> dict:
    width, height = mask.get_size()
    return {
        "width": width,
        "height": height,
        "rows": [
            "".join("1" if mask.get_at((x, y)) else "0" for x in range(width))
            for y in range(height)
        ],
    }


def frame_data(surface: pygame.Surface, mask: pygame.mask.Mask, relative: str) -> dict:
    if surface.get_size() != mask.get_size():
        raise ValueError(f"Frame and collision mask have different sizes: {relative}")
    info = write_surface(surface, relative)
    return {"file": info["file"], "mask": mask_data(mask)}


def source_fingerprints() -> dict[Path, str]:
    # Only executable sources and actual image inputs are inspected. In
    # particular, the score data, study materials and archived docs stay closed.
    inputs = list((PROJECT_ROOT / "desktop_prototype").glob("*.py"))
    image_names = set(config.BACKGROUND_FILES) | {
        config.START_IMAGE_FILE, "bugi.png", "bugi_run.png", "hsucat_run.png",
        "hsucat_crouch.png", "hsucat_book.png", "chicken_flap.png", "sj_run.png",
        "sj_dig.png", "sj_hole.png", config.SJ_BASE_IMAGE_FILE,
        config.HSUCAT_GIANT_IMAGE_FILE, config.HSUCAT_BOOK_IMAGE_FILE,
        config.HSUCAT_FALL_IMAGE_FILE, config.SJ_ESCAPE_IMAGE_FILE,
        *config.WAVE_IMAGE_FILES.values(),
    }
    inputs.extend(config.IMAGE_DIR / name for name in sorted(image_names))
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}


def main() -> None:
    before = source_fingerprints()
    pygame.init()
    try:
        # convert()/convert_alpha() need an initialized display, but no visible
        # desktop window is created by SDL's dummy video driver.
        pygame.display.set_mode((1, 1))
        prepared = pygame_assets.load_game_assets()
        # Keep the complete 4:3 artwork. The browser fits it into its wider
        # canvas without cropping the title or the props along the bottom.
        intro_source = config.IMAGE_DIR / config.START_IMAGE_FILE
        intro = pygame.image.load(str(intro_source))
        intro_target = OUTPUT / "intro.png"
        intro_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(intro_source, intro_target)
        manifest = {
            "version": "0.1.0",
            "backgrounds": [
                write_surface(surface, f"backgrounds/{name}")
                for name, surface in zip(config.BACKGROUND_FILES, prepared.background_stages)
            ],
            "intro": {
                "file": intro_target.relative_to(WEB_ROOT).as_posix(),
                "width": intro.get_width(),
                "height": intro.get_height(),
            },
            "player": {
                "width": prepared.player_image.get_width(),
                "height": prepared.player_image.get_height(),
                "frames": [
                    frame_data(frame, mask, f"player/{index}.png")
                    for index, (frame, mask) in enumerate(
                        zip(prepared.run_frames, prepared.player_masks)
                    )
                ],
            },
            "obstacles": {},
        }
        for name, frames in prepared.obstacle_frames.items():
            safe_name = name.removesuffix(".png")
            if not safe_name.replace("_", "").isalnum():
                raise ValueError(f"Unsafe obstacle name: {name}")
            masks = prepared.obstacle_frame_masks.get(name)
            if masks is None:
                masks = [prepared.obstacle_masks[name]] * len(frames)
            if len(frames) != len(masks):
                raise ValueError(f"Missing collision masks: {name}")
            manifest["obstacles"][name] = {
                "width": frames[0].get_width(),
                "height": frames[0].get_height(),
                "frames": [
                    frame_data(frame, mask, f"obstacles/{safe_name}/{index}.png")
                    for index, (frame, mask) in enumerate(zip(frames, masks))
                ],
            }
        manifest_path = OUTPUT / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    finally:
        pygame.quit()
    if source_fingerprints() != before:
        raise RuntimeError("Original Pygame source or image changed during export")
    png_count = len(list(OUTPUT.rglob("*.png")))
    byte_count = sum(path.stat().st_size for path in OUTPUT.rglob("*") if path.is_file())
    print(json.dumps({
        "manifest": str(manifest_path),
        "backgrounds": len(manifest["backgrounds"]),
        "obstacle_types": len(manifest["obstacles"]),
        "png_count": png_count,
        "bytes": byte_count,
        "original_sources_unchanged": True,
    }))


if __name__ == "__main__":
    main()
