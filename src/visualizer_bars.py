# src/visualizer_bars.py

import subprocess


class VisualizerBars:

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

        ascale = preset.get(
            "ascale",
            "log"
        )

        fscale = preset.get(
            "fscale",
            "lin"
        )

        win_size = preset.get(
            "win_size",
            1024
        )

        cmode = preset.get(
            "cmode",
            "combined"
        )

        glow_blur = preset.get(
            "glow_blur",
            10
        )

        glow_opacity = preset.get(
            "glow_opacity",
            1.0
        )

        blend_mode = preset.get(
            "blend_mode",
            "lighten"
        )

        glow_color = preset.get(
            "glow_color",
            {
                "r": 0.0,
                "g": 1.0,
                "b": 0.0
            }
        )

        glow_r = glow_color.get(
            "r",
            0.0
        )

        glow_g = glow_color.get(
            "g",
            1.0
        )

        glow_b = glow_color.get(
            "b",
            0.0
        )

        # SEMPRE usa bar
        # lines agora são simuladas
        # com barras ultrafinas

        base_filter = (
            f"showfreqs="
            f"s={width}x{height}:"
            f"mode=bar:"
            f"ascale={ascale}:"
            f"fscale={fscale}:"
            f"win_size={win_size}:"
            f"cmode={cmode}"
        )

        filter_complex = (
            f"[0:a]"
            f"{base_filter},"
            f"format=gray,"
            f"eq=brightness=0.35:contrast=3.5,"
            f"format=rgba,"
            f"colorchannelmixer=aa=0.75"
            f"[base];"

            f"[0:a]"
            f"{base_filter},"
            f"format=gray,"
            f"format=rgba,"
            f"gblur=sigma={glow_blur},"
            f"colorchannelmixer="
            f"rr={glow_r}:"
            f"gg={glow_g}:"
            f"bb={glow_b}:"
            f"aa={glow_opacity}"
            f"[glow];"

            f"[glow][base]"
            f"blend=all_mode={blend_mode}"
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