import sys
import json
import csv
import subprocess
import logging
from pathlib import Path

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


def load_config():
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    return cfg["video_cut"]


def time_to_seconds(t):
    parts = list(map(float, t.strip().split(":")))

    if len(parts) == 2:
        return parts[0] * 60 + parts[1]

    elif len(parts) == 3:
        return (
            parts[0] * 3600 +
            parts[1] * 60 +
            parts[2]
        )

    else:
        raise ValueError(f"Invalid time format: {t}")


def sanitize_filename(name):
    return "".join(
        c for c in name
        if c.isalnum() or c in (" ", "_", "-")
    ).strip().replace(" ", "_")


def parse_bitrate(b):
    b = b.lower().strip()

    if b.endswith("k"):
        return int(b[:-1])

    if b.endswith("m"):
        return int(b[:-1]) * 1000

    raise ValueError(f"Invalid bitrate format: {b}")


def cut_video(video_path, start, end, label, cfg, output_dir):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    start_sec = time_to_seconds(start)
    end_sec = time_to_seconds(end)

    duration = end_sec - start_sec

    if duration <= 0:
        logging.warning(
            f"Skipping invalid cut (duration <= 0): "
            f"{start} → {end}"
        )
        return

    safe_label = sanitize_filename(label)

    output_file = (
        output_dir /
        f"{video_path.stem}_{safe_label}.mp4"
    )

    logging.info(
        f"Cutting: {safe_label} "
        f"({start} → {end})"
    )

    if cfg["mode"] == "fast":
        cmd = [
            ffmpeg,
            "-y",

            "-ss", str(start_sec),
            "-i", str(video_path),

            "-t", str(duration),

            "-map", "0:v",
            "-map", "0:a?",

            "-c", "copy",

            str(output_file)
        ]

    elif cfg["mode"] == "precise":
        p = cfg["precise"]

        bitrate = p["bitrate"]

        bufsize = (
            f"{parse_bitrate(bitrate) * 2}k"
        )

        cmd = [
            ffmpeg,
            "-y",

            "-ss", str(start_sec),
            "-i", str(video_path),

            "-t", str(duration),

            "-map", "0:v",
            "-map", "0:a?",

            "-c:v", "libx265",
            "-preset", p["preset"],
            "-pix_fmt", "yuv420p10le",

            "-x265-params",
            (
                f"profile={p['profile']}:"
                f"level={p['level']}"
            ),

            "-b:v", bitrate,
            "-minrate", bitrate,
            "-maxrate", bitrate,
            "-bufsize", bufsize,

            "-c:a", p["audio_codec"],
            "-b:a", p["audio_bitrate"],

            str(output_file)
        ]

    else:
        raise ValueError(
            f"Invalid mode: {cfg['mode']}"
        )

    subprocess.run(cmd, check=True)

    logging.info(
        f"Saved: {output_file.name}"
    )


def open_csv_with_fallback(csv_file):
    encodings = [
        "utf-8",
        "utf-8-sig",
        "latin1",
        "cp1252"
    ]

    last_error = None

    for enc in encodings:
        try:
            return open(
                csv_file,
                newline="",
                encoding=enc
            )

        except UnicodeDecodeError as e:
            last_error = e

    raise last_error


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: "
            "python video_cut.py "
            "<cuts.csv> <video.mp4>"
        )
        return

    csv_file = Path(sys.argv[1])
    video_file = Path(sys.argv[2])

    if not csv_file.exists():
        raise FileNotFoundError(
            f"CSV not found: {csv_file}"
        )

    if not video_file.exists():
        raise FileNotFoundError(
            f"Video not found: {video_file}"
        )

    cfg = load_config()

    output_dir = (
        BASE_DIR /
        cfg["paths"]["output"]
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    with open_csv_with_fallback(csv_file) as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 3:
                logging.warning(
                    f"Invalid row skipped: {row}"
                )
                continue

            start, end, label = (
                row[0],
                row[1],
                row[2]
            )

            try:
                cut_video(
                    video_file,
                    start,
                    end,
                    label,
                    cfg,
                    output_dir
                )

            except Exception as e:
                logging.error(
                    f"Error processing cut "
                    f"{label}: {e}"
                )


if __name__ == "__main__":
    main()
