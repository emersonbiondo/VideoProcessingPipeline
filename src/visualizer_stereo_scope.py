from src.base_visualizer import BaseVisualizer


class VisualizerStereoScope(BaseVisualizer):

    FILTER_TEMPLATE = (
        "avectorscope="
        "s={width}x{height}:"
        "mode=lissajous"
    )
