import sounddevice as sd
import numpy as np
import whisper
import pyperclip
import keyboard
import threading
import pystray
from PIL import Image
import sys

# Load Whisper model once at start (you can change the model size if needed)
model = whisper.load_model("small")

# Audio recording settings
fs = 16000
recording = False
audio_data = []
audio_thread = None

def record_audio():
    global audio_data
    audio_data = []
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
        while recording:
            audio_chunk, _ = stream.read(fs // 10)
            audio_data.append(audio_chunk)

def transcribe_audio():
    global audio_data
    audio_np = np.concatenate(audio_data, axis=0).flatten()
    result = model.transcribe(audio_np, language='en')  # Adjust language if desired
    text = result['text'].strip()
    pyperclip.copy(text)
    print("Transcribed Text:", text)

def start_recording(event):
    global recording, audio_thread
    if not recording:
        recording = True
        print("🎙️ Recording started...")
        audio_thread = threading.Thread(target=record_audio)
        audio_thread.start()

import time  # <-- add this import at the top

# --- keep everything else the same ---

def stop_recording(event):
    global recording
    if recording:
        recording = False
        audio_thread.join()
        
        print("⏹️ Recording stopped. Finalizing audio...")
        time.sleep(1)  # <-- Add short buffer (500ms) to ensure full audio capture

        print("🔄 Transcribing...")
        transcribe_audio()


def quit_app(icon, item):
    icon.stop()
    sys.exit()

# Tray icon setup
def tray_icon():
    image = Image.new('RGB', (64, 64), color=(0, 128, 255))
    icon = pystray.Icon("Whisper STT", image, "Whisper Speech-to-Clipboard", menu=pystray.Menu(
        pystray.MenuItem("Quit", quit_app)
    ))
    icon.run()

if __name__ == "__main__":
    print("👉 Press and hold F9 to record audio. Release F9 to transcribe.")

    # Explicitly register F9 press and release events
    keyboard.on_press_key('f9', start_recording)
    keyboard.on_release_key('f9', stop_recording)

    # Start tray icon thread
    tray_thread = threading.Thread(target=tray_icon, daemon=True)
    tray_thread.start()

    keyboard.wait()  # Keep script running indefinitely

