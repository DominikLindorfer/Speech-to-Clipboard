import sounddevice as sd
import numpy as np
import whisper
import pyperclip
import keyboard
import threading
import pystray
from PIL import Image, ImageDraw
import sys
import time

# Available languages (add more if needed)
LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it"
}

# Global settings
fs = 16000
recording = False
audio_data = []
audio_thread = None
selected_language = 'en'  # Default language

# Load Whisper model once
model = whisper.load_model("small")

# Tray icon generation (a nicer icon)
def create_icon():
    icon = Image.new('RGB', (64, 64), color='white')
    d = ImageDraw.Draw(icon)
    d.ellipse([8, 8, 56, 56], fill='#0080ff')  # Blue circle
    d.text((20, 22), "🎙️", fill='white')
    return icon

def record_audio():
    global audio_data
    audio_data = []
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
        while recording:
            audio_chunk, _ = stream.read(fs // 10)
            audio_data.append(audio_chunk)

def transcribe_audio():
    global audio_data, selected_language
    audio_np = np.concatenate(audio_data, axis=0).flatten()
    result = model.transcribe(audio_np, language=selected_language)
    text = result['text'].strip()
    pyperclip.copy(text)
    print(f"✅ Transcribed ({selected_language}): {text}")

def start_recording(event):
    global recording, audio_thread
    if not recording:
        recording = True
        print("🎙️ Recording...")
        audio_thread = threading.Thread(target=record_audio)
        audio_thread.start()

def stop_recording(event):
    global recording
    if recording:
        recording = False
        audio_thread.join()
        time.sleep(0.5)  # buffer to capture final audio
        print("⏹️ Stopped recording, transcribing...")
        threading.Thread(target=transcribe_audio).start()

# Tray menu actions
def set_language(icon, item):
    global selected_language
    selected_language = LANGUAGES[item.text]
    print(f"🌐 Language set to: {item.text}")

def quit_app(icon, item):
    icon.stop()
    sys.exit()

def build_menu():
    language_items = [
        pystray.MenuItem(
            lang, 
            set_language, 
            checked=lambda item, lang_code=code: selected_language == lang_code,
            radio=True
        ) 
        for lang, code in LANGUAGES.items()
    ]
    return pystray.Menu(
        pystray.MenuItem('Languages', pystray.Menu(*language_items)),
        pystray.MenuItem('Quit', quit_app)
    )

def tray_icon():
    icon = pystray.Icon(
        "Whisper STT", 
        create_icon(), 
        "Whisper Speech-to-Clipboard",
        build_menu()
    )
    icon.run()

if __name__ == "__main__":
    print("👉 Hold F9 to record. Release to transcribe & copy to clipboard.")
    keyboard.on_press_key('f9', start_recording)
    keyboard.on_release_key('f9', stop_recording)

    tray_thread = threading.Thread(target=tray_icon, daemon=True)
    tray_thread.start()

    keyboard.wait()
