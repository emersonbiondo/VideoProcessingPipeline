import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.visualizer_bars import VisualizerBars
from src.visualizer_dense_bars import VisualizerDenseBars
from src.visualizer_retro_bars import VisualizerRetroBars
from src.visualizer_cyberpunk import VisualizerCyberpunk
from src.visualizer_waveform import VisualizerWaveform
from src.visualizer_horizontal_lines import VisualizerHorizontalLines
from src.visualizer_stereo_scope import VisualizerStereoScope
from src.visualizer_pulse import VisualizerPulse
from src.visualizer_line_spectrum import VisualizerLineSpectrum
from src.visualizer_neon_ring import VisualizerNeonRing

VISUALIZERS = {
    "bars": VisualizerBars,
    "dense_bars": VisualizerDenseBars,
    "retro_bars": VisualizerRetroBars,
    "cyberpunk": VisualizerCyberpunk,
    "waveform": VisualizerWaveform,
    "horizontal_lines": VisualizerHorizontalLines,
    "stereo_scope": VisualizerStereoScope,
    "pulse": VisualizerPulse,
    "line_spectrum": VisualizerLineSpectrum,
    "neon_ring": VisualizerNeonRing,
}


def load_global_config():

    config_path = Path("config.json")

    if not config_path.exists():

        return {}

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def get_video_metadata(
    input_path,
    config
):

    default_output = config.get(
        "default_output",
        {}
    )

    default_width = default_output.get(
        "width",
        2560
    )

    default_height = default_output.get(
        "height",
        1440
    )

    default_fps = default_output.get(
        "fps",
        60
    )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        str(input_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)

    video_streams = [
        s for s in data.get("streams", [])
        if s.get("codec_type") == "video"
    ]

    if video_streams:

        stream = video_streams[0]

        fps_raw = stream.get(
            "r_frame_rate",
            f"{default_fps}/1"
        )

        if "/" in fps_raw:

            num, den = fps_raw.split("/")

            fps = float(num) / float(den)

        else:

            fps = float(fps_raw)

        return {
            "width": default_width,
            "height": default_height,
            "fps": fps
        }

    print(
        "INFO: Arquivo sem vídeo. "
        "Usando default_output."
    )

    return {
        "width": default_width,
        "height": default_height,
        "fps": default_fps
    }


def build_output_path(
    input_path,
    output_dir,
    custom_output=None
):

    if custom_output:

        output_filename = custom_output

    else:

        output_filename = (
            f"{Path(input_path).stem}_overlay.mp4"
        )

    return Path(output_dir) / output_filename


def load_preset(
    preset_path
):

    with open(
        preset_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def has_audio_stream(
    input_path
):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(input_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    return bool(
        result.stdout.strip()
    )


def mux_audio(
    video_path,
    audio_source_path
):

    temp_output = (
        video_path.parent /
        f"{video_path.stem}_temp.mp4"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_source_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-shortest",
        str(temp_output)
    ]

    subprocess.run(
        command,
        check=True
    )

    video_path.unlink()

    shutil.move(
        str(temp_output),
        str(video_path)
    )


def process_task(
    task,
    config
):

    input_path = Path(task["input"])

    preset_path = Path(task["preset"])

    preset = load_preset(
        preset_path
    )

    visualizer_name = preset.get(
        "visualizer"
    )

    if visualizer_name not in VISUALIZERS:

        raise ValueError(
            f"Visualizer inválido: "
            f"{visualizer_name}"
        )

    visualizer = VISUALIZERS[
        visualizer_name
    ]()

    output_dir = Path(
        config.get(
            "paths",
            {}
        ).get(
            "output",
            "output/visualizer"
        )
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    custom_output = task.get(
        "output"
    )

    output_path = build_output_path(
        input_path=input_path,
        output_dir=output_dir,
        custom_output=custom_output
    )

    metadata = get_video_metadata(
        input_path,
        config
    )

    print(
        f"INFO: Renderizando: "
        f"{input_path.name}"
    )

    visualizer.render(
        input_path=input_path,
        output_path=output_path,
        preset=preset,
        metadata=metadata,
        config=config
    )

    if has_audio_stream(
        input_path
    ):

        print(
            "INFO: Adicionando áudio..."
        )

        mux_audio(
            video_path=output_path,
            audio_source_path=input_path
        )

    print(
        f"INFO: Finalizado: "
        f"{output_path}"
    )


def run_pipeline(
    pipeline_path
):

    with open(
        pipeline_path,
        "r",
        encoding="utf-8"
    ) as f:

        tasks = json.load(f)

    global_config = load_global_config()

    config = global_config.get(
        "video_visualizer",
        {}
    )

    for task in tasks:

        process_task(
            task,
            config
        )


def run_manual(
    input_path,
    preset_path,
    output=None
):

    global_config = load_global_config()

    config = global_config.get(
        "video_visualizer",
        {}
    )

    task = {
        "input": input_path,
        "preset": preset_path
    }

    if output:

        task["output"] = output

    process_task(
        task,
        config
    )


def main():

    if (
        len(sys.argv) == 2
        and sys.argv[1].endswith(".json")
    ):

        run_pipeline(
            sys.argv[1]
        )

        return

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input"
    )

    parser.add_argument(
        "preset"
    )

    parser.add_argument(
        "--output",
        help="Nome final do arquivo"
    )

    args = parser.parse_args()

    run_manual(
        input_path=args.input,
        preset_path=args.preset,
        output=args.output
    )


if __name__ == "__main__":
    main()