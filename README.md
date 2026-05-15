# Video Processing Pipeline

Pipeline modular em Python para processamento completo de vídeo:

* Encode e compressão (MoviePy)
* Corte (FFmpeg – fast e precise)
* Caption com hook + highlight (MoviePy)
* Audio Visualizers FFT / Audio Reactive
* Processamento em lote (queue)
* Execução paralela
* Retry automático
* Encode profissional (HEVC Main10 CBR)

---

# Arquitetura

```text
Video Processing Pipeline/
│
├── video_processor.py
├── video_cut.py
├── video_caption.py
├── video_visualizer.py
│
├── config.json
├── tasks.json
├── tasks_visualizer.json
├── fila.txt
├── cortes.csv
│
├── visualizer_presets/
│   ├── retro.json
│   ├── retro_bars.json
│   ├── dense_bars.json
│   ├── cyberpunk_mix.json
│   ├── waveform.json
│   ├── horizontal_lines.json
│   ├── stereo_scope.json
│   ├── pulse.json
│   ├── retro_lines.json
│   ├── dense_lines.json
│   ├── cyberpunk_lines.json
│   ├── retro_scope_lines.json
│   └── neon_ring.json
│
├── src/
│   ├── visualizer_bars.py
│   ├── visualizer_waveform.py
│   ├── visualizer_horizontal_lines.py
│   ├── visualizer_stereo_scope.py
│   ├── visualizer_pulse.py
│   ├── visualizer_line_spectrum.py
│   └── visualizer_neon_ring.py
│
├── test/
│   └── test_video_visualizer.py
│
├── output/
│   ├── processor/
│   ├── cuts/
│   ├── caption/
│   └── visualizer/
```

---

# Módulos

## video_processor.py

Processa vídeos com encode configurável.

- Resize automático
- Controle de FPS
- Controle de bitrate
- Áudio opcional
- Fila (.txt)
- Paralelismo (multi-core)
- Retry automático
- Logs de sucesso/erro

---

## video_cut.py

Corta vídeos via CSV.

### fast

```text
-c copy
```

- rápido
- sem perda
- não frame-perfect

---

### precise (PROFISSIONAL)

```text
HEVC (H.265)
Main10 (10-bit)
CBR real (ex: 85000k)
preset veryslow
```

- frame-perfect
- qualidade máxima
- compatível com DaVinci
- encode profissional

---

## video_caption.py

Adiciona hook textual no vídeo.

- Texto responsivo
- Highlight de palavra
- Stroke + shadow
- Fade in/out
- Mantém codec original
- Mantém áudio original

---

## video_visualizer.py

Sistema modular de visualizers FFT e audio reactive.

### Recursos

- Pipeline por tasks JSON
- Presets independentes
- Visualizers modulares
- Nome de saída customizável
- Execução manual
- Glow neon
- FFT spectrum
- Waveform
- Stereo scope
- Pulse
- Line spectrum
- Neon ring
- Output automático
- Compatível com FFmpeg

---

# Fluxo do video_visualizer

```text
tasks_visualizer.json
        ↓
load_preset()
        ↓
get_video_metadata()
        ↓
resolver visualizer
        ↓
renderer.render()
        ↓
ffmpeg
        ↓
output final
```

---

# Sistema VISUALIZERS

```python
VISUALIZERS = {
    "bars": VisualizerBars,
    "waveform": VisualizerWaveform,
    "pulse": VisualizerPulse,
    "line_spectrum": VisualizerLineSpectrum,
    "neon_ring": VisualizerNeonRing
}
```

---

# Visualizers disponíveis

## 1. Retro Bars

Preset:

```text
retro.json
```

Características:

- barras FFT
- verde neon
- glow retrô

---

## 2. Dense Bars

Preset:

```text
dense_bars.json
```

Características:

- barras densas
- FFT compacta

---

## 3. Cyberpunk Mix

Preset:

```text
cyberpunk_mix.json
```

Características:

- glow cyan
- visual cyberpunk

---

## 4. Waveform

Preset:

```text
waveform.json
```

Características:

- waveform clássico

---

## 5. Horizontal Lines

Preset:

```text
horizontal_lines.json
```

Características:

- waveform horizontal
- linhas centralizadas

---

## 6. Stereo Scope

Preset:

```text
stereo_scope.json
```

Características:

- vectorscope estéreo
- análise L/R

---

## 7. Pulse

Preset:

```text
pulse.json
```

Características:

- pulse reactive
- glow pulsante

---

## 8. Line Spectrum

Renderizador:

```text
visualizer_line_spectrum.py
```

Presets:

```text
retro_lines.json
dense_lines.json
cyberpunk_lines.json
retro_scope_lines.json
```

Características:

- FFT técnico
- spectrum analyzer
- linhas contínuas
- glow leve
- estilo científico

Diferença principal:

```text
bars = colunas FFT
line_spectrum = traço contínuo FFT
```

---

## 9. Neon Ring

Renderizador:

```text
visualizer_neon_ring.py
```

Preset:

```text
neon_ring.json
```

Características:

- glow circular
- visual synthwave
- neon reactive

---

# Configuração (`config.json`)

## Estrutura

* `video_processor`
* `video_cut`
* `video_caption`
* `video_visualizer`

---

## Exemplo completo

```json
{
    "video_processor": {
        "paths": {
            "output": "output/processor"
        },
        "video": {
            "res_max": 720,
            "fps": 12,
            "bitrate": "2000k",
            "preset": "medium",
            "pix_fmt": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "mute_video": false
        },
        "file": {
            "suffix": "_processed"
        },
        "queue": {
            "success": "queue_success.txt",
            "error": "queue_error.txt",
            "max_retries": 2,
            "retry_delay": 3,
            "max_workers": 2
        },
        "audio": {
            "enabled": true,
            "codec": "mp3",
            "bitrate": "192k",
            "extension": "mp3"
        },
        "transcription": {
            "enabled": true,
            "model": "base"
        },
        "subtitle": {
            "enabled": true,
            "format": "srt"
        }
    },

    "video_cut": {
        "paths": {
            "output": "output/cuts"
        },
        "mode": "fast",
        "precise": {
            "bitrate": "85000k",
            "preset": "veryslow",
            "profile": "main10",
            "level": "5.1",
            "audio_codec": "aac",
            "audio_bitrate": "192k"
        }
    },

    "video_caption": {
        "paths": {
            "output": "output/caption"
        },
        "video": {
            "threads": 4,
            "logger": null
        },
        "hook": {
            "start_time": 0.5,
            "duration": 5.0,
            "pos_y_percent": 0.20,
            "width_percent": 0.80,
            "fade_in_duration": 0.3,
            "fade_out_duration": 0.5
        },
        "text_style": {
            "font": "Bebas-Neue",
            "font_size": 90,
            "show_stroke": true,
            "stroke_width": 1.5,
            "show_shadow": true,
            "shadow_opacity": 0.6,
            "shadow_offset_x": 5,
            "shadow_offset_y": 5,
            "interline": -5,
            "color_default": "yellow",
            "color_highlight_text": "white",
            "color_highlight_word": "yellow"
        }
    },

    "video_visualizer": {

        "paths": {
            "output": "output/visualizer"
        },

        "video": {
            "fps": 24,
            "codec": "libx264",
            "pix_fmt": "yuv420p"
        }
    }
}
```

---

# Tasks Visualizer

Arquivo:

```text
tasks_visualizer.json
```

## Exemplo

```json
[
    {
        "input": "test/input.mp4",
        "preset": "visualizer_presets/retro.json",
        "output": "input_retro.mp4"
    },

    {
        "input": "test/input.mp4",
        "preset": "visualizer_presets/cyberpunk_lines.json",
        "output": "input_cyberpunk_lines.mp4"
    }
]
```

---

# Uso

## Processar vídeo

```bash
python video_processor.py video.mp4
```

---

## Processar fila

```bash
python video_processor.py fila.txt
```

---

## Cortar vídeo

CSV:

```text
00:05,00:10,Intro
00:10,00:20,Part1
```

```bash
python video_cut.py cortes.csv video.mp4
```

---

## Caption

tasks.json:

```json
[
    {
        "input": "video.mp4",
        "text": "How to automate videos with python",
        "highlight": "python",
        "output": "video_final.mp4"
    }
]
```

```bash
python video_caption.py
```

---

## Visualizer via pipeline

```bash
python video_visualizer.py tasks_visualizer.json
```

---

## Visualizer manual

```bash
python video_visualizer.py input.mp4 visualizer_presets/retro.json
```

---

## Visualizer manual com output custom

```bash
python video_visualizer.py input.mp4 visualizer_presets/retro.json --output final.mp4
```

---

# Sistema de Output

## Output automático

Caso não seja informado:

```json
"output"
```

o sistema gera automaticamente:

```text
input_overlay.mp4
```

---

## Output customizado

```json
{
    "input": "video.mp4",
    "preset": "visualizer_presets/retro.json",
    "output": "video_final.mp4"
}
```

---

# Sistema de Glow

Utiliza:

- gblur
- colorchannelmixer
- blend

Exemplo:

```json
{
    "glow_blur": 2,
    "glow_opacity": 0.20,
    "blend_mode": "lighten"
}
```

---

# Cores

```json
{
    "glow_color": {
        "r": 0.0,
        "g": 1.0,
        "b": 0.0
    }
}
```

---

# Saídas

```text
output/
├── processor/
│   ├── video_processed.mp4
│   ├── queue_success.txt
│   └── queue_error.txt
│
├── cuts/
│   ├── video_Intro.mp4
│
├── caption/
│   ├── video_final.mp4
│
└── visualizer/
    ├── input_retro.mp4
    ├── input_waveform.mp4
    ├── input_pulse.mp4
    ├── input_lines.mp4
```

---

# Paralelismo

```json
"max_workers": 2
```

Recomendação:

| CPU     | Workers |
| ------- | ------- |
| 4 cores | 1–2     |
| 8 cores | 2–4     |

---

# Testes

Arquivo:

```text
test/test_video_visualizer.py
```

Cobertura:

- build_output_path
- load_preset
- get_video_metadata
- process_task
- visualizer inválido
- run_pipeline
- run_manual
- argparse
- output automático
- output custom
- mocks FFmpeg
- mocks renderers

Executar:

```bash
cd test

python -m pytest test_video_visualizer.py -v
```

---

# Troubleshooting

## Visualizer inválido

Causa:
- renderer não registrado
- nome incorreto no preset

---

## FFprobe error

Causa:
- FFprobe não instalado
- vídeo inexistente

---

## Barras cinzas

Causa:
- glow exagerado
- blend incorreto

Correção:
- reduzir blur
- reduzir opacity

---

# Requisitos

```bash
pip install moviepy imageio-ffmpeg openai-whisper pytest
```

Necessário:

- FFmpeg
- FFprobe
- Python 3.10+
- MoviePy precisa de backend de render (Pillow ou ImageMagick)