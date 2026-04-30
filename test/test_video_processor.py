import subprocess
import json
import shutil
import re
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = BASE_DIR / "config.json"
TEST_DIR = BASE_DIR / "test"
INPUT_VIDEO = TEST_DIR / "input_with_audio.mp4"
OUTPUT_DIR = BASE_DIR / "output" / "processor"

@pytest.fixture
def clean_environment():
    """Limpa ambiente de saída e filas antes e depois dos testes"""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.load(open(CONFIG_FILE))
    q = cfg["video_processor"]["queue"]

    success = BASE_DIR / q["success"]
    error = BASE_DIR / q["error"]

    if success.exists():
        success.unlink()
    if error.exists():
        error.unlink()

    yield

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    if success.exists():
        success.unlink()
    if error.exists():
        error.unlink()

@pytest.fixture
def config_backup():
    """Faz backup do config.json e restaura após o teste"""
    original = CONFIG_FILE.read_text(encoding="utf-8")
    yield
    CONFIG_FILE.write_text(original, encoding="utf-8")

def run(input_file=INPUT_VIDEO, check=True):
    """Executa o video_processor via subprocess"""
    return subprocess.run(
        ["python", "video_processor.py", str(input_file)],
        capture_output=True,
        text=True,
        check=check
    )

def set_flags(audio, transcription, subtitle):
    """Altera flags do processor diretamente no config"""
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    vp = cfg["video_processor"]

    vp["audio"]["enabled"] = audio
    vp["transcription"]["enabled"] = transcription
    vp["subtitle"]["enabled"] = subtitle

    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2)

def outputs():
    """Retorna arquivos gerados pelo processor"""
    return {
        "video": list(OUTPUT_DIR.glob("*.mp4")),
        "audio": list(OUTPUT_DIR.glob("*.mp3")),
        "txt": list(OUTPUT_DIR.glob("*.txt")),
        "srt": list(OUTPUT_DIR.glob("*.srt")),
    }

def normalize(text):
    """Normaliza texto para comparação (remove acentos e pontuação)"""
    return (
        text.lower()
        .replace(",", "")
        .replace(".", "")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ã", "a")
        .replace("ê", "e")
        .replace("ç", "c")
        .replace("ã¡", "a")
        .replace("ã©", "e")
    )

@pytest.mark.parametrize(
    "a,t,s,exp",
    [
        (False, False, False, (0, 0, 0)),
        (True, False, False, (1, 0, 0)),
        (False, True, False, (0, 1, 0)),
        (False, True, True, (0, 1, 1)),
        (True, True, True, (1, 1, 1)),
        (False, False, True, (0, 0, 0)),
    ],
    ids=[
        "nenhum_recurso",
        "somente_audio",
        "somente_transcricao",
        "transcricao_e_legenda",
        "tudo_ativo",
        "legenda_invalida",
    ]
)

def test_flags(a, t, s, exp, clean_environment, config_backup):
    """Valida geração de arquivos conforme combinações de flags"""
    set_flags(a, t, s)
    run()

    out = outputs()

    assert len(out["video"]) == 1
    assert len(out["audio"]) == exp[0]
    assert len(out["txt"]) == exp[1]
    assert len(out["srt"]) == exp[2]

def test_transcription_expected_content(clean_environment, config_backup):
    """Valida conteúdo esperado da transcrição"""
    set_flags(False, True, False)
    run()

    content = outputs()["txt"][0].read_text(encoding="utf-8")

    assert normalize("test de audio 1 2 3 isso e um teste") in normalize(content)

def test_srt_expected_content(clean_environment, config_backup):
    """Valida estrutura e conteúdo básico do arquivo SRT"""
    set_flags(False, True, True)
    run()

    content = outputs()["srt"][0].read_text(encoding="utf-8")

    assert "-->" in content
    assert "test de audio" in normalize(content)

def test_video_without_audio(tmp_path, clean_environment, config_backup):
    """Valida processamento de vídeo sem faixa de áudio"""
    video = tmp_path / "no_audio.mp4"

    subprocess.run([
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=size=1280x720:rate=30",
        "-t", "5",
        "-an",
        str(video)
    ], check=True)

    run(video)

    assert len(outputs()["video"]) == 1

def test_batch_processing(tmp_path, clean_environment, config_backup):
    """Valida processamento em lote via arquivo txt"""
    list_file = tmp_path / "list.txt"
    list_file.write_text(str(INPUT_VIDEO))

    run(list_file)

    assert len(outputs()["video"]) >= 1

def test_queue_success(clean_environment, config_backup):
    """Valida escrita correta na fila de sucesso"""
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    success = BASE_DIR / cfg["video_processor"]["queue"]["success"]

    run()

    assert success.exists()
    assert "input_with_audio.mp4" in success.read_text(encoding="utf-8")

def test_queue_error(clean_environment, config_backup):
    """Valida escrita correta na fila de erro"""
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    error = BASE_DIR / cfg["video_processor"]["queue"]["error"]

    run("arquivo_invalido.mp4", check=False)

    assert error.exists()
    assert "arquivo_invalido.mp4" in error.read_text(encoding="utf-8")

def test_retry(clean_environment, config_backup):
    """Valida comportamento de retry ao ocorrer erro"""
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    cfg["video_processor"]["queue"]["max_retries"] = 1

    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2)

    result = run("arquivo_invalido.mp4", check=False)

    assert result.returncode != 0

def test_video_bitrate_real(clean_environment, config_backup):
    """Valida bitrate real do vídeo gerado via ffprobe"""
    run()

    video = outputs()["video"][0]

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video)
        ],
        capture_output=True,
        text=True
    )

    bitrate = int(result.stdout.strip())
    assert bitrate > 100000

def test_video_duration(clean_environment, config_backup):
    """Valida duração do vídeo gerado"""
    run()

    video = outputs()["video"][0]

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video)
        ],
        capture_output=True,
        text=True
    )

    duration = float(result.stdout.strip())
    assert duration > 0

def test_srt_sync(clean_environment, config_backup):
    """Valida sincronização dos timestamps do SRT"""
    set_flags(False, True, True)
    run()

    content = outputs()["srt"][0].read_text(encoding="utf-8")

    matches = re.findall(
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
        content
    )

    assert len(matches) > 0

    def to_sec(t):
        h, m, s_ms = t.split(":")
        s, ms = s_ms.split(",")
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

    for start, end in matches:
        assert to_sec(end) > to_sec(start)