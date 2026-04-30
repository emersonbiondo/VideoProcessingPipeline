# Video Processing Pipeline

Pipeline modular em Python para processamento completo de vídeo:

* Encode e compressão (MoviePy)
* Corte (FFmpeg – fast e precise)
* Caption com hook + highlight (MoviePy)
* Processamento em lote (queue)
* Execução paralela
* Retry automático
* Encode profissional (HEVC Main10 CBR)

---

# Arquitetura

```text
Video Processing Pipeline/
│
├── video_processor.py    encode / fila
├── video_cut.py          corte via CSV
├── video_caption.py      hook + highlight
├── config.json          ️ config central
├── tasks.json            tarefas caption
├── fila.txt              lista processor
├── cortes.csv            lista cortes
│
├── output/
│   ├── processor/
│   ├── cuts/
│   └── caption/
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

# Requisitos

```bash
pip install moviepy imageio-ffmpeg openai-whisper
```

IMPORTANTE:

* Fontes devem estar instaladas no sistema
* MoviePy precisa de backend de render (Pillow ou ImageMagick)

---

# Configuração (`config.json`)

## Estrutura

* `video_processor`
* `video_cut`
* `video_caption`

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
    }
}
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
└── caption/
    ├── video_final.mp4
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

# Licença

Uso livre para automação e projetos próprios.
