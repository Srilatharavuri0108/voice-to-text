# 🎙️ Speech-to-Text Converter Web Application

[![Deploy with Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=Srilatharavuri0108/voice-to-text&branch=main&mainModule=app.py)

A complete, production-ready **Speech-to-Text Web Application** built with **Python**, **Streamlit**, **SpeechRecognition**, **PyAudio**, and the **Google Web Speech Recognition API**.

---

## 🌟 Key Features

1. **Modern, Responsive Dashboard UI**:
   - Sleek glassmorphism theme with gradient headers and responsive metric cards.
   - Dynamic pulsing badges indicating recording state (`IDLE`, `🔴 RECORDING`, `⏳ PROCESSING`, `✅ SUCCESS`).
   - Clean, professional typography and dark mode color scheme.

2. **Dual-Engine Audio Capture**:
   - **Live Hardware Microphone (PyAudio)**: Dedicated **🔴 Start Recording** and **⏹️ Stop Recording** buttons using a background Python worker thread for zero-latency audio buffering.
   - **Web Browser Microphone (`st.audio_input`)**: Native HTML5 Web Audio API capturing speech directly through the browser without needing local C-audio drivers.
   - **Audio File Upload**: Upload pre-recorded audio files (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`).

3. **High-Accuracy Speech-to-Text Engine**:
   - Powered by the **Google Web Speech Recognition API** via `SpeechRecognition`.
   - **Adaptive Ambient Noise Calibration**: Automatically samples room noise to cancel steady hums, fans, and microphone hiss.
   - **Configurable Speech Energy Threshold**: Fine-tune sensitivity for soft whispers or loud rooms.

4. **Multi-Language Support**:
   - English (US, UK, India, Australia, Canada).
   - Spanish, French, German, Hindi, Telugu, Tamil, Japanese, Mandarin Chinese.

5. **Action Toolbar & Output Metrics**:
   - Large editable text area displaying transcribed speech.
   - Real-time metrics: **Word Count**, **Character Count**, **Audio Duration (s)**, and **API Latency (s)**.
   - **📋 Copy Text**: One-click clipboard copy with instant toast confirmation.
   - **🗑️ Clear Text**: Clears output and resets audio buffers.
   - **💾 Download .TXT**: Export transcription as a clean text file.
   - **📊 Download JSON Report**: Exports full metadata, timestamps, audio duration, and language tags.
   - **🎧 Audio Playback**: Listen to the recorded audio to verify clarity.
   - **📜 Session Audit History**: Keeps a chronological log of all transcriptions during the session.

6. **Robust Error Handling**:
   - Microphone permission / hardware errors (`OSError`, missing mic devices).
   - Inaudible / unclear speech (`sr.UnknownValueError`).
   - Network connectivity / API timeout errors (`sr.RequestError`).

---

## 🏗️ Architecture & Component Flow

```
+-----------------------------------------------------------------------------------+
|                                 USER INTERFACE                                    |
|                              (Streamlit Frontend)                                 |
+-----------------------------------------------------------------------------------+
        |                                   |                              |
        v                                   v                              v
[Live Hardware Mic]               [Web Browser Mic]             [File Uploader]
  (PyAudio Worker)                (st.audio_input)             (.wav / .mp3 / .m4a)
        |                                   |                              |
        v                                   v                              v
+-----------------------------------------------------------------------------------+
|                             AUDIO PROCESSING BUFFER                               |
|              - 16,000 Hz Sampling Rate, 16-bit Mono PCM WAV Stream                |
|              - In-Memory Byte Stream (io.BytesIO)                                 |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                        SPEECH RECOGNITION PIPELINE                                |
|              - Ambient Noise Calibration (adjust_for_ambient_noise)               |
|              - Dynamic Energy Threshold Adjustment                                |
|              - Language Locale Dispatch (e.g. en-US, en-IN, es-ES)                |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                     GOOGLE WEB SPEECH RECOGNITION API                             |
|          Cloud Speech-to-Text Recognition via Secure HTTPS REST Endpoint          |
+-----------------------------------------------------------------------------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
            [Success Payload]                         [Exception Handler]
                   |                                         |
                   v                                         v
   - Formatted Text Output                   - sr.UnknownValueError (Unclear Speech)
   - Real-time Metrics Calculation           - sr.RequestError (No Internet)
   - Session History Append                  - PyAudio/OSError (Hardware Denied)
   - Clipboard / File Export                 - Friendly Guidance & Diagnostic Alerts
```

---

## 📁 Project Structure

```
speech_to_text_app/
│
├── app.py                      # Main application entry point (UI + Audio Engine)
├── requirements.txt            # Project dependencies
├── README.md                   # Complete documentation & interview guide
└── .streamlit/
    ├── config.toml             # Streamlit server & theme configuration
    └── credentials.toml        # Headless initialization settings
```

---

## 🚀 Step-by-Step Installation & Setup on Windows

### 1. Prerequisites
- **Windows 10 or 11**
- **Python 3.10+** (Tested and verified on **Python 3.13.2**)
- Working microphone (built-in or USB headset)
- Active internet connection (for Google Speech Recognition)

### 2. Verify Windows Microphone Permissions
Ensure Windows permits desktop apps to access your microphone:
1. Open **Windows Settings** (`Win + I`).
2. Navigate to **Privacy & Security** > **Microphone**.
3. Toggle **Microphone access** to **ON**.
4. Scroll down and ensure **Let desktop apps access your microphone** is turned **ON**.

### 3. Open PowerShell or Command Prompt
Navigate to your project directory:
```powershell
cd C:\Users\srila\OneDrive\Desktop\speech_to_text_app
```

### 4. Install Dependencies
Run:
```powershell
pip install -r requirements.txt
```
*Note for Python 3.13 on Windows:* `PyAudio` 0.2.14 includes official pre-compiled wheels on PyPI, so no C++ build tools are required!

### 5. Run the Application
Launch the Streamlit web server:
```powershell
streamlit run app.py
```
Or if running directly with a specific Python executable:
```powershell
python -m streamlit run app.py
```

The app will automatically launch in your default web browser at:
👉 **`http://localhost:8501`**

---

## 🎯 How to Use the Application

1. **Select Recognition Language**: In the left sidebar, choose your desired language (default is **English (US)**).
2. **Choose Audio Capture Mode**:
   - **Option A (Hardware Mic)**: Switch to the *Live Hardware Microphone* tab. Click **🔴 Start Recording**, speak into your microphone, then click **⏹️ Stop Recording**.
   - **Option B (Browser Mic)**: Switch to the *Web Browser Microphone* tab. Click the red record icon in the widget, speak, click stop, then click **✨ Transcribe Browser Recording**.
   - **Option C (File Upload)**: Switch to the *Upload Audio File* tab, select a WAV or MP3 recording, and click **🚀 Transcribe Uploaded File**.
3. **Review Transcribed Output**: The text will appear in the large text area along with word count, character count, and audio metrics.
4. **Export**: Click **📋 Copy Text** to copy to clipboard or **💾 Download .TXT** to save the transcript locally.

---

## 💼 Demonstration Guide for Python Full Stack Developer Interview

When demonstrating this project to interviewers or hiring managers, structure your presentation using this technical framework:

### 1. The Elevator Pitch (30 seconds)
> *"I built a real-time Speech-to-Text web application using Python, Streamlit, and the Google Speech Recognition API. It features multi-modal audio capture—including a thread-safe PyAudio hardware recorder and an HTML5 browser-based recorder—adaptive noise cancellation, real-time audio analytics, multi-language support, and comprehensive error resilience."*

### 2. Architecture & Design Decisions Walkthrough

#### A. Concurrency & Thread-Safe Audio Ingestion
- **Interviewer Question**: *"How did you implement the Start and Stop recording buttons in Streamlit without blocking the UI?"*
- **Answer**:
  > *"Streamlit executes its script top-to-bottom upon every user interaction. A naive recording loop with `stream.read()` would freeze the main thread and prevent the Stop button from registering. To solve this, I designed `PyAudioThreadRecorder` as a decoupled class. When the user clicks 'Start Recording', audio frames are acquired continuously inside a daemon worker thread. When the user clicks 'Stop Recording', the main thread signals the worker to terminate, joins the thread with a timeout, and packages the collected PCM chunks into a standardized 16-bit mono 16 kHz WAV stream in an in-memory `io.BytesIO` buffer."*

#### B. Browser Web Audio vs. Server Hardware Audio
- **Interviewer Question**: *"What happens if this app is deployed to the cloud (e.g., AWS EC2 or Streamlit Community Cloud)? Won't PyAudio fail?"*
- **Answer**:
  > *"Exactly. In a local desktop environment, PyAudio accesses the host machine's sound card directly. But in a containerized cloud deployment (Docker/Kubernetes), the container has no physical sound card. That is why I engineered dual-modality: Tab 2 uses Streamlit's native `st.audio_input`, which uses the browser's Web Audio API to record audio on the client's device and transmits the WAV bytes over WebSocket to the server. This guarantees 100% cloud compatibility while preserving low-latency local recording."*

#### C. Handling Background Noise and Speech Variances
- **Interviewer Question**: *"How do you handle ambient background noise or soft speech?"*
- **Answer**:
  > *"Before passing the audio to the transcription engine, the pipeline invokes `recognizer.adjust_for_ambient_noise(source, duration=...)` which computes the acoustic energy floor of the environment to dynamically calibrate `energy_threshold`. Soft whispers or louder rooms can also be manually tuned via the sidebar slider."*

#### D. Production Error Handling Strategy
- **Interviewer Question**: *"What happens if the user has no internet or speaks unintelligibly?"*
- **Answer**:
  > *"The speech processing service wraps every API invocation in granular try/except blocks:
  > - `sr.UnknownValueError`: Raised when speech is unintelligible. The UI informs the user gently with troubleshooting suggestions rather than throwing an unhandled exception.
  > - `sr.RequestError`: Raised when the network socket drops or the API is unreachable. The UI displays an actionable network error message.
  > - `OSError` / Windows Audio Driver errors: Caught during device initialization with guidance to check Windows privacy permissions."*

---

## 🛠️ Tech Stack Reference

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | Streamlit 1.66+ | Reactive web dashboard, widgets, session management |
| **Core Language** | Python 3.13 | Application logic, threading, I/O handling |
| **Audio Ingestion** | PyAudio / sounddevice | Hardware microphone stream capture |
| **Client Audio** | HTML5 Web Audio API | In-browser client-side microphone capture |
| **STT Engine** | SpeechRecognition | Audio frame parsing, noise calibration, API dispatch |
| **Recognition API** | Google Web Speech API | High-accuracy neural speech-to-text conversion |
| **Audio Processing** | Wave & In-Memory BytesIO | Non-blocking PCM WAV compilation |
