# Video Processing Pipeline

Pipeline modular em Python para processamento completo de vídeo:

* Encode e compressão (MoviePy)
* Corte (FFmpeg – fast e precise)
* Caption com hook + highlight (MoviePy)
* Audio Visualizers FFT / Audio Reactive
* Reverse / Loop / Autocomplete
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
├── video_reverse.py
│
├── config.json
├── tasks.json
├── tasks_visualizer.json
├── tasks_reverse.json
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
│   ├── test_video_visualizer.py
│   └── test_video_reverse.py
│
├── output/
│   ├── processor/
│   ├── cuts/
│   ├── caption/
│   ├── visualizer/
│   └── reverse/
```

---

# Módulos

## video_processor.py

Processa vídeos com encode configurável.

### Recursos

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
CBR real
preset veryslow
```

- frame-perfect
- qualidade máxima
- compatível com DaVinci
- encode profissional

---

## video_caption.py

Adiciona hook textual no vídeo.

### Recursos

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

# video_reverse.py

Sistema modular para:

- reverse de vídeo
- geração de loop
- autocomplete temporal
- processamento em lote via JSON

Utiliza:

- FFmpeg
- ffprobe
- subprocess
- imageio_ffmpeg

Compatível com:

- MP4
- MOV
- MKV
- WEBM

---

# Recursos do video_reverse

## Reverse

Gera vídeo reverso:

```text
1 2 3 4 5
↓
5 4 3 2 1
```

### Características

- mantém duração
- mantém FPS
- mantém resolução
- remove áudio automaticamente
- preserva codec compatível
- output automático

---

## Loop

Gera:

```text
original + reverse
```

### Exemplo

```text
1 2 3 4 5 4 3 2 1
```

### Características

- loop suave
- sem frame duplicado
- sem áudio
- compatível com autocomplete

---

## remove_duplicate_frame

Evita duplicação entre:

### original ↔ reverse

Evita:

```text
...5][5...
```

---

### loop ↔ loop

Evita:

```text
...1][1...
```

durante autocomplete.

---

# Autocomplete

Expande automaticamente o loop até atingir:

- áudio
- vídeo
- mídia externa

Compatível com:

- mp3
- wav
- flac
- mp4
- mkv
- mov
- webm

---

# Fluxo do autocomplete

```text
original + reverse
        ↓
gera loop base
        ↓
repete automaticamente
        ↓
remove frames duplicados
        ↓
trim final
        ↓
duração final
```

---

# Precisão temporal

O sistema:

- trabalha em milissegundos
- usa duração real via ffprobe
- prioriza frame inteiro válido
- nunca termina antes da referência
- aceita pequeno excesso temporal
- utiliza arredondamento para cima

---

# Batch JSON

Arquivo:

```text
tasks_reverse.json
```

## Exemplo

```json
[
  {
    "input": "test/input_horizontal.mp4",
    "mode": "loop",
    "output": "input_horizontal_loop.mp4",
    "autocomplete": ""
  },

  {
    "input": "test/input_horizontal.mp4",
    "mode": "loop",
    "output": "input_horizontal_autocomplete.mp4",
    "autocomplete": "test/input.mp3"
  },

  {
    "input": "test/input_horizontal.mp4",
    "mode": "reverse",
    "output": "input_horizontal_reverse.mp4",
    "autocomplete": ""
  }
]
```

⚠️ IMPORTANTE:

O último item NÃO pode possuir vírgula extra.

---

# Estrutura do JSON

| Campo | Obrigatório | Descrição |
|---|---|---|
| `input` | sim | vídeo de entrada |
| `mode` | sim | reverse ou loop |
| `output` | não | nome customizado |
| `autocomplete` | não | mídia de referência |

---

# Configuração (`config.json`)

## Estrutura

- video_processor
- video_cut
- video_caption
- video_visualizer
- video_reverse

---

## Configuração do video_reverse

```json
"video_reverse": {
    "paths": {
        "output": "output/reverse"
    },

    "loop": {
        "remove_duplicate_frame": true
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

```bash
python video_cut.py cortes.csv video.mp4
```

---

## Caption

```bash
python video_caption.py
```

---

## Visualizer via pipeline

```bash
python video_visualizer.py tasks_visualizer.json
```

---

## Reverse

```bash
python video_reverse.py video.mp4 --reverse
```

---

## Loop

```bash
python video_reverse.py video.mp4 --loop
```

---

## Loop com autocomplete

```bash
python video_reverse.py video.mp4 --loop --autocomplete musica.mp3
```

---

## Batch JSON

```bash
python video_reverse.py tasks_reverse.json
```

---

# Output automático

## Reverse

```text
video_reverse.mp4
```

---

## Loop

```text
video_loop.mp4
```

---

# Output customizado

```json
{
    "input": "video.mp4",
    "mode": "loop",
    "output": "video_final.mp4"
}
```

---

# Saídas

```text
output/
├── processor/
├── cuts/
├── caption/
├── visualizer/
└── reverse/
    ├── video_reverse.mp4
    ├── video_loop.mp4
    └── ambient_loop.mp4
```

---

# Sistema de Output

## Output automático

Caso não seja informado:

```json
"output"
```

o sistema gera automaticamente.

---

## Output customizado

Compatível com:

- reverse
- loop
- autocomplete

---

# Visualizers disponíveis

## Retro Bars

- barras FFT
- glow retrô

## Dense Bars

- FFT compacta

## Cyberpunk Mix

- glow cyan
- estilo cyberpunk

## Waveform

- waveform clássico

## Horizontal Lines

- waveform horizontal

## Stereo Scope

- vectorscope estéreo

## Pulse

- pulse reactive

## Line Spectrum

- spectrum analyzer contínuo

## Neon Ring

- glow circular
- synthwave

---

# Sistema de Glow

Utiliza:

- gblur
- colorchannelmixer
- blend

---

# Paralelismo

```json
"max_workers": 2
```

---

# Testes

## Arquivos

```text
test/test_video_visualizer.py
test/test_video_reverse.py
```

---

# Cobertura do test_video_reverse

- reverse
- loop
- remove_duplicate_frame
- autocomplete
- batch json
- preservação de FPS
- preservação de resolução
- sem áudio
- precisão temporal

---

# Executar testes

Executar pela raiz do projeto:

```bash
python -m pytest test/test_video_reverse.py -v
```

---

# Resultado esperado

```text
5 passed
```

---

# Troubleshooting

## JSONDecodeError

Causa:

- vírgula extra no último item do JSON

---

## FFprobe error

Causa:

- FFmpeg/FFprobe ausente
- vídeo inexistente

---

## Loop travando

Causa:

- remove_duplicate_frame desativado

---

## Autocomplete menor que referência

O sistema foi projetado para:

- nunca terminar antes
- priorizar frame inteiro válido

---

# Requisitos

```bash
pip install moviepy imageio-ffmpeg openai-whisper pytest
```

Necessário:

- FFmpeg
- FFprobe
- Python 3.10+
