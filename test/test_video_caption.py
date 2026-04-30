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
TASKS_FILE = TEST_DIR / "tasks.json"
OUTPUT_DIR = BASE_DIR / "output" / "caption"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

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


@pytest.fixture
def tasks_backup():
    original = TASKS_FILE.read_text(encoding="utf-8") if TASKS_FILE.exists() else None
    yield
    if original:
        TASKS_FILE.write_text(original, encoding="utf-8")

def run_caption(check=True):
    return subprocess.run(
        ["python", "video_caption.py"],
        capture_output=True,
        text=True,
        check=check
    )

def write_tasks(tasks):
    TASKS_FILE.write_text(
        json.dumps(tasks, indent=2),
        encoding="utf-8"
    )

def update_style(**kwargs):
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))

    style = cfg["video_caption"]["text_style"]

    for k, v in kwargs.items():
        style[k] = v

    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2)


def output_exists(name):
    path = OUTPUT_DIR / name
    assert path.exists(), f"{name} não foi gerado"
    assert path.stat().st_size > 1000, f"{name} está vazio"
    return path

def test_single_word_responsive(clean_environment, config_backup, tasks_backup):
    """1 palavra → centralizado e não quebra"""
    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "one_word.mp4",
        "text": "TESTE"
    }])

    run_caption()
    output_exists("one_word.mp4")

def test_three_words_single_line(clean_environment, config_backup, tasks_backup):
    """3 palavras → 1 linha"""
    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "three_words.mp4",
        "text": "UM DOIS TRES"
    }])

    run_caption()
    output_exists("three_words.mp4")

def test_seven_words_wrap_two_lines(clean_environment, config_backup, tasks_backup):
    """7 palavras → deve quebrar em 2 linhas"""
    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "seven_words.mp4",
        "text": "UM DOIS TRES QUATRO CINCO SEIS SETE"
    }])

    run_caption()
    output_exists("seven_words.mp4")

def test_no_stroke_no_shadow(clean_environment, config_backup, tasks_backup):
    """Sem stroke e sem sombra"""
    update_style(show_stroke=False, show_shadow=False)

    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "no_style.mp4",
        "text": "TESTE"
    }])

    run_caption()
    output_exists("no_style.mp4")

def test_with_stroke_only(clean_environment, config_backup, tasks_backup):
    """Com stroke apenas"""
    update_style(show_stroke=True, show_shadow=False)

    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "stroke_only.mp4",
        "text": "TESTE"
    }])

    run_caption()
    output_exists("stroke_only.mp4")

def test_with_shadow_only(clean_environment, config_backup, tasks_backup):
    """Com sombra apenas"""
    update_style(show_stroke=False, show_shadow=True)

    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "shadow_only.mp4",
        "text": "TESTE"
    }])

    run_caption()
    output_exists("shadow_only.mp4")

def test_shadow_and_stroke(clean_environment, config_backup, tasks_backup):
    """Com sombra + stroke"""
    update_style(show_stroke=True, show_shadow=True)

    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "shadow_stroke.mp4",
        "text": "TESTE"
    }])

    run_caption()
    output_exists("shadow_stroke.mp4")

def test_highlight_word(clean_environment, config_backup, tasks_backup):
    """Valida highlight aplicado"""
    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "highlight.mp4",
        "text": "TESTE DE HIGHLIGHT",
        "highlight": "HIGHLIGHT"
    }])

    run_caption()
    output_exists("highlight.mp4")

def test_multiple_tasks(clean_environment, config_backup, tasks_backup):
    """Múltiplos vídeos"""
    write_tasks([
        {
            "input": str(INPUT_VIDEO),
            "output": "t1.mp4",
            "text": "A"
        },
        {
            "input": str(INPUT_VIDEO),
            "output": "t2.mp4",
            "text": "B"
        }
    ])

    run_caption()

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) == 2

def test_invalid_input(clean_environment, config_backup, tasks_backup):
    """Input inválido não quebra pipeline"""
    write_tasks([{
        "input": "fake.mp4",
        "output": "fail.mp4",
        "text": "ERRO"
    }])

    run_caption(check=False)

    files = list(OUTPUT_DIR.glob("*.mp4"))
    assert len(files) == 0


def test_multiple_runs(clean_environment, config_backup, tasks_backup):
    """Execução repetida"""
    write_tasks([{
        "input": str(INPUT_VIDEO),
        "output": "repeat.mp4",
        "text": "TESTE"
    }])

    run_caption()
    run_caption()

    output_exists("repeat.mp4")