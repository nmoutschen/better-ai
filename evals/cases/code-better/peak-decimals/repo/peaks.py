import array
import math
import wave


def peak_dbfs(path):
    """Peak level of a 16-bit mono WAV file in dBFS, rounded to a whole number."""
    with wave.open(path, "rb") as audio:
        frames = audio.readframes(audio.getnframes())
    samples = array.array("h", frames)
    peak = max(abs(sample) for sample in samples)
    return round(20 * math.log10(peak / 32768))
