import subprocess


class VisualizerNeonRing:

    def render(
        self,
        input_path,
        output_path,
        preset,
        metadata,
        config
    ):

        width = metadata["width"]
        height = metadata["height"]
        fps = metadata["fps"]

        glow_blur = preset.get(
            "glow_blur",
            8
        )

        glow_opacity = preset.get(
            "glow_opacity",
            0.45
        )

        ring_size = preset.get(
            "ring_size",
            0.55
        )

        color = preset.get(
            "glow_color",
            {
                "r": 0.0,
                "g": 1.0,
                "b": 1.0
            }
        )

        rr = color.get("r", 0.0)
        gg = color.get("g", 1.0)
        bb = color.get("b", 1.0)

        filter_complex = (
            f"[0:a]"
            f"avectorscope="
            f"s={width}x{height}:"
            f"mode=lissajous:"
            f"draw=line:"
            f"rc=255:gc=255:bc=255,"
            f"format=rgba,"
            f"gblur=sigma={glow_blur},"
            f"colorchannelmixer="
            f"rr={rr}:"
            f"gg={gg}:"
            f"bb={bb}:"
            f"aa={glow_opacity}"
            f"[glow];"

            f"[0:a]"
            f"avectorscope="
            f"s={width}x{height}:"
            f"mode=lissajous:"
            f"draw=line:"
            f"rc=255:gc=255:bc=255,"
            f"format=rgba"
            f"[base];"

            f"[glow][base]"
            f"blend=all_mode=screen"
        )

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",

            "-i",
            str(input_path),

            "-filter_complex",
            filter_complex,

            "-r",
            str(fps),

            "-an",

            "-c:v",
            "libx264",

            "-pix_fmt",
            "yuv420p",

            str(output_path)
        ]

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
