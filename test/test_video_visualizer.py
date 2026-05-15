import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(
    str(
        Path(__file__).resolve().parent.parent
    )
)

import pytest
import video_visualizer


@pytest.fixture
def sample_metadata():
    return {
        "width": 1920,
        "height": 1080,
        "fps": 30.0
    }


@pytest.fixture
def sample_task():
    return {
        "input": "test/input.mp4",
        "preset": "visualizer_presets/retro.json"
    }


@pytest.fixture
def sample_task_with_output():
    return {
        "input": "test/input.mp4",
        "preset": "visualizer_presets/retro.json",
        "output": "custom_output.mp4"
    }


@pytest.fixture
def sample_config():
    return {
        "output_dir": "output/visualizer"
    }


def test_build_output_path_default_name():

    result = video_visualizer.build_output_path(
        input_path="test/input.mp4",
        output_dir="output/visualizer"
    )

    assert result == Path(
        "output/visualizer/input_overlay.mp4"
    )


def test_build_output_path_custom_name():

    result = video_visualizer.build_output_path(
        input_path="test/input.mp4",
        output_dir="output/visualizer",
        custom_output="custom.mp4"
    )

    assert result == Path(
        "output/visualizer/custom.mp4"
    )


def test_load_preset(tmp_path):

    preset_data = {
        "visualizer": "bars"
    }

    preset_file = tmp_path / "preset.json"

    preset_file.write_text(
        json.dumps(preset_data),
        encoding="utf-8"
    )

    result = video_visualizer.load_preset(
        preset_file
    )

    assert result == preset_data


@patch("video_visualizer.subprocess.run")
def test_get_video_metadata(mock_run):

    mock_run.return_value.stdout = json.dumps({
        "streams": [
            {
                "width": 1280,
                "height": 720,
                "r_frame_rate": "30/1"
            }
        ]
    })

    result = video_visualizer.get_video_metadata(
        "video.mp4"
    )

    assert result["width"] == 1280
    assert result["height"] == 720
    assert result["fps"] == 30.0


@patch("video_visualizer.get_video_metadata")
@patch("video_visualizer.load_preset")
def test_process_task_default_output(
    mock_load_preset,
    mock_metadata,
    sample_task,
    sample_config,
    sample_metadata
):

    mock_load_preset.return_value = {
        "visualizer": "bars"
    }

    mock_metadata.return_value = sample_metadata

    mock_visualizer = MagicMock()

    with patch.dict(
        video_visualizer.VISUALIZERS,
        {
            "bars": lambda: mock_visualizer
        }
    ):

        video_visualizer.process_task(
            sample_task,
            sample_config
        )

    kwargs = mock_visualizer.render.call_args.kwargs

    assert kwargs["output_path"] == Path(
        "output/visualizer/input_overlay.mp4"
    )


@patch("video_visualizer.get_video_metadata")
@patch("video_visualizer.load_preset")
def test_process_task_custom_output(
    mock_load_preset,
    mock_metadata,
    sample_task_with_output,
    sample_config,
    sample_metadata
):

    mock_load_preset.return_value = {
        "visualizer": "bars"
    }

    mock_metadata.return_value = sample_metadata

    mock_visualizer = MagicMock()

    with patch.dict(
        video_visualizer.VISUALIZERS,
        {
            "bars": lambda: mock_visualizer
        }
    ):

        video_visualizer.process_task(
            sample_task_with_output,
            sample_config
        )

    kwargs = mock_visualizer.render.call_args.kwargs

    assert kwargs["output_path"] == Path(
        "output/visualizer/custom_output.mp4"
    )


@patch("video_visualizer.load_preset")
def test_process_task_invalid_visualizer(
    mock_load_preset,
    sample_task,
    sample_config
):

    mock_load_preset.return_value = {
        "visualizer": "invalid"
    }

    with pytest.raises(ValueError):

        video_visualizer.process_task(
            sample_task,
            sample_config
        )


@patch("video_visualizer.process_task")
def test_run_pipeline(
    mock_process_task,
    tmp_path
):

    tasks = [
        {
            "input": "video.mp4",
            "preset": "preset.json"
        },
        {
            "input": "video2.mp4",
            "preset": "preset2.json"
        }
    ]

    pipeline_file = tmp_path / "tasks.json"

    pipeline_file.write_text(
        json.dumps(tasks),
        encoding="utf-8"
    )

    video_visualizer.run_pipeline(
        pipeline_file
    )

    assert mock_process_task.call_count == 2


@patch("video_visualizer.process_task")
def test_run_manual_without_output(
    mock_process_task
):

    video_visualizer.run_manual(
        input_path="video.mp4",
        preset_path="preset.json"
    )

    task = mock_process_task.call_args.args[0]

    assert task["input"] == "video.mp4"
    assert task["preset"] == "preset.json"
    assert "output" not in task


@patch("video_visualizer.process_task")
def test_run_manual_with_output(
    mock_process_task
):

    video_visualizer.run_manual(
        input_path="video.mp4",
        preset_path="preset.json",
        output="custom.mp4"
    )

    task = mock_process_task.call_args.args[0]

    assert task["output"] == "custom.mp4"


@patch("video_visualizer.run_pipeline")
def test_main_pipeline_mode(
    mock_pipeline
):

    with patch(
        "sys.argv",
        [
            "video_visualizer.py",
            "tasks.json"
        ]
    ):

        video_visualizer.main()

    mock_pipeline.assert_called_once()


@patch("video_visualizer.run_manual")
def test_main_manual_mode(
    mock_manual
):

    with patch(
        "sys.argv",
        [
            "video_visualizer.py",
            "video.mp4",
            "preset.json"
        ]
    ):

        video_visualizer.main()

    mock_manual.assert_called_once()


@patch("video_visualizer.run_manual")
def test_main_manual_mode_with_output(
    mock_manual
):

    with patch(
        "sys.argv",
        [
            "video_visualizer.py",
            "video.mp4",
            "preset.json",
            "--output",
            "custom.mp4"
        ]
    ):

        video_visualizer.main()

    kwargs = mock_manual.call_args.kwargs

    assert kwargs["output"] == "custom.mp4"