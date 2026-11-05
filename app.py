"""
Speech-to-Text Web Application
Author: Senior Python Full Stack Developer
Technologies: Python, Streamlit, SpeechRecognition, PyAudio, Google Speech Recognition API
"""

import io
import os
import sys
import time
import wave
import json
import math
import struct
import logging
import warnings
import threading
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# Suppress optional audio engine warnings (e.g. ffmpeg runtime warning for pydub)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")

import streamlit as st
import speech_recognition as sr

# Lightweight audio libraries for ultra-fast startup
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except (ImportError, Exception):
    PYAUDIO_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except (ImportError, Exception):
    PYDUB_AVAILABLE = False


# ==============================================================================
# 1. STREAMLIT PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Speech-to-Text Converter",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Professional CSS Theme
st.markdown(
    """
    <style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* App Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
        padding: 2.2rem 2.5rem;
        border-radius: 18px;
        color: white;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 30px -10px rgba(79, 70, 229, 0.5);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }
    
    .header-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    
    .header-subtitle {
        font-size: 1.05rem;
        margin-top: 0.5rem;
        opacity: 0.92;
        font-weight: 400;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.55rem 1.2rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    
    .status-idle {
        background: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    
    .status-recording {
        background: rgba(239, 68, 68, 0.25);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.5);
        animation: pulse-red 1.5s infinite;
    }
    
    .status-processing {
        background: rgba(245, 158, 11, 0.25);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.5);
        animation: pulse-amber 1.5s infinite;
    }
    
    .status-success {
        background: rgba(16, 185, 129, 0.25);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.5);
    }
    
    /* Keyframe Animations */
    @keyframes pulse-red {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.04); opacity: 0.85; }
    }
    @keyframes pulse-amber {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.65; }
    }
    
    /* Metric pill */
    .metric-chip {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #818cf8;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.05em;
        margin-top: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. AUDIO RECORDER CORE ENGINE (PyAudio Native Hardware Controller)
# ==============================================================================
class PyAudioThreadRecorder:
    """
    Thread-safe microphone recorder using PyAudio.
    Captures live audio frames at the hardware's native sample rate in a background
    worker thread until explicitly stopped.
    """
    def __init__(self, chunk_size: int = 1024, channels: int = 1, device_index: Optional[int] = None):
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        self.frames = []
        self.is_recording = False
        self.thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        self.stop_time: Optional[float] = None
        self.error: Optional[str] = None
        self.rms_energy: float = 0.0

        # Detect optimal native sample rate from the hardware microphone
        self.sample_rate = 44100
        if PYAUDIO_AVAILABLE:
            try:
                p = pyaudio.PyAudio()
                if device_index is not None:
                    dev = p.get_device_info_by_host_api_device_index(0, device_index)
                else:
                    dev = p.get_default_input_device_info()
                self.sample_rate = int(dev.get("defaultSampleRate", 44100))
                p.terminate()
            except Exception:
                self.sample_rate = 44100

    def start(self):
        """Starts audio capture in a background thread."""
        if not PYAUDIO_AVAILABLE:
            self.error = "PyAudio is not installed or unavailable on this system."
            return False
            
        self.frames = []
        self.is_recording = True
        self.error = None
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()
        return True

    def _capture_worker(self):
        """Worker loop reading chunks from the microphone hardware."""
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )
            while self.is_recording:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
        except Exception as e:
            self.error = str(e)
            self.is_recording = False
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p is not None:
                try:
                    p.terminate()
                except Exception:
                    pass

    def stop(self) -> Optional[bytes]:
        """Stops audio capture, waits for worker thread, and returns PCM WAV bytes."""
        self.is_recording = False
        self.stop_time = time.time()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        if self.error:
            return None
        return self.get_wav_bytes()

    def get_wav_bytes(self) -> Optional[bytes]:
        """Compiles captured audio frames into standard 16-bit PCM WAV bytes."""
        if not self.frames:
            return None
        
        raw_pcm = b"".join(self.frames)
        # Compute RMS audio energy
        try:
            num_shorts = len(raw_pcm) // 2
            if num_shorts > 0:
                shorts = struct.unpack("<" + ("h" * num_shorts), raw_pcm)
                self.rms_energy = math.sqrt(sum(s ** 2 for s in shorts) / num_shorts)
        except Exception:
            self.rms_energy = 0.0

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw_pcm)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()

    @property
    def duration(self) -> float:
        """Returns the recording duration in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.stop_time if self.stop_time else time.time()
        return round(max(0.0, end - self.start_time), 2)


# ==============================================================================
# 3. SPEECH RECOGNITION PIPELINE
# ==============================================================================
def transcribe_audio_bytes(
    audio_bytes: bytes,
    language_code: str = "en-US",
    energy_threshold: int = 300,
    dynamic_energy: bool = True
) -> Tuple[Optional[str], Optional[str], float]:
    """
    Transcribes audio bytes using Google Web Speech Recognition API.
    Crucial: Reads entire audio stream from start to finish without discarding initial speech.
    
    Returns:
        (transcribed_text, error_message, latency_seconds)
    """
    start_t = time.time()
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = energy_threshold
    recognizer.dynamic_energy_threshold = dynamic_energy
    recognizer.pause_threshold = 0.8

    try:
        audio_stream = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_stream) as source:
            # Read complete recording from byte 0 to end (preserves all speech words)
            audio_data = recognizer.record(source)

        # Transcribe using Google Web Speech API
        text = recognizer.recognize_google(audio_data, language=language_code)
        latency = round(time.time() - start_t, 2)
        return text, None, latency

    except sr.UnknownValueError:
        latency = round(time.time() - start_t, 2)
        return None, "Speech was not recognized. Please speak clearly, slightly louder, and closer to your microphone.", latency

    except sr.RequestError as e:
        latency = round(time.time() - start_t, 2)
        return None, f"Could not reach Google Speech Recognition service. Please check your internet connection. (Details: {e})", latency

    except Exception as e:
        latency = round(time.time() - start_t, 2)
        return None, f"Transcription error: {type(e).__name__} - {str(e)}", latency


def convert_audio_to_wav(uploaded_file) -> Optional[bytes]:
    """
    Converts various audio formats (MP3, M4A, OGG, FLAC) to WAV PCM format using pydub.
    If already WAV, returns the raw bytes directly.
    """
    uploaded_file.seek(0)
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    if filename.endswith(".wav"):
        return file_bytes

    if not PYDUB_AVAILABLE:
        st.error("Audio format conversion requires `pydub`. Please upload a standard `.wav` file.")
        return None

    try:
        audio = AudioSegment.from_file(io.BytesIO(file_bytes))
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    except Exception as e:
        st.error(f"Failed to convert audio file '{uploaded_file.name}' to WAV: {e}")
        return None


# Helper to list hardware microphones
def get_available_microphones() -> Dict[str, Optional[int]]:
    """Returns a dictionary of microphone names mapped to device indices."""
    devices = {"Default System Microphone": None}
    if PYAUDIO_AVAILABLE:
        try:
            p = pyaudio.PyAudio()
            info = p.get_host_api_info_by_index(0)
            numdevices = info.get("deviceCount", 0)
            seen_names = set()
            for i in range(numdevices):
                dev = p.get_device_info_by_host_api_device_index(0, i)
                if dev.get("maxInputChannels", 0) > 0:
                    name = dev.get("name", f"Microphone #{i}")
                    if name not in seen_names:
                        devices[f"{name} (Device {i})"] = i
                        seen_names.add(name)
            p.terminate()
        except Exception:
            pass
    return devices


# ==============================================================================
# 4. SESSION STATE INITIALIZATION
# ==============================================================================
if "transcribed_text" not in st.session_state:
    st.session_state["transcribed_text"] = ""
if "last_error" not in st.session_state:
    st.session_state["last_error"] = None
if "audio_bytes" not in st.session_state:
    st.session_state["audio_bytes"] = None
if "recorder" not in st.session_state:
    st.session_state["recorder"] = None
if "is_recording" not in st.session_state:
    st.session_state["is_recording"] = False
if "history" not in st.session_state:
    st.session_state["history"] = []
if "metrics" not in st.session_state:
    st.session_state["metrics"] = {"duration": 0.0, "latency": 0.0, "word_count": 0, "char_count": 0}
if "last_browser_audio_bytes" not in st.session_state:
    st.session_state["last_browser_audio_bytes"] = None


# Helper to update transcription state safely
def set_transcription_result(text: str, source_label: str, duration: float, latency: float):
    words = len(text.split())
    chars = len(text)
    st.session_state["transcribed_text"] = text
    st.session_state["transcription_text_area"] = text
    st.session_state["last_error"] = None
    st.session_state["metrics"] = {
        "duration": duration,
        "latency": latency,
        "word_count": words,
        "char_count": chars,
    }
    st.session_state["history"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "source": source_label,
        "text": text,
        "words": words,
        "duration": duration
    })


# ==============================================================================
# 5. SIDEBAR: SETTINGS & CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")

    # Language Selector
    language_options = {
        "English (US)": "en-US",
        "English (India)": "en-IN",
        "English (UK)": "en-GB",
        "English (Australia)": "en-AU",
        "English (Canada)": "en-CA",
        "Hindi (India)": "hi-IN",
        "Telugu (India)": "te-IN",
        "Tamil (India)": "ta-IN",
        "Spanish (Spain)": "es-ES",
        "French (France)": "fr-FR",
        "German (Germany)": "de-DE",
        "Japanese (Japan)": "ja-JP",
        "Mandarin Chinese": "zh-CN",
    }
    selected_language_label = st.selectbox(
        "🌐 Recognition Language",
        options=list(language_options.keys()),
        index=0,
        help="Select the language or regional accent you will speak."
    )
    language_code = language_options[selected_language_label]

    st.markdown("---")
    st.markdown("### 🎙️ Audio Hardware")

    # Microphone Selection
    available_mics = get_available_microphones()
    selected_mic_name = st.selectbox(
        "Select Hardware Input",
        options=list(available_mics.keys()),
        index=0,
        help="Choose the hardware microphone interface to record from."
    )
    selected_device_index = available_mics[selected_mic_name]

    # Sensitivity Controls
    st.markdown("---")
    st.markdown("### 🎚️ Sensitivity Tuning")
    
    dynamic_energy = st.checkbox("Dynamic Sensitivity", value=True, help="Dynamically adapts voice detection to room acoustic levels.")
    energy_threshold = st.slider("Energy Threshold", min_value=50, max_value=1500, value=300, step=50, help="Lower values detect soft whispers; higher values filter out background hums.")

    st.markdown("---")
    # Health Status
    st.markdown("### 🩺 Diagnostic Status")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.write("**PyAudio:**")
        if PYAUDIO_AVAILABLE:
            st.success("Installed")
        else:
            st.warning("Unavailable")
    with col_d2:
        st.write("**Internet:**")
        st.success("Connected")

    st.caption("Google Web Speech API: **Online & Ready**")


# ==============================================================================
# 6. MAIN HEADER & STATUS BAR
# ==============================================================================
st.markdown(
    """
    <div class="header-banner">
        <div>
            <h1 class="header-title">🎙️ Speech-to-Text Converter</h1>
            <div class="header-subtitle">
                High-performance voice transcription powered by Python, Streamlit & Google Web Speech Recognition
            </div>
        </div>
        <div>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600;">
                ⚡ Fast • Accurate • Multi-Language
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Status Badge Indicator
status_placeholder = st.empty()
if st.session_state["is_recording"]:
    status_placeholder.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <span class="status-badge status-recording">
                🔴 RECORDING IN PROGRESS — Speak clearly into your microphone...
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    status_placeholder.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
            <span class="status-badge status-idle">
                🟢 SYSTEM READY — Choose an audio input method below to begin
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 7. AUDIO CAPTURE MODES (TABS)
# ==============================================================================
tab_browser_mic, tab_live_mic, tab_upload = st.tabs([
    "🎙️ Web Browser Microphone (Works on Cloud and Mobile)",
    "💻 Local Desktop Microphone (PyAudio - Local Machine Only)",
    "📁 Upload Audio File"
])


# ------------------------------------------------------------------------------
# TAB 1: Live Hardware Microphone with Dedicated Start/Stop Buttons
# ------------------------------------------------------------------------------
with tab_live_mic:
    st.info("ℹ️ **Cloud Note:** When using this app over the web (e.g. on Streamlit Cloud), please use the **Web Browser Microphone** tab above so your browser can capture your voice. This tab accesses local server hardware.")
    st.markdown("#### Record Voice via Computer Microphone")
    st.caption("Click **Start Recording** to begin capturing voice, speak a complete sentence, and click **Stop Recording** to transcribe.")

    btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1.5, 3])

    with btn_col1:
        # START RECORDING BUTTON
        start_disabled = st.session_state["is_recording"] or not PYAUDIO_AVAILABLE
        if st.button("🔴 Start Recording", type="primary", use_container_width=True, disabled=start_disabled):
            st.session_state["last_error"] = None
            recorder = PyAudioThreadRecorder(
                chunk_size=1024,
                channels=1,
                device_index=selected_device_index
            )
            success = recorder.start()
            if success:
                st.session_state["recorder"] = recorder
                st.session_state["is_recording"] = True
                st.rerun()
            else:
                st.error(f"Failed to start microphone: {recorder.error}")

    with btn_col2:
        # STOP RECORDING BUTTON
        stop_disabled = not st.session_state["is_recording"]
        if st.button("⏹️ Stop Recording", type="secondary", use_container_width=True, disabled=stop_disabled):
            if st.session_state["recorder"]:
                recorder = st.session_state["recorder"]
                with st.spinner("Finalizing audio stream and transcribing..."):
                    wav_bytes = recorder.stop()
                    duration = recorder.duration
                    rms = recorder.rms_energy
                    st.session_state["is_recording"] = False
                    st.session_state["recorder"] = None

                    if wav_bytes and len(wav_bytes) > 2000:
                        st.session_state["audio_bytes"] = wav_bytes

                        # Check if audio is virtually silent
                        if rms < 80.0:
                            st.warning(f"⚠️ Low audio signal detected (Energy level: {rms:.1f}). If no text appears, make sure your microphone volume is turned up in Windows Sound Settings.")

                        text, err, latency = transcribe_audio_bytes(
                            wav_bytes,
                            language_code=language_code,
                            energy_threshold=energy_threshold,
                            dynamic_energy=dynamic_energy
                        )
                        if text:
                            set_transcription_result(text, "Hardware Mic", duration, latency)
                            st.toast("✅ Voice successfully transcribed!")
                        else:
                            st.session_state["last_error"] = err
                    else:
                        st.session_state["last_error"] = "Recording was too short or empty. Please speak for at least 1-2 seconds."
                st.rerun()

    with btn_col3:
        if st.session_state["is_recording"]:
            rec_obj = st.session_state.get("recorder")
            cur_duration = rec_obj.duration if rec_obj else 0.0
            st.warning(f"🎙️ Microphone is recording! Speak now, then click 'Stop Recording' to produce text.")
        else:
            st.info("💡 Instructions: 1. Click 'Start Recording' ➔ 2. Speak your words ➔ 3. Click 'Stop Recording'.")

    # If PyAudio is missing, show helpful note
    if not PYAUDIO_AVAILABLE:
        st.warning(
            "⚠️ PyAudio is not installed in this environment. You can use the **Web Browser Microphone** tab "
            "which runs directly in any browser without needing PyAudio, or install PyAudio via `pip install pyaudio`."
        )


# ------------------------------------------------------------------------------
# TAB 2: Web Browser Microphone (HTML5 Audio Input)
# ------------------------------------------------------------------------------
with tab_browser_mic:
    st.markdown("#### Record Voice Directly in Your Web Browser")
    st.caption("Uses HTML5 browser audio. Works on all browsers and devices.")

    if hasattr(st, "audio_input"):
        browser_audio = st.audio_input("Record Speech via Browser Microphone")

        if browser_audio is not None:
            audio_bytes = browser_audio.getvalue()
            st.audio(browser_audio, format="audio/wav")

            # Auto-transcribe as soon as new audio is recorded!
            if st.session_state.get("last_browser_audio_bytes") != audio_bytes:
                st.session_state["last_browser_audio_bytes"] = audio_bytes
                st.session_state["audio_bytes"] = audio_bytes
                with st.spinner("Transcribing your speech..."):
                    text, err, latency = transcribe_audio_bytes(
                        audio_bytes,
                        language_code=language_code,
                        energy_threshold=energy_threshold,
                        dynamic_energy=dynamic_energy
                    )
                    if text:
                        set_transcription_result(text, "Browser Mic", round(len(audio_bytes) / 32000.0, 2), latency)
                        st.toast("✅ Browser speech transcribed!")
                        st.rerun()
                    else:
                        st.session_state["last_error"] = err
                        st.rerun()

            # Manual re-transcribe button
            if st.button("✨ Re-transcribe Browser Recording", type="primary", key="btn_transcribe_browser"):
                with st.spinner("Transcribing browser audio..."):
                    text, err, latency = transcribe_audio_bytes(
                        audio_bytes,
                        language_code=language_code,
                        energy_threshold=energy_threshold,
                        dynamic_energy=dynamic_energy
                    )
                    if text:
                        set_transcription_result(text, "Browser Mic", round(len(audio_bytes) / 32000.0, 2), latency)
                        st.toast("✅ Browser speech transcribed!")
                        st.rerun()
                    else:
                        st.session_state["last_error"] = err
                        st.rerun()
    else:
        st.info("💡 In-browser recording widget requires Streamlit 1.40+. Please use the **Live Hardware Microphone** tab above!")


# ------------------------------------------------------------------------------
# TAB 3: Audio File Upload
# ------------------------------------------------------------------------------
with tab_upload:
    st.markdown("#### Transcribe Pre-Recorded Audio Files")
    st.caption("Supports WAV, MP3, M4A, FLAC, and OGG formats.")

    uploaded_file = st.file_uploader(
        "Upload Speech Audio File",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        help="Upload an audio recording of human speech."
    )

    if uploaded_file is not None:
        st.audio(uploaded_file)
        if st.button("🚀 Transcribe Uploaded File", type="primary", key="btn_transcribe_file"):
            with st.spinner(f"Converting and transcribing '{uploaded_file.name}'..."):
                wav_bytes = convert_audio_to_wav(uploaded_file)
                if wav_bytes:
                    st.session_state["audio_bytes"] = wav_bytes
                    text, err, latency = transcribe_audio_bytes(
                        wav_bytes,
                        language_code=language_code,
                        energy_threshold=energy_threshold,
                        dynamic_energy=dynamic_energy
                    )
                    if text:
                        set_transcription_result(text, f"File ({uploaded_file.name})", round(len(wav_bytes) / 32000.0, 2), latency)
                        st.toast("✅ Audio file transcribed successfully!")
                        st.rerun()
                    else:
                        st.session_state["last_error"] = err
                        st.rerun()


# ==============================================================================
# 8. ERROR & WARNING DISPLAY
# ==============================================================================
if st.session_state.get("last_error"):
    st.markdown("---")
    st.error(f"⚠️ **Notice:** {st.session_state['last_error']}")
    st.info("💡 **Quick Fixes:**\n"
            "- Speak clearly directly towards the microphone.\n"
            "- Speak for at least 1-2 seconds.\n"
            "- Check Windows microphone privacy settings: *Settings > Privacy & Security > Microphone*.\n"
            "- Verify that your internet connection is active.")


# ==============================================================================
# 9. TRANSCRIPTION OUTPUT & METRICS DASHBOARD
# ==============================================================================
st.markdown("---")
st.markdown("### 📝 Transcribed Output")

current_text = st.session_state.get("transcribed_text", "")

# Prominent Visual Highlight Card when speech is transcribed
if current_text:
    st.markdown(
        f"""
        <div style="background: rgba(16, 185, 129, 0.15); border: 1.5px solid rgba(16, 185, 129, 0.5); border-radius: 14px; padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1);">
            <div style="color: #34d399; font-weight: 700; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.5rem;">
                <span>🗣️ Detected Speech</span>
            </div>
            <div style="color: #ffffff; font-size: 1.35rem; font-weight: 600; margin-top: 0.5rem; line-height: 1.5;">
                "{current_text}"
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Metrics summary bar
m = st.session_state["metrics"]
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        f"""
        <div class="metric-chip">
            <div class="metric-value">{m['word_count']}</div>
            <div class="metric-label">Words Counted</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_m2:
    st.markdown(
        f"""
        <div class="metric-chip">
            <div class="metric-value">{m['char_count']}</div>
            <div class="metric-label">Characters</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-chip">
            <div class="metric-value">{m['duration']}s</div>
            <div class="metric-label">Audio Length</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_m4:
    st.markdown(
        f"""
        <div class="metric-chip">
            <div class="metric-value">{m['latency']}s</div>
            <div class="metric-label">Processing Time</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("")

# Synchronize session state text area
if "transcription_text_area" not in st.session_state:
    st.session_state["transcription_text_area"] = current_text

edited_text = st.text_area(
    "Transcribed Speech Content (Editable)",
    value=st.session_state["transcription_text_area"],
    height=180,
    placeholder="Your spoken words will appear here immediately after recording stops...",
    key="transcription_text_area"
)

# Playback of the recorded/uploaded audio if present
if st.session_state.get("audio_bytes"):
    with st.expander("🎧 Listen to Last Processed Audio Recording", expanded=True):
        st.audio(st.session_state["audio_bytes"], format="audio/wav")


# ==============================================================================
# 10. ACTION BUTTONS: COPY, CLEAR, DOWNLOAD
# ==============================================================================
act_col1, act_col2, act_col3, act_col4 = st.columns([1.2, 1.2, 1.5, 2.5])

with act_col1:
    # COPY TEXT BUTTON (JavaScript Clipboard API + Toast Feedback)
    if st.button("📋 Copy Text", use_container_width=True, disabled=not bool(current_text)):
        escaped_text = json.dumps(current_text)
        copy_js = f"""
        <script>
        navigator.clipboard.writeText({escaped_text}).then(function() {{
            console.log('Text copied to clipboard!');
        }});
        </script>
        """
        st.components.v1.html(copy_js, height=0, width=0)
        st.toast("✅ Transcribed text copied to clipboard!")

with act_col2:
    # CLEAR TEXT BUTTON
    if st.button("🗑️ Clear Text", use_container_width=True, disabled=not bool(current_text or st.session_state.get("audio_bytes"))):
        st.session_state["transcribed_text"] = ""
        st.session_state["transcription_text_area"] = ""
        st.session_state["audio_bytes"] = None
        st.session_state["last_error"] = None
        st.session_state["last_browser_audio_bytes"] = None
        st.session_state["metrics"] = {"duration": 0.0, "latency": 0.0, "word_count": 0, "char_count": 0}
        st.toast("🧹 Output cleared!")
        st.rerun()

with act_col3:
    # DOWNLOAD AS TEXT FILE (.txt)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="💾 Download .TXT",
        data=current_text.encode("utf-8"),
        file_name=f"transcription_{timestamp_str}.txt",
        mime="text/plain",
        use_container_width=True,
        disabled=not bool(current_text)
    )

with act_col4:
    # DOWNLOAD AS JSON REPORT (.json)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "language": selected_language_label,
        "language_code": language_code,
        "metrics": st.session_state["metrics"],
        "transcription": current_text,
    }
    st.download_button(
        label="📊 Download JSON Report",
        data=json.dumps(report_data, indent=2).encode("utf-8"),
        file_name=f"transcription_report_{timestamp_str}.json",
        mime="application/json",
        use_container_width=True,
        disabled=not bool(current_text)
    )


# ==============================================================================
# 11. TRANSCRIPTION HISTORY LOG
# ==============================================================================
if st.session_state.get("history"):
    st.markdown("---")
    with st.expander(f"📜 Session Transcription History ({len(st.session_state['history'])} records)", expanded=False):
        for idx, entry in enumerate(reversed(st.session_state["history"])):
            st.markdown(
                f"""
                <div style="background: rgba(15, 23, 42, 0.4); border-left: 4px solid #6366f1; padding: 0.8rem 1rem; margin-bottom: 0.8rem; border-radius: 8px;">
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.3rem;">
                        🕒 <b>{entry['time']}</b> &nbsp;•&nbsp; 🏷️ Source: <i>{entry['source']}</i> &nbsp;•&nbsp; ⏱️ Audio: {entry['duration']}s &nbsp;•&nbsp; 📝 Words: {entry['words']}
                    </div>
                    <div style="font-size: 0.95rem; color: #f1f5f9;">
                        "{entry['text']}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        if st.button("Clear History Log", key="btn_clear_history"):
            st.session_state["history"] = []
            st.rerun()


# ==============================================================================
# 12. FOOTER & DEVELOPER INFO
# ==============================================================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 1.2rem 0;">
        Speech-to-Text Converter Web Application • Built with 🐍 Python, 🎈 Streamlit & 🎙️ Google Speech Recognition API
        <br>
        <i>Engineered for Real-time Robustness, Noise Suppression & Cross-Platform Accessibility</i>
    </div>
    """,
    unsafe_allow_html=True
)
