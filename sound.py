import math
import os
import struct
import tempfile
import wave

from PySide6.QtWidgets import QApplication

try:
    import winsound
except ImportError:
    winsound = None

CHIME_PATH = os.path.join(tempfile.gettempdir(), "pomodoro_chime.wav")
SOUND_CHOICES = {"none": "无", "system": "系统提示音", "chime": "内置叮声"}


def _generate_chime():
    if os.path.exists(CHIME_PATH):
        return
    rate = 44100
    frames = int(rate * 0.7)
    data = bytearray()
    for i in range(frames):
        t = i / rate
        envelope = math.exp(-7 * t)
        value = 0.5 * envelope * (
            math.sin(2 * math.pi * 880 * t) * 0.6
            + math.sin(2 * math.pi * 1318.5 * t) * 0.4
        )
        data += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))
    with wave.open(CHIME_PATH, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(data))


def play(choice):
    if choice == "none":
        return
    if choice == "system":
        QApplication.beep()
        return
    try:
        if winsound is None:
            QApplication.beep()
            return
        _generate_chime()
        winsound.PlaySound(CHIME_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        QApplication.beep()