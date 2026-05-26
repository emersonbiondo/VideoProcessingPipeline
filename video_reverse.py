import sys
import json
import math
import shutil
import logging
import tempfile
import subprocess

from pathlib import Path

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

CODEC_MAP = {
    "h264": "libx264",
    "hevc": "libx265",
    "h265": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1"
}


def load_config():
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    return cfg["video_reverse"]


def load_tasks(path):
    return json.load(open(path, encoding="utf-8"))


def run_ffmpeg(cmd):
    logging.info(" ".join(map(str, cmd)))

    subprocess.run(
        list(map(str, cmd)),
        check=True
    )


def get_media_duration(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(result.stdout.strip())


def get_video_fps(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    raw = result.stdout.strip()

    if "/" in raw:
        num, den = raw.split("/")
        return float(num) / float(den)

    return float(raw)


def get_video_metadata(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=codec_name,bit_rate,pix_fmt",
            "-of", "json",
            str(file)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)

    stream = data["streams"][0]

    codec_name = stream.get("codec_name", "h264")

    codec = CODEC_MAP.get(codec_name, "libx264")

    return {
        "codec": codec,
        "bitrate": stream.get("bit_rate"),
        "pix_fmt": stream.get("pix_fmt", "yuv420p"),
        "fps": get_video_fps(file)
    }


def build_output_path(input_file, mode, output_name, cfg):
    output_dir = BASE_DIR / cfg["paths"]["output"]

    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name:
        return output_dir / output_name

    suffix = "_reverse" if mode == "reverse" else "_loop"

    return output_dir / f"{input_file.stem}{suffix}.mp4"


def reverse_video(input_file, output_file, metadata):
    logging.info(f"Creating reverse: {output_file.name}")

    cmd = [
        FFMPEG,
        "-y",
        "-i", input_file,

        "-vf", "reverse",

        "-an",

        "-c:v", metadata["codec"],
        "-pix_fmt", metadata["pix_fmt"],

        str(output_file)
    ]

    bitrate = metadata.get("bitrate")

    if bitrate:
        cmd.extend([
            "-b:v", str(bitrate)
        ])

    run_ffmpeg(cmd)


def remove_first_frame(input_file, output_file, metadata):
    cmd = [
        FFMPEG,
        "-y",
        "-i", input_file,

        "-vf", "select='not(eq(n,0))'",

        "-an",

        "-vsync", "vfr",

        "-c:v", metadata["codec"],
        "-pix_fmt", metadata["pix_fmt"],

        str(output_file)
    ]

    bitrate = metadata.get("bitrate")

    if bitrate:
        cmd.extend([
            "-b:v", str(bitrate)
        ])

    run_ffmpeg(cmd)


def concat_videos(files, output_file, metadata):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8"
    ) as f:

        for file in files:
            f.write(f"file '{Path(file).resolve()}'\n")

        list_file = Path(f.name)

    cmd = [
        FFMPEG,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,

        "-an",

        "-c:v", metadata["codec"],
        "-pix_fmt", metadata["pix_fmt"],

        str(output_file)
    ]

    bitrate = metadata.get("bitrate")

    if bitrate:
        cmd.extend([
            "-b:v", str(bitrate)
        ])

    run_ffmpeg(cmd)

    list_file.unlink(missing_ok=True)


def trim_video(input_file, output_file, duration, metadata):
    cmd = [
        FFMPEG,
        "-y",
        "-i", input_file,

        "-t", str(duration),

        "-an",

        "-c:v", metadata["codec"],
        "-pix_fmt", metadata["pix_fmt"],

        str(output_file)
    ]

    bitrate = metadata.get("bitrate")

    if bitrate:
        cmd.extend([
            "-b:v", str(bitrate)
        ])

    run_ffmpeg(cmd)


def create_loop(input_file, output_file, cfg, autocomplete=None):
    metadata = get_video_metadata(input_file)

    fps = metadata["fps"]

    remove_duplicate = cfg["loop"]["remove_duplicate_frame"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        reverse_file = tmp / "reverse.mp4"

        reverse_video(
            input_file=input_file,
            output_file=reverse_file,
            metadata=metadata
        )

        reverse_for_loop = reverse_file

        if remove_duplicate:
            reverse_trimmed = tmp / "reverse_trimmed.mp4"

            remove_first_frame(
                input_file=reverse_file,
                output_file=reverse_trimmed,
                metadata=metadata
            )

            reverse_for_loop = reverse_trimmed

        base_loop = tmp / "base_loop.mp4"

        concat_videos(
            [
                input_file,
                reverse_for_loop
            ],
            base_loop,
            metadata
        )

        if not autocomplete:
            shutil.copy2(base_loop, output_file)
            return

        target_duration = get_media_duration(autocomplete)

        base_duration = get_media_duration(base_loop)

        loops_needed = math.ceil(target_duration / base_duration)

        loop_files = []

        for i in range(loops_needed):
            if i == 0:
                loop_files.append(base_loop)
                continue

            if remove_duplicate:
                trimmed_loop = tmp / f"loop_trimmed_{i}.mp4"

                remove_first_frame(
                    input_file=base_loop,
                    output_file=trimmed_loop,
                    metadata=metadata
                )

                loop_files.append(trimmed_loop)

            else:
                loop_files.append(base_loop)

        expanded_loop = tmp / "expanded_loop.mp4"

        concat_videos(
            loop_files,
            expanded_loop,
            metadata
        )

        final_frames = math.ceil(target_duration * fps)

        final_duration = final_frames / fps

        trim_video(
            input_file=expanded_loop,
            output_file=output_file,
            duration=final_duration,
            metadata=metadata
        )


def validate_task(task):
    required = [
        "input",
        "mode"
    ]

    for field in required:
        if field not in task:
            raise ValueError(f"Missing field: {field}")

    if task["mode"] not in ["reverse", "loop"]:
        raise ValueError(f"Invalid mode: {task['mode']}")


def process_task(task, cfg):
    validate_task(task)

    input_file = Path(task["input"])

    if not input_file.exists():
        raise FileNotFoundError(f"Input not found: {input_file}")

    mode = task["mode"]

    autocomplete = task.get("autocomplete") or ""

    autocomplete = str(autocomplete).strip()

    if autocomplete:
        autocomplete = Path(autocomplete)

        if not autocomplete.exists():
            raise FileNotFoundError(
                f"Autocomplete file not found: {autocomplete}"
            )

    output_file = build_output_path(
        input_file=input_file,
        mode=mode,
        output_name=task.get("output"),
        cfg=cfg
    )

    metadata = get_video_metadata(input_file)

    if mode == "reverse":
        reverse_video(
            input_file=input_file,
            output_file=output_file,
            metadata=metadata
        )

    elif mode == "loop":
        create_loop(
            input_file=input_file,
            output_file=output_file,
            cfg=cfg,
            autocomplete=autocomplete
        )

    logging.info(f"Saved: {output_file.name}")


def process_cli(input_file, reverse_mode, loop_mode, autocomplete, cfg):
    input_file = Path(input_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Input not found: {input_file}")

    if reverse_mode:
        mode = "reverse"
    elif loop_mode:
        mode = "loop"
    else:
        raise ValueError("Choose --reverse or --loop")

    if autocomplete:
        autocomplete = Path(autocomplete)

        if not autocomplete.exists():
            raise FileNotFoundError(
                f"Autocomplete file not found: {autocomplete}"
            )

    output_file = build_output_path(
        input_file=input_file,
        mode=mode,
        output_name=None,
        cfg=cfg
    )

    metadata = get_video_metadata(input_file)

    if mode == "reverse":
        reverse_video(
            input_file=input_file,
            output_file=output_file,
            metadata=metadata
        )

    elif mode == "loop":
        create_loop(
            input_file=input_file,
            output_file=output_file,
            cfg=cfg,
            autocomplete=autocomplete
        )

    logging.info(f"Saved: {output_file.name}")


def main():
    cfg = load_config()

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "python video_reverse.py video.mp4 --reverse\n"
            "python video_reverse.py video.mp4 --loop\n"
            "python video_reverse.py video.mp4 --loop --autocomplete audio.mp3\n"
            "python video_reverse.py tasks_reverse.json"
        )
        return

    first_arg = Path(sys.argv[1])

    if first_arg.suffix.lower() == ".json":
        tasks = load_tasks(first_arg)

        for task in tasks:
            try:
                process_task(task, cfg)
            except Exception as e:
                logging.error(f"Task failed: {e}")

        return

    reverse_mode = "--reverse" in sys.argv
    loop_mode = "--loop" in sys.argv

    autocomplete = None

    if "--autocomplete" in sys.argv:
        idx = sys.argv.index("--autocomplete")

        if idx + 1 >= len(sys.argv):
            raise ValueError("--autocomplete requires path")

        autocomplete = sys.argv[idx + 1]

    process_cli(
        input_file=first_arg,
        reverse_mode=reverse_mode,
        loop_mode=loop_mode,
        autocomplete=autocomplete,
        cfg=cfg
    )


if __name__ == "__main__":
    main()
