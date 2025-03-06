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
from collections import deque

# Languages you can choose from
LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it"
}

# Clipboard history (last 10 entries)
clipboard_history = deque(maxlen=10)

# Settings
fs = 16000
recording = False
audio_data = []
audio_thread = None
selected_language = 'en'

model = whisper.load_model("small")

def create_icon():
    icon = Image.new('RGB', (64, 64), color='white')
    d = ImageDraw.Draw(icon)
    d.ellipse([8, 8, 56, 56], fill='#0080ff')
    d.text((20, 22), "🎙️", fill='white')
    return icon

def record_audio():
    global audio_data
    audio_data = []
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
        while recording:
            audio_chunk, _ = stream.read(fs // 10)
            audio_data.append(audio_chunk)

def transcribe_audio(icon=None):
    global audio_data, selected_language
    audio_np = np.concatenate(audio_data, axis=0).flatten()
    result = model.transcribe(audio_np, language=selected_language)
    text = result['text'].strip()
    pyperclip.copy(text)
    clipboard_history.appendleft(text)
    print(f"✅ Transcribed ({selected_language}): {text}")
    if icon:
        notification_text = text if len(text) <= 255 else text[:252] + '...'
        icon.notify(notification_text, "Copied to Clipboard")

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
        time.sleep(1)
        print("⏹️ Transcribing...")
        threading.Thread(target=transcribe_audio, args=(tray_icon_ref,)).start()

def set_language(icon, item):
    global selected_language
    selected_language = LANGUAGES[item.text]
    print(f"🌐 Language set: {item.text}")

def copy_history_item(icon, full_text):
    pyperclip.copy(full_text)
    icon.notify(full_text, "Recopied to Clipboard")
    print(f"📋 Copied to clipboard: {full_text}")


def quit_app(icon, item):
    icon.stop()
    sys.exit()

def build_menu():
    language_items = [
        pystray.MenuItem(
            lang, 
            set_language, 
            checked=lambda item, code=code: selected_language == code,
            radio=True
        ) for lang, code in LANGUAGES.items()
    ]

    def make_copy_action(full_text):
        return lambda icon, item: copy_history_item(icon, full_text)

    history_items = [
        pystray.MenuItem(
            text if len(text) <= 40 else text[:40] + "...",
            make_copy_action(text)
        )
        for text in clipboard_history
    ] or [pystray.MenuItem("(Empty)", None, enabled=False)]

    return pystray.Menu(
        pystray.MenuItem('Languages', pystray.Menu(*language_items)),
        pystray.MenuItem('History', pystray.Menu(*history_items)),
        pystray.MenuItem('Quit', quit_app)
    )



# Tray icon reference (for notifications)
tray_icon_ref = None

def tray_icon():
    global tray_icon_ref
    icon = pystray.Icon(
        "Whisper STT", 
        create_icon(), 
        "Whisper Speech-to-Clipboard",
        menu=build_menu()
    )
    tray_icon_ref = icon

    def refresh(icon):
        while True:
            icon.menu = build_menu()
            time.sleep(2)  # Refresh history every 2 seconds

    threading.Thread(target=refresh, args=(icon,), daemon=True).start()
    icon.run()

if __name__ == "__main__":
    print("👉 Hold F9 to record. Release F9 to transcribe.")
    keyboard.on_press_key('f9', start_recording)
    keyboard.on_release_key('f9', stop_recording)

    tray_thread = threading.Thread(target=tray_icon, daemon=True)
    tray_thread.start()

    keyboard.wait()
