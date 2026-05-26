import subprocess
import json
import shutil
from pathlib import Path

import pytest
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_FILE = BASE_DIR / "config.json"

TEST_DIR = BASE_DIR / "test"

INPUT_VIDEO = TEST_DIR / "input_horizontal.mp4"
INPUT_VERTICAL = TEST_DIR / "input_vertical.mp4"
INPUT_AUDIO = TEST_DIR / "input.mp3"

TASKS_FILE = TEST_DIR / "tasks_reverse.json"

OUTPUT_DIR = BASE_DIR / "output" / "reverse"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"config.json not found at: {CONFIG_FILE}")

if not INPUT_VIDEO.exists():
    raise FileNotFoundError(f"Missing test video: {INPUT_VIDEO}")

if not INPUT_AUDIO.exists():
    raise FileNotFoundError(f"Missing test audio: {INPUT_AUDIO}")


@pytest.fixture
def clean_environment():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


def run_reverse(args, check=True):
    return subprocess.run(
        ["python", "video_reverse.py"] + args,
        capture_output=True,
        text=True,
        check=check
    )


def get_duration(file):
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


def has_audio_stream(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(file)
        ],
        capture_output=True,
        text=True
    )

    return bool(result.stdout.strip())


def get_resolution(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(file)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    width, height = result.stdout.strip().split("x")

    return int(width), int(height)


def get_fps(file):
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


def test_reverse_basic(clean_environment):
    """
    Valida:
    - reverse criado
    - duração preservada
    - sem áudio
    - resolução preservada
    - fps preservado
    """

    run_reverse([
        str(INPUT_VIDEO),
        "--reverse"
    ])

    output = OUTPUT_DIR / "input_horizontal_reverse.mp4"

    assert output.exists()

    input_duration = get_duration(INPUT_VIDEO)
    output_duration = get_duration(output)

    assert abs(input_duration - output_duration) <= 0.1

    assert not has_audio_stream(output)

    assert get_resolution(INPUT_VIDEO) == get_resolution(output)

    assert abs(get_fps(INPUT_VIDEO) - get_fps(output)) <= 0.01


def test_loop_basic(clean_environment):
    """
    Valida:
    - loop criado
    - duração aproximada dobrada
    - sem áudio
    """

    run_reverse([
        str(INPUT_VIDEO),
        "--loop"
    ])

    output = OUTPUT_DIR / "input_horizontal_loop.mp4"

    assert output.exists()

    input_duration = get_duration(INPUT_VIDEO)
    output_duration = get_duration(output)

    assert output_duration > input_duration

    assert output_duration <= (input_duration * 2)

    assert not has_audio_stream(output)


def test_remove_duplicate_frame(clean_environment):
    """
    Valida:
    - remove_duplicate_frame reduz duração do loop
    - evita frame duplicado
    """

    run_reverse([
        str(INPUT_VIDEO),
        "--loop"
    ])

    output = OUTPUT_DIR / "input_horizontal_loop.mp4"

    assert output.exists()

    input_duration = get_duration(INPUT_VIDEO)
    output_duration = get_duration(output)

    fps = get_fps(INPUT_VIDEO)

    expected_full = input_duration * 2

    frame_time = 1 / fps

    assert output_duration < expected_full

    assert abs(output_duration - (expected_full - frame_time)) <= 0.1


def test_autocomplete(clean_environment):
    """
    Valida:
    - autocomplete expande loop
    - duração nunca menor que alvo
    - sem áudio
    """

    target_duration = get_duration(INPUT_AUDIO)

    run_reverse([
        str(INPUT_VIDEO),
        "--loop",
        "--autocomplete",
        str(INPUT_AUDIO)
    ])

    output = OUTPUT_DIR / "input_horizontal_loop.mp4"

    assert output.exists()

    output_duration = get_duration(output)

    assert output_duration >= target_duration

    assert (output_duration - target_duration) <= 0.2

    assert not has_audio_stream(output)


def test_batch_processing(clean_environment):
    """
    Valida:
    - tasks_reverse.json
    - reverse
    - loop
    - autocomplete
    """

    run_reverse([
        str(TASKS_FILE)
    ])

    expected = [
        "input_horizontal_loop.mp4",
        "input_horizontal_autocomplete.mp4",
        "input_horizontal_reverse.mp4"
    ]

    for file in expected:
        path = OUTPUT_DIR / file

        assert path.exists(), f"{file} não foi criado"

        assert not has_audio_stream(path)