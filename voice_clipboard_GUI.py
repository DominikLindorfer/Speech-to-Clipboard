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
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# App configuration
from config import (
    LANGUAGES,
    fs,
    recording,
    audio_data,
    audio_thread,
    selected_language,
    tray_icon_ref,
    status_window,
    current_hotkey,
    clipboard_history,
)

if getattr(sys, "frozen", False):
    # Running from PyInstaller exe
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(__file__)

# explicitly load the model
model_path = os.path.join(application_path, "small.pt")

# Try loading local model first, fallback to download if not found
try:
    if os.path.exists(model_path):
        print("✅ Loading Whisper model from local file...")
        model = whisper.load_model(model_path)
        print("✅ Loading model complete!")
    else:
        raise FileNotFoundError
except (FileNotFoundError, RuntimeError):
    print("⚠️ Local model not found, downloading from Whisper...")
    model = whisper.load_model("small")  # Whisper downloads automatically

stop_event = threading.Event()


# Create a nice tray icon
def create_icon():
    icon = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(icon)
    draw.rectangle((28, 15, 36, 40), fill=(255, 255, 255))
    draw.arc((22, 10, 42, 30), start=0, end=180, fill=(255, 255, 255))
    draw.rectangle((30, 40, 34, 50), fill=(255, 255, 255))
    draw.rectangle((20, 50, 44, 54), fill=(255, 255, 255))
    draw.text((20, 22), "🎙️", fill="white")

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
        notification_title = "Copied to Clipboard"
        icon.notify(notification_text, notification_title)

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
        time.sleep(1.5)
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
    stop_event.set()  # signal threads to stop
    keyboard.unhook_all()  # remove keyboard listeners
    icon.stop()  # stop the tray icon loop
    status("❌ Quitting application...", tag="error")

    # safely close the GUI in the main thread
    status_window.root.after(100, status_window.root.destroy)


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
        "Speech-to-Clipboard", create_icon(), "Speech-to-Clipboard", menu=build_menu()
    )
    tray_icon_ref = icon

    def refresh(icon, stop_event):
        while not stop_event.is_set():
            icon.menu = build_menu()
            time.sleep(2)

    threading.Thread(target=refresh, args=(icon, stop_event), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    stop_event = threading.Event()

    status_window = StatusWindow()
    status_window.hide()

    # Start tray icon thread
    tray_thread = threading.Thread(target=tray_icon, daemon=True)
    tray_thread.start()

    # Set up keyboard listeners
    keyboard.on_press_key(current_hotkey, start_recording)
    keyboard.on_release_key(current_hotkey, stop_recording)

    status(f"👉 Hold {current_hotkey} to record. Release to transcribe.")

    # Check periodically if we should exit
    def periodic_check():
        if stop_event.is_set():
            status_window.root.destroy()
        else:
            status_window.root.after(100, periodic_check)  # check every 100 ms

    status_window.root.after(100, periodic_check)

    # Run GUI loop (main thread)
    status_window.run()
