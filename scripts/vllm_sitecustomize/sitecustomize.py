"""Runtime compatibility settings for trace-eval vLLM server processes."""

try:
    from PIL import ImageFile
except ImportError:
    ImageFile = None

if ImageFile is not None:
    # Some canonical benchmark artifacts contain valid pixels but omit the
    # trailing bytes Pillow expects. The generation client already enables
    # this setting; file:// transport requires the server to do the same.
    ImageFile.LOAD_TRUNCATED_IMAGES = True
