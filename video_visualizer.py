import argparse
import json
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


def get_video_metadata(input_path):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate",
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

    stream = data["streams"][0]

    fps_raw = stream["r_frame_rate"]

    if "/" in fps_raw:

        num, den = fps_raw.split("/")

        fps = float(num) / float(den)

    else:

        fps = float(fps_raw)

    return {
        "width": stream["width"],
        "height": stream["height"],
        "fps": fps
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
            "output_dir",
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
        input_path
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

    config = {
        "output_dir": "output/visualizer"
    }

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

    config = {
        "output_dir": "output/visualizer"
    }

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