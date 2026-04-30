import subprocess
import json
import shutil
from pathlib import Path
import pytest
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_FILE = BASE_DIR / "config.json"
TEST_DIR = BASE_DIR / "test"
INPUT_VIDEO = TEST_DIR / "input.mp4"
CSV_FILE = TEST_DIR / "cuts.csv"
OUTPUT_DIR = BASE_DIR / "output" / "cuts"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"config.json not found at: {CONFIG_FILE}")

if not INPUT_VIDEO.exists():
    raise FileNotFoundError(f"Missing test video: {INPUT_VIDEO}")

if not CSV_FILE.exists():
    raise FileNotFoundError(f"Missing CSV file: {CSV_FILE}")

@pytest.fixture
def clean_environment():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yield

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

@pytest.fixture
def config_backup():
    original = CONFIG_FILE.read_text(encoding="utf-8")
    yield
    CONFIG_FILE.write_text(original, encoding="utf-8")

def run_cut(csv_path=CSV_FILE, video_path=INPUT_VIDEO, check=True):
    return subprocess.run(
        ["python", "video_cut.py", str(csv_path), str(video_path)],
        capture_output=True,
        text=True,
        check=check
    )

def set_mode(mode):
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    cfg["video_cut"]["mode"] = mode
    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2)


def get_duration(file):
    result = subprocess.run(
        [FFMPEG, "-i", str(file), "-hide_banner"],
        stderr=subprocess.PIPE,
        text=True
    )

    for line in result.stderr.splitlines():
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)

    return None

@pytest.mark.parametrize("mode", ["fast", "precise"], ids=[
    "modo_fast",
    "modo_precise"
])
def test_basic_cuts_duration(mode, clean_environment, config_backup):
    """Valida cortes básicos e duração aproximada"""
    set_mode(mode)
    run_cut()

    expected = {
        "input_cut_1.mp4": 2,
        "input_cut_2.mp4": 2,
        "input_cut_3.mp4": 2,
        "input_cut_4.mp4": 1,
    }

    for file, expected_duration in expected.items():
        path = OUTPUT_DIR / file

        assert path.exists(), f"{file} não foi criado"

        duration = get_duration(path)
        assert duration is not None, f"Duração não detectada: {file}"

        assert abs(duration - expected_duration) <= 0.5


def test_invalid_cut_is_skipped(clean_environment, config_backup):
    """Corte inválido não deve gerar arquivo"""
    run_cut()

    invalid = OUTPUT_DIR / "input_invalid_cut.mp4"
    assert not invalid.exists()


def test_unordered_csv_processing(clean_environment, config_backup, tmp_path):
    """CSV fora de ordem deve funcionar normalmente"""
    csv = tmp_path / "unordered.csv"

    csv.write_text(
        "00:05,00:07,c3\n"
        "00:01,00:03,c1\n"
        "00:03,00:05,c2\n",
        encoding="utf-8"
    )

    run_cut(csv_path=csv)

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) == 3

def test_video_without_audio(clean_environment, config_backup, tmp_path):
    """Pipeline deve funcionar sem áudio"""
    video = tmp_path / "no_audio.mp4"

    subprocess.run([
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=size=1280x720:rate=30",
        "-t", "5",
        "-an",
        str(video)
    ], check=True)

    csv = tmp_path / "test.csv"
    csv.write_text("00:01,00:03,cut\n", encoding="utf-8")

    run_cut(csv_path=csv, video_path=video)

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) == 1

def test_invalid_csv_is_handled(clean_environment, config_backup, tmp_path):
    """CSV inválido não deve quebrar execução"""
    csv = tmp_path / "invalid.csv"
    csv.write_text("00:01,sem_fim\n", encoding="utf-8")

    run_cut(csv_path=csv)

def test_missing_video_should_fail(clean_environment, config_backup):
    """Arquivo inexistente deve gerar erro"""
    with pytest.raises(subprocess.CalledProcessError):
        run_cut(video_path="fake.mp4")

def test_multiple_runs_no_conflict(clean_environment, config_backup):
    """Execuções repetidas não devem conflitar"""
    run_cut()
    run_cut()

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) >= 1

def test_csv_with_empty_lines(clean_environment, config_backup, tmp_path):
    """Linhas vazias no CSV devem ser ignoradas"""
    csv = tmp_path / "test.csv"

    csv.write_text(
        "\n"
        "00:01,00:03,c1\n"
        "\n",
        encoding="utf-8"
    )

    run_cut(csv_path=csv)

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) == 1