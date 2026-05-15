import json
import logging
import traceback
from pathlib import Path

from moviepy import VideoFileClip, CompositeVideoClip, TextClip

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
TASKS_FILE = BASE_DIR / "tasks.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def load_config():
    return json.load(open(CONFIG_FILE, encoding="utf-8"))["video_caption"]

def load_tasks():
    if not TASKS_FILE.exists():
        logging.warning("tasks.json não encontrado")
        return []

    tasks = json.load(open(TASKS_FILE, encoding="utf-8"))
    logging.info(f"{len(tasks)} task(s) carregada(s)")
    return tasks

def resolve_font(font_name):
    path = BASE_DIR / font_name

    if path.exists():
        return str(path)

    raise FileNotFoundError(f"Fonte não encontrada: {font_name}")

def split_text(text):
    words = text.split()

    if len(words) <= 3:
        return text

    mid = len(words) // 2
    return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])

def build_text_clip(text, style, video_size, color):
    font = resolve_font(style["font"])

    return TextClip(
        text=text,
        font=font,
        font_size=style.get("font_size", 60),
        color=color,
        method="caption",
        size=(int(video_size[0] * 0.8), None),
        interline=style.get("interline", 0),
    )

def process_task(task, cfg):
    input_path = Path(task["input"])

    if not input_path.exists():
        logging.warning(f"Arquivo não encontrado: {input_path}")
        return

    output_dir = BASE_DIR / cfg["paths"]["output"]
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / task["output"]

    logging.info(f"Processing: {input_path.name}")

    clip = VideoFileClip(str(input_path))

    text = split_text(task.get("text", ""))
    style = cfg["text_style"]

    layers = [clip]

    base = build_text_clip(
        text,
        style,
        clip.size,
        style.get("color_default", "white")
    ).with_duration(clip.duration).with_position(("center", "bottom"))

    if style.get("show_shadow"):
        shadow = build_text_clip(
            text,
            style,
            clip.size,
            "black"
        ).with_duration(clip.duration)

        shadow = shadow.with_position((
            style.get("shadow_offset_x", 5),
            style.get("shadow_offset_y", 5)
        ))

        layers.append(shadow)

    if style.get("show_stroke"):
        sw = style.get("stroke_width", 2)

        for dx in [-sw, sw]:
            for dy in [-sw, sw]:
                stroke = build_text_clip(
                    text,
                    style,
                    clip.size,
                    "black"
                ).with_duration(clip.duration)

                stroke = stroke.with_position((dx, dy))
                layers.append(stroke)

    layers.append(base)

    highlight_word = task.get("highlight")

    if highlight_word and highlight_word in text:
        highlight = build_text_clip(
            highlight_word,
            style,
            clip.size,
            style.get("color_highlight_word", "yellow")
        ).with_duration(clip.duration).with_position(("center", "bottom"))

        layers.append(highlight)

    final = CompositeVideoClip(layers)

    try:
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=24
        )

        logging.info(f"Gerado: {output_path.name}")

    except Exception as e:
        logging.error(f"Erro ao renderizar: {e}")
        traceback.print_exc()

    finally:
        clip.close()
        final.close()

def main():
    logging.info("Iniciando video_caption...")

    cfg = load_config()
    tasks = load_tasks()

    if not tasks:
        logging.warning("Nenhuma task encontrada")
        return

    for task in tasks:
        try:
            process_task(task, cfg)
        except Exception as e:
            logging.error(f"Erro geral: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()