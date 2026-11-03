#!/usr/bin/env python3
"""Render a Zoom work-style horoscope over one of the bundled zodiac images.

Input JSON supports either a freeform ``body`` (for example, a no-activity result)
or a ``header`` (the one-sentence sign superpower) plus ``sentences`` list. An
optional ``sign`` selects the matching image; otherwise ``background_image`` must
name one of the bundled PNG files.
"""
import argparse
import base64
import json
import re
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ASSETS_DIR = SCRIPT_DIR.parent / "assets" / "zodiac-images"
SHARE_ICONS_DIR = SCRIPT_DIR.parent / "assets" / "share-icons"
HERO_MANIFEST = SCRIPT_DIR.parents[3] / "hero-templates" / "manifest.json"
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf",
    "/Library/Fonts/Times New Roman Bold Italic.ttf",
]
FALLBACK_PATHS = [
    "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf",
    "/Library/Fonts/Georgia Bold Italic.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
# Herculanum is macOS's ancient Greek/Roman inscription-style display face —
# mysterious and hand-carved-looking but still legible, unlike a pure script font.
TITLE_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Herculanum.ttf",
    "/Library/Fonts/Herculanum.ttf",
]
TITLE_FALLBACK_PATHS = [
    "/System/Library/Fonts/Supplemental/Apple Chancery.ttf",
    "/Library/Fonts/Apple Chancery.ttf",
]
YELLOW = (247, 206, 84)
WHITE = (255, 255, 255)
LIGHT_YELLOW = (255, 241, 118)
POWERED_BY_TEXT = "Powered by Zoom AI Workflows"
TEXT_STROKE_FILL = (0, 0, 0, 255)


def footer_text(host: str) -> str:
    manifest = json.loads(HERO_MANIFEST.read_text(encoding="utf-8"))
    shortcut = next(s for s in manifest["shortcuts"] if s.get("template") == "zoom-zodiac")
    return manifest["shortcut_prefix"][host] + shortcut["suffix"]


def load_font(size: int):
    # Last resort for load_title_font when neither Herculanum nor Apple Chancery is installed.
    for filename in FONT_PATHS + FALLBACK_PATHS:
        path = Path(filename)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def load_title_font(size: int):
    """The mysterious, hand-carved, Greek-inscription-style face for the title and the footer,
    and for card text when no content face is installed."""
    for filename in TITLE_FONT_PATHS + TITLE_FALLBACK_PATHS:
        path = Path(filename)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return load_font(size)


FONT_DIRS = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts"]
# Per-language faces for the card's content text (superpower line + sentences),
# each a classic, inscriptional or calligraphic serif that suits the mystical
# look. Entries are (filename, preferred face name or None); the first one that
# exists and covers every character of the text wins. The title and footer are
# English brand text and always keep the Herculanum face above.
LANGUAGE_FONTS = {
    "zh": [("Songti.ttc", "Songti SC Regular"), ("Songti.ttc", "Songti TC Regular"), ("Songti.ttc", "STSong Regular")],
    "ja": [("ヒラギノ明朝 ProN.ttc", "Hiragino Mincho ProN W3")],
    "ko": [("AppleMyungjo.ttf", None)],
    "ru": [("Palatino.ttc", "Palatino Regular"), ("Baskerville.ttc", "Baskerville Regular"), ("Times.ttc", "Times Regular")],
    "el": [("Palatino.ttc", "Palatino Regular"), ("Baskerville.ttc", "Baskerville Regular"), ("Times.ttc", "Times Regular")],
    "th": [("Thonburi.ttc", "Thonburi Regular")],
    "ar": [("Diwan Thuluth.ttf", None)],
    "hi": [("Devanagari Sangam MN.ttc", "Devanagari Sangam MN Regular")],
    "he": [("Arial Unicode.ttf", None)],
}
# Used for Latin text (Herculanum) and as the catch-all when a language has no
# entry above or none of its faces covers the text.
DEFAULT_FONTS = [(name, None) for name in ("Herculanum.ttf", "Apple Chancery.ttf")] + [
    ("Palatino.ttc", "Palatino Regular"),
    ("Arial Unicode.ttf", None),
    ("Arial.ttf", None),
    ("DejaVuSans.ttf", None),
]
NO_SPACE_LANGUAGES = {"zh", "ja", "th"}
_SCRIPT_RANGES = [
    ("ja", [(0x3040, 0x30FF), (0x31F0, 0x31FF), (0xFF66, 0xFF9F)]),
    ("ko", [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)]),
    ("zh", [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)]),
    ("ru", [(0x0400, 0x04FF), (0x0500, 0x052F)]),
    ("el", [(0x0370, 0x03FF), (0x1F00, 0x1FFF)]),
    ("th", [(0x0E00, 0x0E7F)]),
    ("ar", [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)]),
    ("hi", [(0x0900, 0x097F)]),
    ("he", [(0x0590, 0x05FF)]),
]
_font_cache = {}
CONTENT_FONT = None  # (path, index) chosen for this card's language; None = Latin default


def detect_language(text: str) -> str:
    """Rough script-based language guess: kana implies Japanese, hangul Korean,
    Han-only Chinese; otherwise the most common non-Latin script, else 'latin'."""
    counts = {}
    for ch in text:
        cp = ord(ch)
        for lang, ranges in _SCRIPT_RANGES:
            if any(lo <= cp <= hi for lo, hi in ranges):
                counts[lang] = counts.get(lang, 0) + 1
                break
    if counts.get("ja"):
        return "ja"
    if not counts:
        return "latin"
    return max(counts, key=counts.get)


def _find_font(filename: str, face: str = None):
    for directory in FONT_DIRS:
        path = Path(directory) / filename
        if not path.exists():
            continue
        if face is None:
            return str(path), 0
        for index in range(32):
            try:
                font = ImageFont.truetype(str(path), 20, index=index)
            except OSError:
                break
            if " ".join(font.getname()) == face:
                return str(path), index
        return str(path), 0
    return None


def _covers(spec, text: str) -> bool:
    """True if the face has a real glyph for every printable character (a missing
    glyph renders as the same 'tofu' box as an unassigned codepoint)."""
    path, index = spec
    font = ImageFont.truetype(path, 24, index=index)

    def glyph(ch: str) -> bytes:
        canvas = Image.new("L", (48, 48), 0)
        ImageDraw.Draw(canvas).text((4, 4), ch, font=font, fill=255)
        return canvas.tobytes()

    missing = glyph("\U0010FFFD")
    for ch in set(text):
        if ch.isspace() or ch in "\u200b\u200c\u200d":
            continue
        if glyph(ch) == missing:
            return False
    return True


def choose_content_font(text: str):
    """Pick the (path, index) face for this card's language, falling back to the
    default list. Always returns something; the final fallback is None."""
    language = detect_language(text)
    candidates = LANGUAGE_FONTS.get(language, []) + DEFAULT_FONTS
    first_found = None
    for filename, face in candidates:
        spec = _find_font(filename, face)
        if spec is None:
            continue
        first_found = first_found or spec
        try:
            if _covers(spec, text):
                return spec
        except OSError:
            continue
    return first_found


def load_content_font(size: int):
    """Font for the superpower line and horoscope sentences, in the card's language."""
    if CONTENT_FONT is None:
        return load_title_font(size)
    key = (CONTENT_FONT, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(CONTENT_FONT[0], size, index=CONTENT_FONT[1])
    return _font_cache[key]


def content_text(data: dict) -> str:
    parts = [str(data.get("header", "")), str(data.get("body", ""))]
    for item in data.get("sentences", []):
        parts.append(item if isinstance(item, str) else str(item["text"]))
    return " ".join(parts)


def resolve_background(data: dict, assets_dir: Path) -> Path:
    files = {path.stem.casefold(): path for path in assets_dir.glob("*.webp")}
    sign = str(data.get("sign", "")).strip()
    if sign:
        path = files.get(sign.casefold())
        if path is None:
            raise ValueError(f"No bundled background matches sign {sign!r}.")
        return path
    filename = str(data.get("background_image", "")).strip()
    if not filename:
        return sorted(files.values())[0]
    if Path(filename).name != filename:
        raise ValueError("background_image must be a filename from the bundled zodiac-images folder.")
    path = assets_dir / filename
    if not path.is_file() or path.suffix.casefold() != ".webp":
        raise ValueError(f"Bundled background image not found: {filename}")
    return path


def split_sentences(text: str) -> list:
    text = " ".join(text.split()).strip()
    if not text:
        return []
    return [part for part in re.split(r"(?<=[.!?])\s+", text) if part]


def wrap_to_width(draw, text: str, font, max_width: int):
    lines, current = [], ""
    if detect_language(text) in NO_SPACE_LANGUAGES:
        # No word spaces: wrap per character, but keep closing punctuation off the
        # start of a line.
        tokens, joiner = list(text.replace("\n", "")), ""
    else:
        tokens, joiner = text.split(), " "
    for word in tokens:
        candidate = f"{current}{joiner}{word}".strip() if joiner else current + word
        if (
            not joiner and current and word in "，。！？、；：）」』】》,.!?;:)"
            and draw.textbbox((0, 0), candidate, font=font)[2] > max_width
        ):
            candidate = current + word  # let a trailing mark overhang rather than start a line
            lines.append(candidate)
            current = ""
            continue
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def measure_block(draw, text: str, font, max_width: int, gap: int):
    if not text:
        return [], [], 0
    lines = wrap_to_width(draw, text, font, max_width)
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
    height = sum(line_heights) + gap * max(0, len(lines) - 1)
    return lines, line_heights, height


def draw_block(draw, lines, line_heights, font, color, gap, cx: int, top: int, stroke_width: int):
    y = top
    for line, line_height in zip(lines, line_heights):
        box = draw.textbbox((0, 0), line, font=font)
        x = cx - (box[2] - box[0]) // 2
        draw.text(
            (x, y - box[1]), line, font=font, fill=color,
            stroke_width=stroke_width, stroke_fill=TEXT_STROKE_FILL,
        )
        y += line_height + gap
    return y - gap


def make_layout(draw, data: dict, width: int, font_size: int, footer: str):
    scale = width / 1122
    title = str(data.get("title", "Your Zoom Zodiac"))
    header = str(data.get("header", "")).strip()
    title_font = load_title_font(max(20, int(40 * scale)))
    header_font = load_content_font(max(17, int(29 * scale)))
    body_font = load_content_font(font_size)
    footer_font = load_title_font(font_size + 2)
    max_text_width = int(width * 0.68)
    line_gap = max(4, int(8 * scale))
    section_gap = max(int(font_size * 0.7), int(16 * scale))
    subtitle_gap = max(int(font_size * 0.3), int(8 * scale))
    footer_gap = 3 * (font_size + line_gap)
    # Each block is (text, font, color, line_gap, gap_before) — gap_before is the
    # vertical space inserted above this block, skipped for the first block.
    blocks = []
    blocks.append((title, title_font, YELLOW, line_gap, 0))
    if header:
        blocks.append((header, header_font, WHITE, line_gap, subtitle_gap))
    for sentence in split_sentences(str(data.get("body", ""))):
        blocks.append((sentence, body_font, WHITE, line_gap, section_gap))
    for item in data.get("sentences", []):
        if isinstance(item, str):
            sentence, highlighted = item, False
        else:
            sentence, highlighted = str(item["text"]), bool(item.get("highlight", False))
        blocks.append((sentence, body_font, LIGHT_YELLOW if highlighted else WHITE, line_gap, section_gap))
    blocks.append((footer, footer_font, LIGHT_YELLOW, line_gap, footer_gap))
    blocks.append((POWERED_BY_TEXT, footer_font, LIGHT_YELLOW, line_gap, (font_size + 2) + line_gap))
    measured = []
    total_height = 0
    for index, (text, font, color, gap, gap_before) in enumerate(blocks):
        lines, line_heights, height = measure_block(draw, text, font, max_text_width, gap)
        effective_gap_before = gap_before if index > 0 else 0
        measured.append((lines, font, color, gap, line_heights, effective_gap_before))
        total_height += effective_gap_before + height
    return measured, total_height


def render_stacked(data: dict, draw, width: int, region, stroke_width: int, footer: str):
    """Old single-column layout, used when there's no header/sentence set to
    split into the four-area grid (the no-sign, body-only result)."""
    region_width, region_height = region[2] - region[0], region[3] - region[1]
    padding = int(width * .045)
    body_room = region_height - 2 * padding

    layout = None
    for size in range(int(width * .027), max(15, int(width * .016)) - 1, -1):
        candidate = make_layout(draw, data, width, size, footer)
        if candidate[1] <= body_room:
            layout = candidate
            break
    if layout is None:
        raise ValueError("The supplied horoscope text is too long to fit legibly in this card template.")

    blocks, total_height = layout
    y = region[1] + (region_height - total_height) // 2
    cx = width // 2
    for lines, font, color, gap, line_heights, gap_before in blocks:
        y += gap_before
        y = draw_block(draw, lines, line_heights, font, color, gap, cx, y, stroke_width) + gap


def render_grid(data: dict, draw, width: int, region, stroke_width: int, footer: str):
    """Title on top, the sign's superpower line and the three horoscope
    sentences placed into four unshaded, unbordered quadrants beneath it
    (reading order: top-left, top-right, bottom-left, bottom-right), footer
    at the bottom."""
    scale = width / 1122
    region_width, region_height = region[2] - region[0], region[3] - region[1]
    line_gap = max(4, int(8 * scale))
    title_gap = max(int(28 * scale), 20)
    col_gutter = int(region_width * 0.06)
    row_gutter = int(region_width * 0.05)
    max_title_width = int(region_width * 0.9)

    title = str(data.get("title", "Your Zoom Zodiac"))
    title_font = load_title_font(max(20, int(40 * scale)))
    title_lines, title_heights, title_height = measure_block(draw, title, title_font, max_title_width, line_gap)

    header = str(data.get("header", "")).strip()
    cell_items = [(header, WHITE, True)]
    for item in data.get("sentences", [])[:3]:
        if isinstance(item, str):
            text, highlighted = item, False
        else:
            text, highlighted = str(item["text"]), bool(item.get("highlight", False))
        cell_items.append((text, LIGHT_YELLOW if highlighted else WHITE, False))
    while len(cell_items) < 4:
        cell_items.append(("", WHITE, False))

    layout = None
    for font_size in range(int(width * .027), max(14, int(width * .014)) - 1, -1):
        body_font = load_content_font(font_size)
        header_font = load_content_font(font_size + 2)
        footer_font = load_title_font(font_size + 2)
        footer_gap = 3 * (font_size + line_gap)
        col_width = (region_width - col_gutter) // 2
        cell_text_width = int(col_width * 0.88)

        measured_cells = []
        max_cell_height = 0
        for text, color, is_header in cell_items:
            font = header_font if is_header else body_font
            lines, heights, cell_height = measure_block(draw, text, font, cell_text_width, line_gap)
            measured_cells.append((lines, heights, font, color))
            max_cell_height = max(max_cell_height, cell_height)

        footer_lines, footer_heights, footer_height = measure_block(draw, footer, footer_font, max_title_width, line_gap)
        powered_lines, powered_heights, powered_height = measure_block(draw, POWERED_BY_TEXT, footer_font, max_title_width, line_gap)
        footer_line_break = (font_size + 2) + line_gap
        footer_block_height = footer_height + footer_line_break + powered_height
        row_height = max_cell_height
        grid_height = row_height * 2 + row_gutter
        total_height = title_height + title_gap + grid_height + footer_gap + footer_block_height
        if total_height <= region_height:
            layout = (measured_cells, row_height, col_width, footer_lines, footer_heights, powered_lines, powered_heights, footer_font, footer_gap, footer_line_break, total_height)
            break
    if layout is None:
        raise ValueError("The supplied horoscope text is too long to fit legibly in this card template.")
    measured_cells, row_height, col_width, footer_lines, footer_heights, powered_lines, powered_heights, footer_font, footer_gap, footer_line_break, total_height = layout

    cx = width // 2
    y = region[1] + (region_height - total_height) // 2
    y = draw_block(draw, title_lines, title_heights, title_font, YELLOW, line_gap, cx, y, stroke_width)
    y += title_gap

    grid_top = y
    col_left = [region[0], region[0] + col_width + col_gutter]
    row_top = [grid_top, grid_top + row_height + row_gutter]
    positions = [(row_top[0], col_left[0]), (row_top[0], col_left[1]), (row_top[1], col_left[0]), (row_top[1], col_left[1])]
    for (cell_top, cell_left), (lines, heights, font, color) in zip(positions, measured_cells):
        if not lines:
            continue
        cell_height = sum(heights) + line_gap * max(0, len(lines) - 1)
        cell_cx = cell_left + col_width // 2
        cell_y = cell_top + (row_height - cell_height) // 2
        draw_block(draw, lines, heights, font, color, line_gap, cell_cx, cell_y, stroke_width)

    footer_top = grid_top + row_height * 2 + row_gutter + footer_gap
    footer_bottom = draw_block(draw, footer_lines, footer_heights, footer_font, LIGHT_YELLOW, line_gap, cx, footer_top, stroke_width)
    draw_block(draw, powered_lines, powered_heights, footer_font, LIGHT_YELLOW, line_gap, cx, footer_bottom + footer_line_break, stroke_width)


def render(data: dict, output_path: Path, assets_dir: Path, footer: str):
    global CONTENT_FONT
    CONTENT_FONT = choose_content_font(content_text(data))
    source = resolve_background(data, assets_dir)
    image = Image.open(source).convert("RGBA")
    width, height = image.size
    draw = ImageDraw.Draw(image)
    # No shaded panel (per style contract): this rect is only the text layout
    # bounds, never drawn.
    region = (int(width * .10), int(height * .20), int(width * .90), int(height * .80))
    stroke_width = max(1, round(width * 0.0015))

    has_grid_content = bool(str(data.get("header", "")).strip()) and bool(data.get("sentences"))
    if has_grid_content:
        render_grid(data, draw, width, region, stroke_width, footer)
    else:
        render_stacked(data, draw, width, region, stroke_width, footer)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG")
    return source, image.size


def icon_data_uri(filename: str) -> str:
    data = (SHARE_ICONS_DIR / filename).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")


def write_share_page(image_path: Path, output_path: Path, caption: str, x_icon: str, linkedin_icon: str):
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    x_url = "https://x.com/intent/post?text=" + urllib.parse.quote(caption)
    linkedin_url = "https://www.linkedin.com/feed/?shareActive=true"
    escaped_caption = json.dumps(caption, ensure_ascii=False).replace("</", "<\\/")
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Work-Style Horoscope</title><style>body{{margin:0;padding:24px;text-align:center;background:#0c1220;color:white;font:16px system-ui}}img.card{{max-width:min(92vw,720px);max-height:72vh;object-fit:contain;border-radius:12px}}button{{border:0;border-radius:999px;padding:0;margin:12px 6px;background:none;cursor:pointer;line-height:0}}button img{{height:48px}}</style><img class="card" id="card" alt="Work-style horoscope card" src="data:image/png;base64,{encoded}"><div><button onclick="share('x')"><img src="{x_icon}" alt="Share to X"></button><button onclick="share('linkedin')"><img src="{linkedin_icon}" alt="Share on LinkedIn"></button></div><script>const caption={escaped_caption};const urls={{x:{json.dumps(x_url)},linkedin:{json.dumps(linkedin_url)}}};async function share(platform){{const image=document.getElementById('card');try{{const blob=await(await fetch(image.src)).blob();const file=new File([blob],'work-style-horoscope.png',{{type:'image/png'}});if(navigator.canShare&&navigator.canShare({{files:[file]}})){{await navigator.share({{files:[file],text:caption,title:'Work-Style Horoscope'}});return;}}}}catch(e){{}}const a=document.createElement('a');a.href=image.src;a.download='work-style-horoscope.png';a.click();if(platform==='linkedin'){{try{{await navigator.clipboard.writeText(caption);}}catch(e){{}}}}window.open(urls[platform],'_blank','noopener,noreferrer');}}</script></html>'''
    output_path.write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--assets-dir", default=str(DEFAULT_ASSETS_DIR))
    parser.add_argument("--host", default="claude", choices=("claude", "codex"), help="Host whose shortcut prompt the footer shows")
    parser.add_argument("--share-html", help="Optional path for an HTML preview with X and LinkedIn actions")
    parser.add_argument("--display", default="inline", choices=("inline", "file"),
                        help="inline: markdown image and logo badges; file: the host shows the PNG as a file card, plain-text share links")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = Path(args.output)
    source, size = render(data, output, Path(args.assets_dir), footer_text(args.host))
    print(f"Saved: {output} {size}; background: {source.name}")
    body = data.get("body", " ".join(str(s if isinstance(s, str) else s["text"]) for s in data.get("sentences", [])))
    caption = str(data.get("caption", body))
    x_url = "https://x.com/intent/post?text=" + urllib.parse.quote(caption)
    linkedin_url = "https://www.linkedin.com/feed/?shareActive=true"
    x_icon = icon_data_uri("share-to-x.svg")
    linkedin_icon = icon_data_uri("share-to-linkedin.svg")
    if args.share_html:
        write_share_page(output, Path(args.share_html), caption, x_icon, linkedin_icon)
        print(f"Share page: {args.share_html}")
    if args.display == "inline":
        resolved = str(output.resolve())
        if any(ch.isspace() for ch in resolved):
            print(f"IMAGE_MARKDOWN_UNAVAILABLE: re-render under a path without spaces: {resolved}")
        else:
            print(f"IMAGE_MARKDOWN: ![Your Zoom Zodiac]({resolved})")
    print("SHARE_MARKDOWN_START")
    if args.display == "file":
        print(f"[Share on X]({x_url}) · [Share on LinkedIn]({linkedin_url})")
    else:
        print(f"[![Share on X]({x_icon})]({x_url})")
        print(f"[![Share on LinkedIn]({linkedin_icon})]({linkedin_url})")
    print("SHARE_MARKDOWN_END")


if __name__ == "__main__":
    main()
