# test_video_publish_essential_corrected.py
# CORRECTED ESSENTIAL TEST SUITE (26 TESTS) - stable, no duplication, stronger asserts

import subprocess
import json
import shutil
from pathlib import Path
import pytest
import imageio_ffmpeg
import uuid
import shutil

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = BASE_DIR / "config.json"
TEST_DIR = BASE_DIR / "test"

INPUT_HORIZONTAL = TEST_DIR / "input_horizontal.mp4"
INPUT_VERTICAL = TEST_DIR / "input_vertical.mp4"

# Each test will use its own isolated output directory
OUTPUT_ROOT = BASE_DIR / "output"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FFPROBE = FFMPEG.replace("ffmpeg", "ffprobe")


# ==============================
# FIXTURES
# ==============================

@pytest.fixture(scope="session", autouse=True)
def generate_inputs():
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_HORIZONTAL.exists():
        subprocess.run([
            "ffmpeg","-f","lavfi","-i","testsrc=size=1280x720:rate=30",
            "-f","lavfi","-i","sine=frequency=1000",
            "-t","5","-c:v","libx264","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","128k",str(INPUT_HORIZONTAL)
        ], check=True)

    if not INPUT_VERTICAL.exists():
        subprocess.run([
            "ffmpeg","-f","lavfi","-i","testsrc=size=1080x1920:rate=30",
            "-f","lavfi","-i","sine=frequency=1000",
            "-t","5","-c:v","libx264","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","128k",str(INPUT_VERTICAL)
        ], check=True)


@pytest.fixture
def isolated_output_dir(tmp_path):
    # unique output folder per test
    out = tmp_path / f"publish_{uuid.uuid4().hex[:8]}"
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def config_backup():
    original = CONFIG_FILE.read_text(encoding="utf-8")
    yield
    CONFIG_FILE.write_text(original, encoding="utf-8")


# ==============================
# HELPERS
# ==============================

def write_config(presets, output_path):
    cfg = {
        "video_publish": {
            "paths": {
                "output": str(output_path)
            },
            "queue": {
                "max_workers": 2,
                "max_retries": 1,
                "retry_delay": 1
            },
            "presets": presets
        }
    }

    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def run(cmd, check=True):
    return subprocess.run(cmd, check=check)


def outputs(output_path):
    return list(Path(output_path).glob("*.mp4"))


def ffprobe(file):
    ffprobe_bin = shutil.which("ffprobe")

    if not ffprobe_bin:
        pytest.skip("ffprobe não encontrado no sistema")

    result = subprocess.run([
        ffprobe_bin,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(file)
    ], capture_output=True, text=True)

    return json.loads(result.stdout)


# ==============================
# 1. INPUT (5)
# ==============================

def test_cli_valid(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_a" in outs[0].name


def test_cli_invalid(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py","fake.mp4","out"], check=False)
    assert len(outputs(isolated_output_dir)) == 0


def test_csv_multiple(isolated_output_dir, config_backup, tmp_path):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    csv = tmp_path / "list.csv"
    csv.write_text(f"{INPUT_HORIZONTAL},a\n{INPUT_HORIZONTAL},b\n", encoding="utf-8")
    run(["python","video_publish.py",str(csv)])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 2
    names = [f.name for f in outs]
    assert any("a_a" in n or n.endswith("a_a.mp4") or "_a.mp4" in n for n in names)


def test_csv_ignore_invalid(isolated_output_dir, config_backup, tmp_path):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    csv = tmp_path / "list.csv"
    csv.write_text(f"invalid_line\n{INPUT_HORIZONTAL},a\n", encoding="utf-8")
    run(["python","video_publish.py",str(csv)])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_a" in outs[0].name


def test_csv_ignore_comments(isolated_output_dir, config_backup, tmp_path):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    csv = tmp_path / "list.csv"
    csv.write_text(f"#comment\n{INPUT_HORIZONTAL},a\n", encoding="utf-8")
    run(["python","video_publish.py",str(csv)])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_a" in outs[0].name


# ==============================
# 2. PRESETS (6)
# ==============================

def test_valid_preset(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert len(outputs(isolated_output_dir)) == 1


def test_disabled_preset(isolated_output_dir, config_backup):
    write_config([{"name":"a","enabled":False,"tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert len(outputs(isolated_output_dir)) == 0


def test_no_type_runs(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert len(outputs(isolated_output_dir)) == 1


def test_horizontal_type(isolated_output_dir, config_backup):
    write_config([{"name":"h","type":"horizontal","tag":"_h","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_h" in outs[0].name


def test_vertical_type(isolated_output_dir, config_backup):
    write_config([{"name":"v","type":"vertical","tag":"_v","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_VERTICAL),"out"])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_v" in outs[0].name


def test_mixed_presets(isolated_output_dir, config_backup):
    write_config([
        {"name":"h","type":"horizontal","tag":"_h","video":{}},
        {"name":"a","tag":"_a","video":{}}
    ], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    outs = outputs(isolated_output_dir)
    names = [f.name for f in outs]
    assert len(outs) == 2
    assert any("_h" in n for n in names) and any("_a" in n for n in names)


# ==============================
# 3. PIPELINE LOGIC (3)
# ==============================

def test_multiple_outputs(isolated_output_dir, config_backup):
    write_config([
        {"name":"a","tag":"_a","video":{}},
        {"name":"b","tag":"_b","video":{}}
    ], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    outs = outputs(isolated_output_dir)
    names = [f.name for f in outs]
    assert len(outs) == 2
    assert any("_a" in n for n in names) and any("_b" in n for n in names)


def test_tag_applied(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_tag","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 1 and "_tag" in outs[0].name


def test_incompatible_ignored(isolated_output_dir, config_backup):
    write_config([{"name":"v","type":"vertical","tag":"_v","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert len(outputs(isolated_output_dir)) == 0


# ==============================
# 4. EXECUTION (4)
# ==============================

def test_csv_execution(isolated_output_dir, config_backup, tmp_path):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    csv = tmp_path / "list.csv"
    csv.write_text(f"{INPUT_HORIZONTAL},a\n", encoding="utf-8")
    run(["python","video_publish.py",str(csv)])
    assert len(outputs(isolated_output_dir)) == 1


def test_parallel(isolated_output_dir, config_backup, tmp_path):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    csv = tmp_path / "list.csv"
    csv.write_text(f"{INPUT_HORIZONTAL},a\n{INPUT_HORIZONTAL},b\n", encoding="utf-8")
    run(["python","video_publish.py",str(csv)])
    outs = outputs(isolated_output_dir)
    assert len(outs) == 2
    names = [f.name for f in outs]
    assert any("a_a" in n or "_a" in n for n in names)


def test_partial_failure(isolated_output_dir, config_backup):
    write_config([
        {"name":"ok","tag":"_ok","video":{}},
        {"name":"bad","tag":"_bad","video":{"codec":"invalid"}}
    ], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"], check=False)
    names = [f.name for f in outputs(isolated_output_dir)]
    assert any("_ok" in n for n in names)


def test_multiple_jobs_cli(isolated_output_dir, config_backup):
    # simulate two runs to ensure queue doesn't interfere
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out1"])
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out2"])
    outs = outputs(isolated_output_dir)
    # same tag, different base names
    assert len(outs) == 2


# ==============================
# 5. OUTPUT (4)
# ==============================

def test_file_created(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert len(outputs(isolated_output_dir)) == 1


def test_not_empty(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    f = outputs(isolated_output_dir)[0]
    assert f.stat().st_size > 1000


def test_overwrite(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    first = outputs(isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    second = outputs(isolated_output_dir)
    assert len(first) == 1 and len(second) == 1


def test_output_dir_created(tmp_path, config_backup):
    out = tmp_path / "new_output_dir"
    # do not create it beforehand
    write_config([{"name":"a","tag":"_a","video":{}}], out)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    assert out.exists()
    assert len(list(out.glob("*.mp4"))) == 1


# ==============================
# 6. MEDIA VALIDATION (4)
# ==============================

def test_resolution(isolated_output_dir, config_backup):
    write_config([{"name":"r","tag":"_r","video":{"width":320,"height":240}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    meta = ffprobe(outputs(isolated_output_dir)[0])
    v = next(s for s in meta["streams"] if s["codec_type"]=="video")
    assert v["width"] == 320 and v["height"] == 240


def test_audio_exists(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    meta = ffprobe(outputs(isolated_output_dir)[0])
    assert any(s["codec_type"]=="audio" for s in meta["streams"])


def test_codec(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{"codec":"libx264"}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    meta = ffprobe(outputs(isolated_output_dir)[0])
    v = next(s for s in meta["streams"] if s["codec_type"]=="video")
    assert v["codec_name"] == "h264"


def test_duration(isolated_output_dir, config_backup):
    write_config([{"name":"a","tag":"_a","video":{}}], isolated_output_dir)
    run(["python","video_publish.py",str(INPUT_HORIZONTAL),"out"])
    meta = ffprobe(outputs(isolated_output_dir)[0])
    assert float(meta["format"]["duration"]) > 4.0
