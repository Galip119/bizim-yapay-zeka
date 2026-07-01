"""
=====================================================================
Eymex Nexus-Core(EXPANDED VERSION)
=====================================================================
"""

# ========================= IMPORTS =========================
import streamlit as st
import numpy as np
import time
import base64
import io
import datetime
import logging


# ========================= LOG SYSTEM =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("ColossusOS")


# ========================= SESSION INIT =========================
def init_state():
    if "log" not in st.session_state:
        st.session_state.log = []

    if "bpm" not in st.session_state:
        st.session_state.bpm = 140

    if "engine_ready" not in st.session_state:
        st.session_state.engine_ready = True

    if "selected_style" not in st.session_state:
        st.session_state.selected_style = "manual"

    if "last_render" not in st.session_state:
        st.session_state.last_render = None


init_state()


# ========================= BEAT GRID ENGINE =========================
class BeatGrid:

    def __init__(self, steps=16):
        self.steps = steps
        self.reset()

    def reset(self):
        self.kick = np.zeros(self.steps)
        self.snare = np.zeros(self.steps)
        self.hihat = np.zeros(self.steps)

    def clear(self):
        self.reset()

    def set_step(self, track, step):
        if 0 <= step < self.steps:
            getattr(self, track)[step] = 1

    def preset_trap(self):
        self.clear()

        for i in [0, 4, 8, 12]:
            self.kick[i] = 1

        for i in [4, 12]:
            self.snare[i] = 1

        self.hihat[:] = [1 if i % 2 == 0 else 0 for i in range(self.steps)]

    def preset_techno(self):
        self.clear()

        for i in range(0, self.steps, 4):
            self.kick[i] = 1

        self.hihat[:] = 1

    def preset_lofi(self):
        self.clear()

        self.kick[0] = 1
        self.snare[8] = 1

        for i in range(self.steps):
            if i % 3 == 0:
                self.hihat[i] = 1

    def export_pattern(self):
        return {
            "kick": self.kick.tolist(),
            "snare": self.snare.tolist(),
            "hihat": self.hihat.tolist()
        }

    def render_audio(self, sr=44100):

        step_len = sr // 4
        total = self.steps * step_len

        audio = np.zeros(total)

        kick_sample = np.sin(np.linspace(0, 15, 200)) * 0.8
        snare_sample = np.random.randn(200) * 0.4
        hat_sample = np.random.randn(80) * 0.2

        def place(track, sample):
            for i in range(self.steps):
                if track[i]:
                    start = i * step_len
                    end = start + len(sample)

                    if end < total:
                        audio[start:end] += sample

        place(self.kick, kick_sample)
        place(self.snare, snare_sample)
        place(self.hihat, hat_sample)

        return audio


# ========================= ENGINE =========================
class ColossusEngine:

    def __init__(self):
        self.grid = BeatGrid(16)
        self.version = "1.0-EXPANDED"

    def analyze_prompt(self, prompt: str):

        p = prompt.lower()

        if "trap" in p:
            self.grid.preset_trap()
            return "Trap pattern generated"

        elif "techno" in p:
            self.grid.preset_techno()
            return "Techno pattern generated"

        elif "lofi" in p:
            self.grid.preset_lofi()
            return "Lofi pattern generated"

        else:
            self.grid.clear()
            return "Empty pattern"


engine = ColossusEngine()


# ========================= UI HELPERS =========================
def log_add(msg):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append(f"[{t}] {msg}")


def show_log():
    st.subheader("📜 System Log")

    for l in reversed(st.session_state.log[-15:]):
        st.code(l)


# ========================= STREAMLIT UI =========================
st.set_page_config(
    page_title="Colossus Music OS",
    layout="wide"
)

st.title("🎛 COLLOSSUS MUSIC OS - EXPANDED EDITION")


# ================= SIDEBAR =================
st.sidebar.header("Control Panel")

st.session_state.selected_style = st.sidebar.selectbox(
    "Style",
    ["manual", "trap", "techno", "lofi"]
)

st.session_state.bpm = st.sidebar.slider(
    "BPM",
    60, 200, 140
)

if st.sidebar.button("Generate Pattern"):

    result = engine.analyze_prompt(
        st.session_state.selected_style
    )

    log_add(result)

    st.success(result)


if st.sidebar.button("Reset Grid"):

    engine.grid.clear()

    log_add("Grid cleared")

    st.warning("Grid reset")


# ================= GRID VIEW =================
st.divider()

st.subheader("🎹 Step Sequencer (16 Grid)")

cols = st.columns(16)

for i in range(16):

    with cols[i]:

        if st.button("●", key=f"step_{i}"):

            engine.grid.kick[i] = 1
            log_add(f"Kick added at step {i}")

        st.caption(str(i))


# ================= PATTERN VIEW =================
st.divider()

st.write("Kick Pattern:", engine.grid.kick)
st.write("Snare Pattern:", engine.grid.snare)
st.write("Hat Pattern:", engine.grid.hihat)


# ================= RENDER =================
if st.button("▶ Render Track"):

    audio = engine.grid.render_audio()

    st.session_state.last_render = audio

    log_add("Audio rendered")

    st.success("Render complete")

    st.line_chart(audio[:2000])


# ================= EXPORT =================
if st.button("📦 Export Pattern JSON"):

    pattern = engine.grid.export_pattern()

    st.json(pattern)

    log_add("Pattern exported")


# ================= LOG PANEL =================
st.divider()

show_log()


# ================= STATUS =================
st.sidebar.divider()

st.sidebar.metric(
    "Active BPM",
    st.session_state.bpm
)

st.sidebar.metric(
    "Log Count",
    len(st.session_state.log)
)
