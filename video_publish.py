import sys
import json
import csv
import logging
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from shutil import which

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def load_config():
    data = json.load(open(CONFIG_FILE, encoding="utf-8"))
    return data["video_publish"]

def parse_input():
    input_path = Path(sys.argv[1])

    if input_path.suffix == ".csv":
        jobs = []
        with open(input_path, encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or len(row) < 2:
                    continue

                if row[0].strip().startswith("#"):
                    continue

                jobs.append({
                    "input": row[0],
                    "output": row[1]
                })

        return jobs

    return [{
        "input": sys.argv[1],
        "output": sys.argv[2]
    }]

def get_ffprobe(ffmpeg):
    return which("ffprobe") or ffmpeg.replace("ffmpeg", "ffprobe")

def get_orientation(ffmpeg, input_path):
    ffprobe = get_ffprobe(ffmpeg)

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                str(input_path)
            ],
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)
        stream = data["streams"][0]

        w, h = stream["width"], stream["height"]

        return "vertical" if h > w else "horizontal"

    except Exception:
        logging.warning("Orientation fallback → horizontal")
        return "horizontal"

def parse_bitrate(b):
    b = str(b).lower()
    if "k" in b:
        return int(float(b.replace("k", "")))
    if "m" in b:
        return int(float(b.replace("m", "")) * 1000)
    return int(b)

def build_cmd(ffmpeg, input, output, preset):
    vcfg = preset.get("video", {})
    acfg = preset.get("audio", {})

    cmd = [ffmpeg, "-y", "-i", input]

    if vcfg.get("width") and vcfg.get("height"):
        cmd += [
            "-vf",
            f"scale={vcfg['width']}:{vcfg['height']}:force_original_aspect_ratio=decrease,"
            f"pad={vcfg['width']}:{vcfg['height']}:(ow-iw)/2:(oh-ih)/2"
        ]

    if vcfg.get("fps"):
        cmd += ["-r", str(vcfg["fps"])]

    cmd += ["-c:v", vcfg.get("codec", "libx264")]

    if vcfg.get("bitrate"):
        br = parse_bitrate(vcfg["bitrate"])
        cmd += [
            "-b:v", vcfg["bitrate"],
            "-maxrate", vcfg["bitrate"],
            "-bufsize", f"{br * 2}k"
        ]

    if vcfg.get("preset"):
        cmd += ["-preset", vcfg["preset"]]

    if vcfg.get("profile"):
        cmd += ["-profile:v", vcfg["profile"]]

    if vcfg.get("pix_fmt"):
        cmd += ["-pix_fmt", vcfg["pix_fmt"]]

    if vcfg.get("gop"):
        cmd += ["-g", str(vcfg["gop"])]

    if vcfg.get("bf"):
        cmd += ["-bf", str(vcfg["bf"])]

    cmd += [
        "-c:a", acfg.get("codec", "aac"),
        "-b:a", acfg.get("bitrate", "192k")
    ]

    cmd += ["-movflags", "+faststart"]

    cmd += [output]

    return cmd

def process_job(job, cfg):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    orientation = get_orientation(ffmpeg, job["input"])

    for preset in cfg["presets"]:
        if not preset.get("enabled", True):
            continue

        ptype = preset.get("type", "both")

        if ptype not in ("both", orientation):
            continue

        output_dir = BASE_DIR / cfg["paths"]["output"]
        output_dir.mkdir(parents=True, exist_ok=True)

        out = output_dir / f"{job['output']}{preset['tag']}.mp4"

        for attempt in range(cfg["queue"]["max_retries"] + 1):
            try:
                cmd = build_cmd(ffmpeg, job["input"], str(out), preset)

                logging.info(" ".join(cmd))

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logging.error(result.stderr)
                    raise RuntimeError()

                break

            except Exception:
                logging.warning(f"Retry {attempt + 1} falhou → tentando novamente...")
                time.sleep(cfg["queue"]["retry_delay"])

def run_queue(jobs, cfg):
    with ThreadPoolExecutor(max_workers=cfg["queue"]["max_workers"]) as ex:
        futures = [ex.submit(process_job, j, cfg) for j in jobs]
        for f in as_completed(futures):
            f.result()

def main():
    cfg = load_config()
    jobs = parse_input()
    run_queue(jobs, cfg)

if __name__ == "__main__":
    main()