import sys
import json
import logging
import time
import os
import tempfile
from pathlib import Path

from moviepy import VideoFileClip
from moviepy.video.fx.Resize import Resize

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"config.json not found: {CONFIG_FILE}")

    data = json.load(open(CONFIG_FILE, encoding="utf-8"))

    if "video_processor" not in data:
        raise ValueError("Missing 'video_processor'")

    return data["video_processor"]

def write_queue_success(cfg, video_path):
    try:
        success_file = BASE_DIR / cfg["queue"]["success"]
        with open(success_file, "a", encoding="utf-8") as f:
            f.write(video_path.name + "\n")
    except Exception as e:
        logging.warning(f"Erro ao escrever queue success: {e}")


def write_queue_error(cfg, video_path):
    try:
        error_file = BASE_DIR / cfg["queue"]["error"]
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(video_path.name + "\n")
    except Exception as e:
        logging.warning(f"Erro ao escrever queue error: {e}")

def resize_clip(clip, max_res):
    w, h = clip.size
    if w >= h:
        return clip.with_effects([Resize(height=max_res)])
    else:
        return clip.with_effects([Resize(width=max_res)])

def format_srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def safe_remove(path, retries=5, delay=0.5):
    if not path or not os.path.exists(path):
        return

    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(delay)

def process_video(video_path, cfg):
    video_path = Path(video_path)

    if not video_path.exists():
        write_queue_error(cfg, video_path)
        raise FileNotFoundError(f"Input not found: {video_path}")

    output_dir = BASE_DIR / cfg["paths"]["output"]
    output_dir.mkdir(parents=True, exist_ok=True)

    name = video_path.stem
    output_video = output_dir / f"{name}{cfg['file']['suffix']}.mp4"

    need_audio = cfg["audio"]["enabled"]
    need_transcription = cfg["transcription"]["enabled"]
    need_subtitle = cfg["subtitle"]["enabled"]

    wav_path = None
    transcription_result = None

    try:
        if need_transcription or need_subtitle:
            clip = VideoFileClip(str(video_path))

            if clip.audio:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                wav_path = tmp.name
                tmp.close()

                logging.info("Extracting WAV...")
                clip.audio.write_audiofile(wav_path, codec="pcm_s16le")

            else:
                logging.warning("No audio found → skipping transcription/subtitle")

            clip.close()

        if need_transcription and wav_path:
            import whisper
            logging.info("Running transcription...")

            model = whisper.load_model(cfg["transcription"]["model"])
            transcription_result = model.transcribe(wav_path)

            (output_dir / f"{name}.txt").write_text(
                transcription_result["text"],
                encoding="utf-8"
            )

        if need_subtitle and transcription_result:
            logging.info("Generating subtitles...")

            with open(output_dir / f"{name}.srt", "w", encoding="utf-8") as f:
                for i, seg in enumerate(transcription_result["segments"], 1):
                    f.write(f"{i}\n")
                    f.write(
                        f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}\n"
                    )
                    f.write(seg["text"].strip() + "\n\n")

        if need_audio:
            clip = VideoFileClip(str(video_path))

            if clip.audio:
                logging.info("Exporting audio...")
                clip.audio.write_audiofile(
                    str(output_dir / f"{name}.{cfg['audio']['extension']}"),
                    codec=cfg["audio"]["codec"],
                    bitrate=cfg["audio"]["bitrate"]
                )
            else:
                logging.warning("No audio → skipping audio export")

            clip.close()

        for attempt in range(cfg["queue"]["max_retries"] + 1):
            try:
                logging.info(f"Encoding video (attempt {attempt+1})...")

                clip = VideoFileClip(str(video_path))
                clip_resized = resize_clip(clip, cfg["video"]["res_max"])

                kwargs = {
                    "codec": "libx264",
                    "fps": cfg["video"]["fps"],
                    "bitrate": cfg["video"]["bitrate"],
                    "preset": cfg["video"]["preset"],
                    "ffmpeg_params": ["-pix_fmt", cfg["video"]["pix_fmt"]],
                }

                if clip.audio and not cfg["video"]["mute_video"]:
                    kwargs["audio_codec"] = cfg["video"]["audio_codec"]
                    kwargs["audio_bitrate"] = cfg["video"]["audio_bitrate"]
                else:
                    kwargs["audio"] = False

                clip_resized.write_videofile(str(output_video), **kwargs)

                clip.close()
                break

            except Exception as e:
                logging.error(f"Encode error: {e}")

                if attempt < cfg["queue"]["max_retries"]:
                    time.sleep(cfg["queue"]["retry_delay"])
                else:
                    raise

        write_queue_success(cfg, video_path)

    except Exception as e:
        logging.error(f"Erro ao processar {video_path.name}: {e}")
        write_queue_error(cfg, video_path)
        raise

    finally:
        safe_remove(wav_path)

    logging.info(f"Done: {video_path.name}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python video_processor.py <video.mp4 | list.txt>")
        return

    cfg = load_config()
    input_path = Path(sys.argv[1])

    if input_path.suffix == ".txt":
        videos = [line.strip() for line in open(input_path) if line.strip()]
        for v in videos:
            process_video(v, cfg)
    else:
        process_video(input_path, cfg)

if __name__ == "__main__":
    main()