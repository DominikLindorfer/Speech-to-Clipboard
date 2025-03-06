import sounddevice as sd
import numpy as np
import whisper
import pyperclip
import keyboard
import threading
import pystray
from PIL import Image, ImageDraw
import sys, os
import time
from collections import deque
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# App configuration
LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
}
clipboard_history = deque(maxlen=10)
fs = 16000
recording = False
audio_data = []
audio_thread = None
selected_language = "en"
tray_icon_ref = None
status_window = None

if getattr(sys, "frozen", False):
    # Running from PyInstaller exe
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(__file__)

# explicitly load the model
model_path = os.path.join(application_path, "small.pt")
model = whisper.load_model(model_path)


# Create a nice tray icon
def create_icon():
    icon = Image.new("RGB", (64, 64), color="white")
    d = ImageDraw.Draw(icon)
    d.ellipse([8, 8, 56, 56], fill="#0080ff")
    d.text((20, 22), "🎙️", fill="white")
    return icon


# Status Console (GUI)
class StatusWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Status Console")
        self.root.geometry("500x300")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        # Set custom icon (ensure mic.ico is in the same folder!)
        icon_path = os.path.join(os.path.dirname(__file__), "mic.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # ScrolledText widget with black background
        self.text_area = ScrolledText(
            self.root,
            state="disabled",
            wrap="word",
            bg="black",
            fg="white",  # Default text color
            font=("Consolas", 11),
        )
        self.text_area.pack(expand=True, fill="both")

        # Explicit color tags (foreground clearly set)
        self.text_area.tag_config("info", foreground="white")
        self.text_area.tag_config("record", foreground="#00ff00")  # Bright green
        self.text_area.tag_config("stop", foreground="#ff9900")  # Orange
        self.text_area.tag_config("transcribe", foreground="#00ccff")  # Cyan
        self.text_area.tag_config("success", foreground="#33ff33")  # Bright green
        self.text_area.tag_config("language", foreground="#ff66ff")  # Pink
        self.text_area.tag_config("clipboard", foreground="#ffff00")  # Yellow
        self.text_area.tag_config("error", foreground="#ff3333")  # Bright red

    def write(self, message, tag="info"):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, message + "\n", tag)
        self.text_area.see(tk.END)
        self.text_area.configure(state="disabled")

    def show(self):
        self.root.deiconify()

    def hide(self):
        self.root.withdraw()

    def toggle(self, icon=None, item=None):
        if self.root.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def run(self):
        self.root.mainloop()


def status(msg, tag="info"):
    print(msg)
    if status_window:
        status_window.write(msg, tag)


def record_audio():
    global audio_data
    audio_data = []
    with sd.InputStream(samplerate=fs, channels=1, dtype="float32") as stream:
        while recording:
            audio_chunk, _ = stream.read(fs // 10)
            audio_data.append(audio_chunk)


def transcribe_audio(icon=None):
    global audio_data, selected_language
    status("🔄 Transcribing audio...", tag="transcribe")
    audio_np = np.concatenate(audio_data, axis=0).flatten()
    result = model.transcribe(audio_np, language=selected_language)
    text = result["text"].strip()
    pyperclip.copy(text)
    clipboard_history.appendleft(text)

    notification_text = text if len(text) <= 255 else text[:252] + "..."
    if icon:
        icon.notify(notification_text, "Copied to Clipboard")

    status(f"✅ Transcribed ({selected_language}): {text}", tag="success")


def start_recording(event):
    global recording, audio_thread
    if not recording:
        recording = True
        status("🎙️ Recording started...", tag="record")
        audio_thread = threading.Thread(target=record_audio)
        audio_thread.start()


def stop_recording(event):
    global recording
    if recording:
        recording = False
        audio_thread.join()
        status("⏹️ Recording stopped.", tag="stop")
        time.sleep(1)
        threading.Thread(target=transcribe_audio, args=(tray_icon_ref,)).start()


def set_language(icon, item):
    global selected_language
    selected_language = LANGUAGES[item.text]
    status(f"🌐 Language set to: {item.text}", tag="language")


def copy_history_item(icon, full_text):
    pyperclip.copy(full_text)
    icon.notify(full_text[:255], "Recopied to Clipboard")
    status(f"📋 Copied to clipboard: {full_text}", tag="clipboard")


def quit_app(icon, item):
    icon.stop()
    sys.exit()


def build_menu():
    language_items = [
        pystray.MenuItem(
            lang,
            set_language,
            checked=lambda item, code=code: selected_language == code,
            radio=True,
        )
        for lang, code in LANGUAGES.items()
    ]

    def make_copy_action(full_text):
        return lambda icon, item: copy_history_item(icon, full_text)

    history_items = [
        pystray.MenuItem(
            text if len(text) <= 40 else text[:40] + "...", make_copy_action(text)
        )
        for text in clipboard_history
    ] or [pystray.MenuItem("(Empty)", None, enabled=False)]

    return pystray.Menu(
        pystray.MenuItem("Languages", pystray.Menu(*language_items)),
        pystray.MenuItem("History", pystray.Menu(*history_items)),
        pystray.MenuItem("Show Console", status_window.toggle),
        pystray.MenuItem("Quit", quit_app),
    )


def tray_icon():
    global tray_icon_ref
    icon = pystray.Icon(
        "Whisper STT", create_icon(), "Whisper Speech-to-Clipboard", menu=build_menu()
    )
    tray_icon_ref = icon

    def refresh(icon):
        while True:
            icon.menu = build_menu()
            time.sleep(2)

    threading.Thread(target=refresh, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    status_window = StatusWindow()
    status_window.hide()

    # Run tray icon in background thread
    threading.Thread(target=tray_icon, daemon=True).start()

    # Setup hotkeys in background threads
    keyboard.on_press_key("f9", start_recording)
    keyboard.on_release_key("f9", stop_recording)

    status("👉 Hold F9 to record. Release to transcribe.")

    # Run Tkinter GUI (main thread)
    status_window.run()
