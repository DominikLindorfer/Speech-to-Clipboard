# Speech-to-Clipboard on Windows

> This project is perfect for developers diving into [vibe coding](https://en.wikipedia.org/wiki/Vibe_coding).

A minimalistic and hackable Python application for Windows that transcribes speech into text using OpenAI's Whisper model and copies it to your clipboard. Hold down a hotkey to record audio, and upon release, the transcribed text is automatically copied to your clipboard. The application runs in the system tray, allowing you to select the language, view transcription history, and access other features. 


![image](https://github.com/user-attachments/assets/cf51fd8b-ef8c-4620-9bd4-da06c4b56906)

## Features

- **Real-time Speech Recognition:** Transcribe audio to text using Whisper.
- **Clipboard Integration:** Automatically copies transcribed text to the clipboard.
- **Hotkey Activation:** Start and stop recording with a customizable hotkey (default is `F9`).
- **Multilingual Support:** Supports multiple languages selectable from the system tray.
- **System Tray Icon:** Access settings and history from the system tray.
- **Transcription History:** Keeps a history of recent transcriptions for quick access.
- **Status Console:** Optional GUI console to view status messages and logs.

## Installation

Download the latest release from the [Releases](https://github.com/yourusername/Speech-to-Clipboard/releases) page. Extract the contents of the ZIP file to a directory of your choice. Run the `Speech-to-Clipboard.exe` executable to start the application.

## Configuration

The application uses a `config.json` file for configuration settings.

```json config.json
{
    "AppConfig": {
        "fs": 16000,
        "recording": false,
        "selected_language": "en",
        "current_hotkey": "F9"
    },
    "Languages": {
        "English": "en",
        "German": "de",
        "Spanish": "es",
        "French": "fr",
        "Italian": "it"
    }
}
```

- **fs:** Sampling rate for audio recording.
- **recording:** Recording status (do not change manually).
- **selected_language:** Default language for transcription.
- **current_hotkey:** Hotkey for starting/stopping recording.

You can modify these settings as needed.

## Building from Source

### Clone the Repository

```bash
git clone https://github.com/yourusername/Speech-to-Clipboard.git
cd Speech-to-Clipboard
```

### Install Dependencies

Using `pipenv` (recommended):

```bash
pip install pipenv
pipenv install
```

Note: Whisper's small.pt is downloaded automatically upon first run.

### Building Executables

You can build standalone executables using `PyInstaller`. A batch script `build_clean.bat` is provided

```bash
build_clean.bat
```

## License
MIT
