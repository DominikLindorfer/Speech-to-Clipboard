# App configuration
from collections import deque

LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
}
fs = 16000
recording = False
audio_data = []
audio_thread = None
selected_language = "en"
tray_icon_ref = None
status_window = None
current_hotkey = "F4"
clipboard_history = deque(maxlen=10)
