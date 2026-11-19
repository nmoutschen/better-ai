import os
import tempfile
import wave

from peaks import peak_dbfs


def recording(peak):
    path = os.path.join(tempfile.mkdtemp(), "tone.wav")
    with wave.open(path, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        samples = [0, peak // 3, -peak, peak // 2, 0]
        audio.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return path


# 20 * log10(22767 / 32768) = -3.16; 20 * log10(16384 / 32768) = -6.02; 29000 gives -1.06.
assert peak_dbfs(recording(22767)) == -3.2, peak_dbfs(recording(22767))
assert peak_dbfs(recording(16384)) == -6.0, peak_dbfs(recording(16384))
assert peak_dbfs(recording(29000)) == -1.1, peak_dbfs(recording(29000))
