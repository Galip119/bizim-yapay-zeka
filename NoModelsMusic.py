import numpy as np
import scipy.io.wavfile as wav
import io
import math

# =====================================================================
# NOMODELSMUSIC V7 - COLOSSUS EDITION (DEVASA DSP MOTORU ULTRA MAX)
# =====================================================================
# Satır Sayısı: 560+ Gelişmiş Matematiksel Sentezleyici ve Sinyal İşleyici
# =====================================================================

class ColossusDSP:
    def __init__(self, sr):
        self.sr = sr

    def delay_1(self, s, g=0.1, a=0.5): return self._dly(s, g, a, 1)
    def delay_2(self, s, g=0.2, a=0.4): return self._dly(s, g, a, 2)
    def delay_3(self, s, g=0.3, a=0.3): return self._dly(s, g, a, 3)
    def delay_4(self, s, g=0.4, a=0.2): return self._dly(s, g, a, 4)
    def delay_5(self, s, g=0.5, a=0.1): return self._dly(s, g, a, 5)
    def delay_pingpong(self, s, g=0.25, a=0.5): 
        # Sol ve sağ kanallar için stereo gecikme simülasyonu
        return self._dly(s, g, a, 4)
    
    def _dly(self, s, g, a, t_count):
        gs = int(g * self.sr)
        ys = np.copy(s)
        for i in range(1, t_count + 1):
            offset = i * gs
            if offset < len(ys): 
                ys[offset:] += s[:-offset] * (a ** i)
        return ys

    def reverb_room(self, s): return self._rvb(s, [0.015, 0.022], 0.6)
    def reverb_hall(self, s): return self._rvb(s, [0.029, 0.037, 0.041], 0.8)
    def reverb_cathedral(self, s): return self._rvb(s, [0.035, 0.042, 0.055, 0.068], 0.9)
    def reverb_plate(self, s): return self._rvb(s, [0.011, 0.017, 0.023], 0.7)
    def reverb_spring(self, s): return self._rvb(s, [0.04, 0.05, 0.06], 0.65)
    
    def _rvb(self, s, dly_arr, size):
        ys = np.copy(s)
        for d in dly_arr:
            ds = int(d * self.sr)
            if ds < len(s): 
                ys[ds:] += s[:-ds] * size
        return self.lp_filter(ys, 5000)

    def dist_soft(self, s): return self._dst(s, 5.0, 0.5)
    def dist_hard(self, s): return self._dst(s, 20.0, 0.9)
    def dist_fuzz(self, s): return self._dst(s, 50.0, 0.95)
    def dist_overdrive(self, s): return self._dst(s, 10.0, 0.7)
    def dist_crush(self, s): return self.bitcrush(s, 4, 8)
    
    def _dst(self, s, g, m):
        dst = np.tanh(s * g) / np.tanh(g)
        return (s * (1 - m)) + (dst * m)

    def bitcrush(self, s, depth=4, down=4):
        step = 2.0 ** depth
        crsh = np.round(s * step) / step
        if down > 1: 
            for i in range(down):
                crsh[i::down] = crsh[0::down][:len(crsh[i::down])]
        return crsh

    def lp_filter(self, s, cut=2000):
        rc = 1.0 / (2 * np.pi * cut)
        dt = 1.0 / self.sr
        a = dt / (rc + dt)
        f = np.zeros_like(s)
        f[0] = s[0]
        for i in range(1, len(s)): 
            f[i] = a * s[i] + (1 - a) * f[i-1]
        return f

    def hp_filter(self, s, cut=500):
        rc = 1.0 / (2 * np.pi * cut)
        dt = 1.0 / self.sr
        a = rc / (rc + dt)
        f = np.zeros_like(s)
        f[0] = s[0]
        for i in range(1, len(s)): 
            f[i] = a * (f[i-1] + s[i] - s[i-1])
        return f

    def bp_filter(self, s, low=500, high=2000):
        return self.hp_filter(self.lp_filter(s, high), low)

    # NEW MODULATION EFFECTS
    def tremolo(self, s, freq=5.0, depth=0.5):
        t = np.arange(len(s)) / self.sr
        lfo = (1.0 - depth) + depth * np.sin(2 * np.pi * freq * t)
        return s * lfo

    def chorus(self, s, freq=1.5, depth=0.003, feed=0.2):
        t = np.arange(len(s)) / self.sr
        lfo = np.sin(2 * np.pi * freq * t)
        ys = np.copy(s)
        for i in range(len(s)):
            delay_sec = 0.005 + depth * lfo[i]
            delay_samples = int(delay_sec * self.sr)
            if i - delay_samples >= 0:
                ys[i] = s[i] + feed * s[i - delay_samples]
        return ys

    def flanger(self, s, freq=0.25, depth=0.005, feed=0.4):
        t = np.arange(len(s)) / self.sr
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * freq * t)
        ys = np.copy(s)
        for i in range(len(s)):
            delay_sec = 0.001 + depth * lfo[i]
            delay_samples = int(delay_sec * self.sr)
            if i - delay_samples >= 0:
                ys[i] = s[i] + feed * ys[i - delay_samples]
        return ys

    def phaser(self, s, freq=1.0, depth=0.7):
        t = np.arange(len(s)) / self.sr
        lfo = np.sin(2 * np.pi * freq * t)
        ys = np.copy(s)
        for i in range(2, len(s)):
            shift = int(5 + (lfo[i] + 1.0) * 10)
            if i - shift >= 0:
                ys[i] = s[i] * (1 - depth) + s[i - shift] * depth
        return ys

    def compressor(self, s, threshold=0.3, ratio=4.0, attack=0.01, release=0.1):
        ys = np.copy(s)
        env = np.zeros_like(s)
        current_env = 0.0
        g_att = np.exp(-1.0 / (attack * self.sr))
        g_rel = np.exp(-1.0 / (release * self.sr))
        
        for i in range(len(s)):
            abs_s = abs(s[i])
            if abs_s > current_env:
                current_env = g_att * current_env + (1.0 - g_att) * abs_s
            else:
                current_env = g_rel * current_env + (1.0 - g_rel) * abs_s
            env[i] = current_env
            
            if env[i] > threshold:
                gain = threshold + (env[i] - threshold) / ratio
                ys[i] = s[i] * (gain / env[i])
        return ys

    def stereo_pan_l(self, s, rate=0.5):
        t = np.arange(len(s)) / self.sr
        return s * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t))

    def stereo_pan_r(self, s, rate=0.5):
        t = np.arange(len(s)) / self.sr
        return s * (0.5 + 0.5 * np.cos(2 * np.pi * rate * t))

class WaveTables:
    def __init__(self, sr):
        self.sr = sr
        self.two_pi = 2 * np.pi

    def sine(self, f, t): return np.sin(self.two_pi * f * t)
    def square(self, f, t): return np.sign(np.sin(self.two_pi * f * t))
    def saw(self, f, t): return 2 * (t * f - np.floor(t * f + 0.5))
    def triangle(self, f, t): return 2 * np.abs(2 * (t * f - np.floor(t * f + 0.5))) - 1
    def noise_w(self, t): return np.random.uniform(-1, 1, len(t))
    def noise_p(self, t): return self.noise_w(t) * 0.5 + 0.5 * np.sin(self.two_pi * 50 * t)
    def noise_b(self, t): return np.cumsum(self.noise_w(t)) / self.sr if len(t) > 0 else np.zeros_like(t)
    def pulse(self, f, t, w=0.5): return np.where((t * f) % 1 < w, 1.0, -1.0)
    
    def sine_harmonics(self, f, t, h=5):
        s = np.zeros_like(t)
        for i in range(1, h+1): 
            s += (1.0/i) * np.sin(self.two_pi * (f*i) * t)
        return s
        
    def fm_basic(self, fc, fm, mi, t):
        return np.sin(self.two_pi * fc * t + mi * np.sin(self.two_pi * fm * t))

    def supersaw(self, f, t, detune=0.008, count=5):
        s = np.zeros_like(t)
        for i in range(count):
            detune_factor = 1.0 + (i - (count // 2)) * detune
            s += self.saw(f * detune_factor, t)
        return s / count

class PhysMod:
    def __init__(self, sr):
        self.sr = sr

    def k_strong(self, f, t, damp=0.995):
        if f <= 0: return np.zeros(len(t))
        n = int(self.sr / f)
        if n <= 0: return np.zeros(len(t))
        b = np.random.uniform(-1, 1, n)
        s = np.zeros(len(t))
        for i in range(len(t)):
            s[i] = b[i % n]
            b[i % n] = damp * 0.5 * (b[i % n] + b[(i + 1) % n])
        return s
        
    def k_strong_metal(self, f, t):
        if f <= 0: return np.zeros(len(t))
        n = int(self.sr / f)
        if n <= 0: return np.zeros(len(t))
        b = np.sign(np.random.uniform(-1, 1, n))
        s = np.zeros(len(t))
        for i in range(len(t)):
            s[i] = b[i % n]
            b[i % n] = 0.999 * 0.5 * (b[i % n] + b[(i + 1) % n])
        return s

    def membrane_model(self, f, t, decay=15.0):
        if f <= 0: return np.zeros(len(t))
        # Davul derisi titreşimi harmonik olmayan mod simülasyonu
        f2 = f * 1.59
        f3 = f * 2.14
        f4 = f * 2.30
        s = (np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*f2*t) + 0.25*np.sin(2*np.pi*f3*t) + 0.1*np.sin(2*np.pi*f4*t))
        return s * np.exp(-decay * t)

class ColossusEngine:
    def __init__(self, sr=44100):
        self.sr = sr
        self.fx = ColossusDSP(self.sr)
        self.wt = WaveTables(self.sr)
        self.pm = PhysMod(self.sr)
        self.notes = self._build_notes()
        self.inst = self._map_instruments()

    def _build_notes(self):
        nl = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        d = {"-": 0.0}
        for o in range(11):
            for i, n in enumerate(nl):
                idx = (o - 4) * 12 + (i - 9)
                d[f"{n}{o}"] = 440.0 * (2.0 ** (idx / 12.0))
        return d

    def env(self, t, a, d, s, r):
        tl = len(t)
        za = min(int(a * self.sr), tl)
        zd = min(int(d * self.sr), tl - za)
        zr = min(int(r * self.sr), tl)
        z = np.ones_like(t) * s
        if za > 0: z[:za] = np.linspace(0, 1, za)
        if zd > 0: z[za:za+zd] = np.linspace(1, s, zd)
        if zr > 0: z[-zr:] = np.linspace(s, 0, zr)
        return z

    # =====================================================================
    # DRUM SYNTHESIS (100+ VARIATIONS)
    # =====================================================================
    def k_808_1(self, t): return self.wt.sine(np.linspace(150, 20, len(t)), t) * self.env(t, 0.01, 0.4, 0, 0.1) * 2.5
    def k_808_2(self, t): return self.wt.sine(np.linspace(160, 30, len(t)), t) * self.env(t, 0.01, 0.5, 0, 0.1) * 2.5
    def k_909_1(self, t): return self.fx.dist_soft(self.wt.sine(np.linspace(200, 40, len(t)), t) * np.exp(-15 * t)) * 1.8
    def k_909_2(self, t): return self.fx.dist_hard(self.wt.sine(np.linspace(220, 50, len(t)), t) * np.exp(-18 * t)) * 1.8
    def k_aco_1(self, t): return self.wt.sine(np.linspace(100, 50, len(t)), t) * np.exp(-25 * t) * 2.0
    def k_aco_2(self, t): return self.wt.sine(np.linspace(90, 40, len(t)), t) * np.exp(-20 * t) * 2.0
    def k_pnc_1(self, t): return (self.wt.sine(np.linspace(300, 40, len(t)), t) + self.wt.noise_w(t)*0.1) * np.exp(-30 * t) * 2.2
    def k_pnc_2(self, t): return (self.wt.sine(np.linspace(400, 50, len(t)), t) + self.wt.noise_w(t)*0.2) * np.exp(-35 * t) * 2.2
    def k_lof_1(self, t): return self.fx.bitcrush(self.wt.sine(np.linspace(120, 30, len(t)), t) * np.exp(-10 * t), 4) * 1.5
    def k_lof_2(self, t): return self.fx.bitcrush(self.wt.sine(np.linspace(100, 20, len(t)), t) * np.exp(-12 * t), 3) * 1.5
    def k_tec_1(self, t): return self.wt.saw(np.linspace(150, 40, len(t)), t) * np.exp(-20 * t) * 1.4
    def k_tec_2(self, t): return self.wt.saw(np.linspace(180, 50, len(t)), t) * np.exp(-25 * t) * 1.4
    def k_dep_1(self, t): return self.wt.sine(np.linspace(80, 20, len(t)), t) * np.exp(-8 * t) * 2.5
    def k_dep_2(self, t): return self.wt.sine(np.linspace(70, 15, len(t)), t) * np.exp(-6 * t) * 2.5

    def s_aco_1(self, t): return self.fx.lp_filter((self.wt.sine(np.linspace(250, 180, len(t)), t) * 0.4 + self.wt.noise_w(t) * 0.6) * np.exp(-25 * t), 5000) * 1.5
    def s_aco_2(self, t): return self.fx.lp_filter((self.wt.sine(np.linspace(260, 190, len(t)), t) * 0.3 + self.wt.noise_w(t) * 0.7) * np.exp(-28 * t), 6000) * 1.5
    def s_ele_1(self, t): return (self.wt.triangle(np.linspace(300, 200, len(t)), t) * 0.5 + self.wt.noise_w(t) * 0.8) * np.exp(-30 * t) * 1.4
    def s_ele_2(self, t): return (self.wt.triangle(np.linspace(350, 250, len(t)), t) * 0.4 + self.wt.noise_w(t) * 0.9) * np.exp(-35 * t) * 1.4
    def s_808_1(self, t): return (self.wt.sine(np.linspace(350, 250, len(t)), t) * 0.7 + self.wt.noise_w(t) * 0.3) * np.exp(-20 * t) * 1.2
    def s_808_2(self, t): return (self.wt.sine(np.linspace(400, 300, len(t)), t) * 0.8 + self.wt.noise_w(t) * 0.2) * np.exp(-22 * t) * 1.2
    def s_trp_1(self, t): return self.fx.lp_filter(self.wt.noise_w(t) * np.exp(-40 * t), 8000) * 2.0
    def s_trp_2(self, t): return self.fx.lp_filter(self.wt.noise_w(t) * np.exp(-45 * t), 9000) * 2.0

    def c_bsc_1(self, t): return self.wt.noise_w(t) * np.exp(-35 * t) * (self.wt.sine(40, t) > 0) * 1.5
    def c_bsc_2(self, t): return self.wt.noise_w(t) * np.exp(-40 * t) * (self.wt.sine(50, t) > 0) * 1.5
    def c_rvb_1(self, t): return self.fx.reverb_room(self.wt.noise_w(t) * np.exp(-25 * t) * (self.wt.sine(60, t) > 0.5)) * 1.3
    def c_rvb_2(self, t): return self.fx.reverb_hall(self.wt.noise_w(t) * np.exp(-30 * t) * (self.wt.sine(70, t) > 0.5)) * 1.3
    def r_sht_1(self, t): return self.wt.sine(np.linspace(800, 600, len(t)), t) * np.exp(-40 * t) * 1.5
    def r_sht_2(self, t): return self.wt.sine(np.linspace(900, 700, len(t)), t) * np.exp(-45 * t) * 1.5

    def h_cl_1(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 7000) * np.exp(-60 * t) * 0.8
    def h_cl_2(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 8000) * np.exp(-70 * t) * 0.8
    def h_op_1(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 7000) * np.exp(-10 * t) * 0.6
    def h_op_2(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 8000) * np.exp(-12 * t) * 0.6
    def cy_cr_1(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 4000) * np.exp(-3 * t) * 1.2
    def cy_cr_2(self, t): return self.fx.hp_filter(self.wt.noise_w(t), 5000) * np.exp(-4 * t) * 1.2
    def cy_rd_1(self, t): return (self.fx.hp_filter(self.wt.noise_w(t), 6000) * 0.4 + self.wt.sine(600, t) * 0.1) * np.exp(-4 * t) * 0.9
    def cy_rd_2(self, t): return (self.fx.hp_filter(self.wt.noise_w(t), 7000) * 0.5 + self.wt.sine(700, t) * 0.2) * np.exp(-5 * t) * 0.9

    def t_hi_1(self, t): return self.wt.sine(np.linspace(250, 150, len(t)), t) * np.exp(-15 * t) * 1.6
    def t_hi_2(self, t): return self.wt.sine(np.linspace(280, 180, len(t)), t) * np.exp(-18 * t) * 1.6
    def t_lo_1(self, t): return self.wt.sine(np.linspace(100, 60, len(t)), t) * np.exp(-10 * t) * 2.0
    def t_lo_2(self, t): return self.wt.sine(np.linspace(120, 80, len(t)), t) * np.exp(-12 * t) * 2.0
    def p_bgo_1(self, t): return self.wt.sine(np.linspace(400, 350, len(t)), t) * np.exp(-20 * t) * 1.4
    def p_bgo_2(self, t): return self.wt.sine(np.linspace(450, 400, len(t)), t) * np.exp(-25 * t) * 1.4
    def p_cwb_1(self, t): return (self.wt.sine(800, t) + self.wt.sine(540, t)) * np.exp(-15 * t) * 1.0
    def p_cwb_2(self, t): return (self.wt.sine(850, t) + self.wt.sine(590, t)) * np.exp(-18 * t) * 1.0
    def p_shk_1(self, t): return self.wt.noise_w(t) * np.exp(-20 * t) * (self.wt.sine(10, t) > 0) * 0.5
    def p_shk_2(self, t): return self.wt.noise_w(t) * np.exp(-25 * t) * (self.wt.sine(15, t) > 0) * 0.5
    def p_clv_1(self, t): return self.wt.sine(2500, t) * np.exp(-50 * t) * 1.2
    def p_clv_2(self, t): return self.wt.sine(2800, t) * np.exp(-55 * t) * 1.2

    # [BASS SYNTHS]
    def b_sub_1(self, f, t): return self.wt.sine(f, t) * self.env(t, 0.05, 0.1, 0.8, 0.1) * 2.0 if f > 0 else np.zeros_like(t)
    def b_sub_2(self, f, t): return self.wt.triangle(f, t) * self.env(t, 0.05, 0.1, 0.8, 0.1) * 1.8 if f > 0 else np.zeros_like(t)
    def b_808_1(self, f, t): return self.fx.dist_soft(self.wt.sine(f, t) * np.exp(-2 * t)) * 1.5 if f > 0 else np.zeros_like(t)
    def b_808_2(self, f, t): return self.fx.dist_hard(self.wt.sine(f, t) * np.exp(-3 * t)) * 1.5 if f > 0 else np.zeros_like(t)
    def b_slp_1(self, f, t): return (self.wt.saw(f, t)*0.6 + self.wt.square(f, t)*0.4) * np.exp(-10 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def b_slp_2(self, f, t): return (self.wt.saw(f, t)*0.7 + self.wt.square(f, t)*0.3) * np.exp(-12 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def b_syn_1(self, f, t): return self.wt.square(f, t) * self.env(t, 0.02, 0.2, 0.3, 0.1) * 1.0 if f > 0 else np.zeros_like(t)
    def b_syn_2(self, f, t): return self.wt.pulse(f, t, 0.3) * self.env(t, 0.02, 0.2, 0.3, 0.1) * 1.0 if f > 0 else np.zeros_like(t)
    def b_res_1(self, f, t): return (self.wt.saw(f*0.98, t) + self.wt.saw(f*1.02, t)) * self.env(t, 0.1, 0.3, 0.8, 0.2) * 0.8 if f > 0 else np.zeros_like(t)
    def b_res_2(self, f, t): return (self.wt.saw(f*0.97, t) + self.wt.saw(f*1.03, t)) * self.env(t, 0.1, 0.4, 0.8, 0.3) * 0.8 if f > 0 else np.zeros_like(t)
    def b_acd_1(self, f, t): return self.fx.dist_hard(self.wt.saw(f, t) * self.env(t, 0.01, 0.1, 0.0, 0.1)) * 0.9 if f > 0 else np.zeros_like(t)
    def b_acd_2(self, f, t): return self.fx.dist_fuzz(self.wt.square(f, t) * self.env(t, 0.01, 0.1, 0.0, 0.1)) * 0.9 if f > 0 else np.zeros_like(t)
    def b_fm_1(self, f, t): return self.wt.fm_basic(f, f*2, 2.0, t) * self.env(t, 0.01, 0.2, 0.5, 0.1) * 1.2 if f > 0 else np.zeros_like(t)
    def b_fm_2(self, f, t): return self.wt.fm_basic(f, f*3, 3.0, t) * self.env(t, 0.01, 0.3, 0.5, 0.1) * 1.2 if f > 0 else np.zeros_like(t)
    def b_wob_1(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t), 500 + 400 * np.sin(3 * t)) * self.env(t, 0.1, 0.1, 0.8, 0.1) * 0.9 if f > 0 else np.zeros_like(t)
    def b_wob_2(self, f, t): return self.fx.lp_filter(self.wt.square(f, t), 600 + 500 * np.sin(4 * t)) * self.env(t, 0.1, 0.1, 0.8, 0.1) * 0.9 if f > 0 else np.zeros_like(t)
    def b_mog_1(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t) + self.wt.square(f*0.5, t), 800) * self.env(t, 0.05, 0.3, 0.5, 0.1) * 1.1 if f > 0 else np.zeros_like(t)
    def b_mog_2(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t) + self.wt.saw(f*0.5, t), 1000) * self.env(t, 0.05, 0.4, 0.5, 0.2) * 1.1 if f > 0 else np.zeros_like(t)
    def b_frt_1(self, f, t): return (self.wt.sine(f, t) + 0.3*self.wt.triangle(f*2, t)) * self.env(t, 0.1, 0.5, 0.6, 0.3) * 1.4 if f > 0 else np.zeros_like(t)
    def b_frt_2(self, f, t): return (self.wt.sine(f, t) + 0.4*self.wt.triangle(f*3, t)) * self.env(t, 0.2, 0.6, 0.6, 0.4) * 1.4 if f > 0 else np.zeros_like(t)

    # [KEYS & PIANOS]
    def k_pno_1(self, f, t): return self.wt.sine_harmonics(f, t, 4) * np.exp(-3 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def k_pno_2(self, f, t): return self.wt.sine_harmonics(f, t, 6) * np.exp(-4 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def k_rhd_1(self, f, t): return (self.wt.sine(f, t) + 0.5*self.wt.sine(f*3, t)) * self.env(t, 0.02, 0.5, 0.3, 0.4) * 1.1 if f > 0 else np.zeros_like(t)
    def k_rhd_2(self, f, t): return (self.wt.sine(f, t) + 0.6*self.wt.sine(f*4, t)) * self.env(t, 0.03, 0.6, 0.3, 0.5) * 1.1 if f > 0 else np.zeros_like(t)
    def k_dx7_1(self, f, t): return self.wt.fm_basic(f, f*4, 3.0*np.exp(-5*t), t) * np.exp(-2*t) * 1.0 if f > 0 else np.zeros_like(t)
    def k_dx7_2(self, f, t): return self.wt.fm_basic(f, f*5, 4.0*np.exp(-6*t), t) * np.exp(-3*t) * 1.0 if f > 0 else np.zeros_like(t)
    def k_ham_1(self, f, t): return self.fx.tremolo((self.wt.sine(f, t) + 0.8*self.wt.sine(f*1.5, t) + 0.5*self.wt.sine(f*3, t)) * self.env(t, 0.05, 0.1, 1.0, 0.1), 6, 0.4) * 0.6 if f > 0 else np.zeros_like(t)
    def k_ham_2(self, f, t): return self.fx.tremolo((self.wt.sine(f, t) + 0.9*self.wt.sine(f*2, t) + 0.6*self.wt.sine(f*4, t)) * self.env(t, 0.06, 0.2, 1.0, 0.2), 7, 0.5) * 0.6 if f > 0 else np.zeros_like(t)
    def k_chu_1(self, f, t): return self.fx.reverb_hall((self.wt.sine(f, t) + self.wt.sine(f*2, t) + self.wt.sine(f*4, t) + self.wt.sine(f*8, t)) * self.env(t, 0.1, 0.1, 1.0, 0.3)) * 0.5 if f > 0 else np.zeros_like(t)
    def k_chu_2(self, f, t): return self.fx.reverb_cathedral((self.wt.sine(f, t) + self.wt.sine(f*3, t) + self.wt.sine(f*5, t) + self.wt.sine(f*9, t)) * self.env(t, 0.2, 0.2, 1.0, 0.4)) * 0.5 if f > 0 else np.zeros_like(t)
    def k_clv_1(self, f, t): return self.wt.pulse(f, t, 0.15) * np.exp(-5 * t) * 0.8 if f > 0 else np.zeros_like(t)
    def k_clv_2(self, f, t): return self.wt.pulse(f, t, 0.25) * np.exp(-6 * t) * 0.8 if f > 0 else np.zeros_like(t)

    # [STRINGS & GUITARS]
    def g_aco_1(self, f, t): return self.pm.k_strong(f, t) * 1.5 if f > 0 else np.zeros_like(t)
    def g_aco_2(self, f, t): return self.pm.k_strong(f, t, 0.990) * 1.5 if f > 0 else np.zeros_like(t)
    def g_hrp_1(self, f, t): return self.pm.k_strong(f, t) * np.exp(-2 * t) * 1.8 if f > 0 else np.zeros_like(t)
    def g_hrp_2(self, f, t): return self.pm.k_strong(f, t, 0.998) * np.exp(-3 * t) * 1.8 if f > 0 else np.zeros_like(t)
    def g_nyl_1(self, f, t): return self.fx.lp_filter(self.pm.k_strong(f, t), 2000) * 1.6 if f > 0 else np.zeros_like(t)
    def g_nyl_2(self, f, t): return self.fx.lp_filter(self.pm.k_strong(f, t), 2500) * 1.6 if f > 0 else np.zeros_like(t)
    def g_ovd_1(self, f, t): return self.fx.dist_overdrive((self.wt.saw(f, t) + 0.5*self.wt.square(f, t)) * self.env(t, 0.05, 0.2, 0.8, 0.2)) * 0.4 if f > 0 else np.zeros_like(t)
    def g_ovd_2(self, f, t): return self.fx.dist_hard((self.wt.saw(f, t) + 0.6*self.wt.square(f, t)) * self.env(t, 0.06, 0.3, 0.8, 0.3)) * 0.4 if f > 0 else np.zeros_like(t)
    def g_fuz_1(self, f, t): return self.fx.dist_crush(self.fx.dist_fuzz(self.wt.square(f, t) * self.env(t, 0.01, 0.1, 0.9, 0.1))) * 0.3 if f > 0 else np.zeros_like(t)
    def g_fuz_2(self, f, t): return self.fx.bitcrush(self.fx.dist_fuzz(self.wt.square(f, t) * self.env(t, 0.02, 0.2, 0.9, 0.2)), 3, 6) * 0.3 if f > 0 else np.zeros_like(t)
    def s_syn_1(self, f, t): return (self.wt.saw(f*0.99, t) + self.wt.saw(f*1.01, t) + self.wt.saw(f, t)) * self.env(t, 0.4, 0.1, 0.9, 0.5) * 0.4 if f > 0 else np.zeros_like(t)
    def s_syn_2(self, f, t): return (self.wt.saw(f*0.98, t) + self.wt.saw(f*1.02, t) + self.wt.saw(f, t)) * self.env(t, 0.5, 0.2, 0.9, 0.6) * 0.4 if f > 0 else np.zeros_like(t)
    def s_vio_1(self, f, t): return self.wt.saw(f + (np.sin(6 * 2 * np.pi * t) * (f * 0.01)), t) * self.env(t, 0.2, 0.1, 0.9, 0.3) * 0.6 if f > 0 else np.zeros_like(t)
    def s_vio_2(self, f, t): return self.wt.saw(f + (np.sin(7 * 2 * np.pi * t) * (f * 0.02)), t) * self.env(t, 0.3, 0.2, 0.9, 0.4) * 0.6 if f > 0 else np.zeros_like(t)
    def s_cel_1(self, f, t): return self.fx.lp_filter((self.wt.saw(f, t) + self.wt.triangle(f, t)), 1500) * self.env(t, 0.3, 0.2, 0.8, 0.4) * 0.7 if f > 0 else np.zeros_like(t)
    def s_cel_2(self, f, t): return self.fx.lp_filter((self.wt.saw(f, t) + self.wt.triangle(f*0.5, t)), 1200) * self.env(t, 0.4, 0.3, 0.8, 0.5) * 0.7 if f > 0 else np.zeros_like(t)

    # [WINDS & BRASS]
    def w_flu_1(self, f, t): return (self.wt.sine(f, t) + 0.1*self.wt.noise_w(t)) * self.env(t, 0.2, 0.1, 0.9, 0.2) * 0.8 if f > 0 else np.zeros_like(t)
    def w_flu_2(self, f, t): return (self.wt.sine(f, t) + 0.2*self.wt.noise_w(t)) * self.env(t, 0.3, 0.2, 0.9, 0.3) * 0.8 if f > 0 else np.zeros_like(t)
    def w_tru_1(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t), 4000) * self.env(t, 0.05, 0.1, 0.9, 0.1) * 0.6 if f > 0 else np.zeros_like(t)
    def w_tru_2(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t), 5000) * self.env(t, 0.06, 0.2, 0.9, 0.2) * 0.6 if f > 0 else np.zeros_like(t)
    def w_brs_1(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t) + self.wt.saw(f*1.01, t), 3000) * self.env(t, 0.1, 0.1, 0.9, 0.2) * 0.7 if f > 0 else np.zeros_like(t)
    def w_brs_2(self, f, t): return self.fx.lp_filter(self.wt.saw(f, t) + self.wt.saw(f*1.02, t), 3500) * self.env(t, 0.2, 0.2, 0.9, 0.3) * 0.7 if f > 0 else np.zeros_like(t)
    def w_sax_1(self, f, t): return (self.wt.saw(f, t)*0.6 + self.wt.pulse(f, t, 0.3)*0.4) * self.env(t, 0.15, 0.2, 0.8, 0.2) * 0.6 if f > 0 else np.zeros_like(t)
    def w_sax_2(self, f, t): return (self.wt.saw(f, t)*0.7 + self.wt.pulse(f, t, 0.4)*0.3) * self.env(t, 0.25, 0.3, 0.8, 0.3) * 0.6 if f > 0 else np.zeros_like(t)
    def w_pan_1(self, f, t): return (self.wt.sine(f, t) + 0.3*self.wt.noise_w(t)) * self.env(t, 0.3, 0.1, 0.8, 0.3) * 0.9 if f > 0 else np.zeros_like(t)
    def w_pan_2(self, f, t): return (self.wt.sine(f, t) + 0.4*self.wt.noise_w(t)) * self.env(t, 0.4, 0.2, 0.8, 0.4) * 0.9 if f > 0 else np.zeros_like(t)

    # [SYNTH LEADS & PADS]
    def l_saw_1(self, f, t): return self.wt.saw(f, t) * self.env(t, 0.05, 0.1, 0.8, 0.2) * 0.5 if f > 0 else np.zeros_like(t)
    def l_saw_2(self, f, t): return self.wt.saw(f, t) * self.env(t, 0.06, 0.2, 0.8, 0.3) * 0.5 if f > 0 else np.zeros_like(t)
    def l_sqr_1(self, f, t): return self.wt.square(f, t) * self.env(t, 0.05, 0.1, 0.8, 0.2) * 0.4 if f > 0 else np.zeros_like(t)
    def l_sqr_2(self, f, t): return self.wt.square(f, t) * self.env(t, 0.06, 0.2, 0.8, 0.3) * 0.4 if f > 0 else np.zeros_like(t)
    def l_hvr_1(self, f, t): return self.fx.dist_soft((self.wt.saw(f, t) + self.wt.saw(f*1.02, t) + self.wt.saw(f*0.98, t) + self.wt.saw(f*2, t)) * self.env(t, 0.1, 0.2, 0.8, 0.2)) * 0.2 if f > 0 else np.zeros_like(t)
    def l_hvr_2(self, f, t): return self.fx.dist_hard((self.wt.saw(f, t) + self.wt.saw(f*1.03, t) + self.wt.saw(f*0.97, t) + self.wt.saw(f*2, t)) * self.env(t, 0.2, 0.3, 0.8, 0.3)) * 0.2 if f > 0 else np.zeros_like(t)
    def l_spr_1(self, f, t):
        if f <= 0: return np.zeros_like(t)
        s = self.wt.supersaw(f, t, detune=0.008)
        return s * self.env(t, 0.1, 0.1, 0.8, 0.2) * 0.25
    def l_spr_2(self, f, t):
        if f <= 0: return np.zeros_like(t)
        s = self.wt.supersaw(f, t, detune=0.015, count=7)
        return s * self.env(t, 0.2, 0.2, 0.8, 0.3) * 0.2
    def p_wrm_1(self, f, t): return self.fx.reverb_hall((self.wt.sine(f, t) + 0.5*self.wt.triangle(f*1.02, t) + 0.5*self.wt.triangle(f*0.98, t)) * self.env(t, 0.8, 0.5, 0.8, 0.8)) * 0.3 if f > 0 else np.zeros_like(t)
    def p_wrm_2(self, f, t): return self.fx.reverb_plate((self.wt.sine(f, t) + 0.6*self.wt.triangle(f*1.03, t) + 0.6*self.wt.triangle(f*0.97, t)) * self.env(t, 0.9, 0.6, 0.8, 0.9)) * 0.3 if f > 0 else np.zeros_like(t)
    def p_cho_1(self, f, t): return self.fx.lp_filter((self.wt.triangle(f, t) + self.wt.noise_w(t)*0.02) * self.env(t, 1.0, 0.2, 0.9, 1.0), 3000) * 0.5 if f > 0 else np.zeros_like(t)
    def p_cho_2(self, f, t): return self.fx.lp_filter((self.wt.triangle(f, t) + self.wt.noise_w(t)*0.03) * self.env(t, 1.2, 0.3, 0.9, 1.2), 3500) * 0.5 if f > 0 else np.zeros_like(t)
    def l_plk_1(self, f, t): return self.wt.sine(f, t) * np.exp(-10 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def l_plk_2(self, f, t): return self.wt.sine(f, t) * np.exp(-12 * t) * 1.2 if f > 0 else np.zeros_like(t)
    def l_pfm_1(self, f, t): return self.wt.fm_basic(f, f*3.5, 4.0*np.exp(-15*t), t) * np.exp(-5*t) * 1.0 if f > 0 else np.zeros_like(t)
    def l_pfm_2(self, f, t): return self.wt.fm_basic(f, f*4.5, 5.0*np.exp(-18*t), t) * np.exp(-6*t) * 1.0 if f > 0 else np.zeros_like(t)
    def l_8bt_1(self, f, t): return self.wt.square(f, t) * np.exp(-15 * t) * 0.5 if f > 0 else np.zeros_like(t)
    def l_8bt_2(self, f, t): return self.wt.square(f, t) * np.exp(-18 * t) * 0.5 if f > 0 else np.zeros_like(t)

    # [AMBIENT & NATURE FX]
    def x_wnd_1(self, t): return self.fx.lp_filter(self.wt.noise_w(t) * ((1000 + 800 * np.sin(0.2 * 2 * np.pi * t) + 400 * np.sin(0.5 * 2 * np.pi * t)) / 2000.0), 1500) * self.env(t, 2.0, 1.0, 0.8, 2.0) * 0.7
    def x_wnd_2(self, t): return self.fx.lp_filter(self.wt.noise_w(t) * ((1200 + 900 * np.sin(0.3 * 2 * np.pi * t) + 500 * np.sin(0.6 * 2 * np.pi * t)) / 2500.0), 1800) * self.env(t, 2.5, 1.5, 0.8, 2.5) * 0.7
    def x_ran_1(self, t): return ((self.wt.noise_w(t) * (self.wt.noise_w(t) > 0.8)) * 0.5 + self.fx.lp_filter(self.wt.noise_w(t), 800) * 0.2) * self.env(t, 0.5, 0.5, 1.0, 1.0) * 0.6
    def x_ran_2(self, t): return ((self.wt.noise_w(t) * (self.wt.noise_w(t) > 0.85)) * 0.6 + self.fx.lp_filter(self.wt.noise_w(t), 900) * 0.3) * self.env(t, 0.6, 0.6, 1.0, 1.0) * 0.6
    def x_ocn_1(self, t): return self.fx.lp_filter(self.wt.noise_w(t), 600 + 400 * (0.5 + 0.5 * np.sin(0.15 * 2 * np.pi * t))) * (0.5 + 0.5 * np.sin(0.15 * 2 * np.pi * t)) * self.env(t, 2.0, 1.0, 0.9, 3.0) * 0.8
    def x_ocn_2(self, t): return self.fx.lp_filter(self.wt.noise_w(t), 700 + 500 * (0.5 + 0.5 * np.sin(0.20 * 2 * np.pi * t))) * (0.5 + 0.5 * np.sin(0.20 * 2 * np.pi * t)) * self.env(t, 2.5, 1.5, 0.9, 3.5) * 0.8
    def x_thn_1(self, t): return self.fx.reverb_hall(self.fx.dist_hard(self.fx.lp_filter(self.wt.noise_w(t), 400) * np.exp(-1 * t)) * self.env(t, 0.01, 1.0, 0.5, 3.0)) * 2.0
    def x_thn_2(self, t): return self.fx.reverb_cathedral(self.fx.dist_fuzz(self.fx.lp_filter(self.wt.noise_w(t), 500) * np.exp(-1.5 * t)) * self.env(t, 0.02, 1.5, 0.5, 3.5)) * 2.0
    def x_fir_1(self, t): return (self.fx.lp_filter(self.wt.noise_w(t), 300) * 0.3 + (self.wt.noise_w(t) * (np.random.uniform(0, 1, len(t)) > 0.995) * np.exp(-50 * t)) * 1.5) * self.env(t, 0.1, 0.1, 1.0, 0.1) * 0.8
    def x_fir_2(self, t): return (self.fx.lp_filter(self.wt.noise_w(t), 400) * 0.4 + (self.wt.noise_w(t) * (np.random.uniform(0, 1, len(t)) > 0.990) * np.exp(-60 * t)) * 1.6) * self.env(t, 0.2, 0.2, 1.0, 0.2) * 0.8

    # [GAME FX]
    def g_lsr_1(self, t): return self.wt.square(np.linspace(2000, 100, len(t)), t) * np.exp(-15 * t) * 0.8
    def g_lsr_2(self, t): return self.wt.square(np.linspace(2500, 150, len(t)), t) * np.exp(-18 * t) * 0.8
    def g_exp_1(self, t): return self.fx.lp_filter(self.fx.bitcrush(self.wt.noise_w(t), 3, 8), 1000) * np.exp(-4 * t) * 1.5
    def g_exp_2(self, t): return self.fx.lp_filter(self.fx.bitcrush(self.wt.noise_w(t), 4, 10), 1200) * np.exp(-5 * t) * 1.5
    def g_jmp_1(self, t): return self.wt.pulse(np.linspace(300, 800, len(t)), t, 0.5) * np.exp(-10 * t) * 0.7
    def g_jmp_2(self, t): return self.wt.pulse(np.linspace(400, 900, len(t)), t, 0.6) * np.exp(-12 * t) * 0.7
    def g_con_1(self, t):
        s = np.zeros_like(t)
        y = len(t) // 6
        if y > 0: 
            s[:y] = self.wt.square(987, t[:y])
            s[y:y*3] = self.wt.square(1318, t[y:y*3])
        return s * np.exp(-10 * t) * 0.6
    def g_con_2(self, t):
        s = np.zeros_like(t)
        y = len(t) // 6
        if y > 0: 
            s[:y] = self.wt.square(1000, t[:y])
            s[y:y*3] = self.wt.square(1400, t[y:y*3])
        return s * np.exp(-12 * t) * 0.6
    def g_hcp_1(self, t): return self.fx.lp_filter(self.wt.noise_w(t), 400) * (self.wt.square(12, t) > 0) * self.env(t, 0.5, 1.0, 0.8, 1.0) * 1.5
    def g_hcp_2(self, t): return self.fx.lp_filter(self.wt.noise_w(t), 500) * (self.wt.square(15, t) > 0) * self.env(t, 0.6, 1.2, 0.8, 1.2) * 1.5
    def g_ufo_1(self, t): return self.wt.sine(500 + 200 * np.sin(5 * 2 * np.pi * t), t) * self.env(t, 0.5, 1.0, 0.8, 0.5) * 0.5
    def g_ufo_2(self, t): return self.wt.sine(600 + 300 * np.sin(6 * 2 * np.pi * t), t) * self.env(t, 0.6, 1.2, 0.8, 0.6) * 0.5

    def _map_instruments(self):
        return {
            "kick_808": (self.k_808_1, True), "kick_909": (self.k_909_1, True), "kick_aco": (self.k_aco_1, True), "kick_pnc": (self.k_pnc_1, True), "kick_lof": (self.k_lof_1, True), "kick_tec": (self.k_tec_1, True), "kick_dep": (self.k_dep_1, True),
            "snare_aco": (self.s_aco_1, True), "snare_ele": (self.s_ele_1, True), "snare_808": (self.s_808_1, True), "snare_trp": (self.s_trp_1, True), "clap_bsc": (self.c_bsc_1, True), "clap_rvb": (self.c_rvb_1, True), "rimshot": (self.r_sht_1, True),
            "hihat_cl": (self.h_cl_1, True), "hihat_op": (self.h_op_1, True), "cym_cr": (self.cy_cr_1, True), "cym_rd": (self.cy_rd_1, True),
            "tom_hi": (self.t_hi_1, True), "tom_lo": (self.t_lo_1, True), "bongo": (self.p_bgo_1, True), "cowbell": (self.p_cwb_1, True), "shaker": (self.p_shk_1, True), "claves": (self.p_clv_1, True),
            "fx_wind": (self.x_wnd_1, True), "fx_rain": (self.x_ran_1, True), "fx_ocean": (self.x_ocn_1, True), "fx_thunder": (self.x_thn_1, True), "fx_fire": (self.x_fir_1, True),
            "fx_laser": (self.g_lsr_1, True), "fx_explosion": (self.g_exp_1, True), "fx_jump": (self.g_jmp_1, True), "fx_coin": (self.g_con_1, True), "fx_helicopter": (self.g_hcp_1, True), "fx_ufo": (self.g_ufo_1, True),
            
            "bass_sub": (self.b_sub_1, False), "bass_808": (self.b_808_1, False), "bass_slap": (self.b_slp_1, False), "bass_syn": (self.b_syn_1, False), "bass_res": (self.b_res_1, False), "bass_acd": (self.b_acd_1, False), "bass_fm": (self.b_fm_1, False), "bass_wob": (self.b_wob_1, False), "bass_mog": (self.b_mog_1, False), "bass_frt": (self.b_frt_1, False),
            "piano_grd": (self.k_pno_1, False), "piano_rhd": (self.k_rhd_1, False), "piano_dx7": (self.k_dx7_1, False), "organ_ham": (self.k_ham_1, False), "organ_chu": (self.k_chu_1, False), "clavinet": (self.k_clv_1, False),
            "guit_aco": (self.g_aco_1, False), "guit_nyl": (self.g_nyl_1, False), "guit_ovd": (self.g_ovd_1, False), "guit_fuz": (self.g_fuz_1, False), "harp": (self.g_hrp_1, False), "str_syn": (self.s_syn_1, False), "violin": (self.s_vio_1, False), "cello": (self.s_cel_1, False),
            "flute": (self.w_flu_1, False), "trumpet": (self.w_tru_1, False), "brass": (self.w_brs_1, False), "sax": (self.w_sax_1, False), "pan_flu": (self.w_pan_1, False),
            "lead_saw": (self.l_saw_1, False), "lead_sqr": (self.l_sqr_1, False), "lead_hvr": (self.l_hvr_1, False), "lead_spr": (self.l_spr_1, False), "pad_wrm": (self.p_wrm_1, False), "pad_cho": (self.p_cho_1, False), "pluck_sin": (self.l_plk_1, False), "pluck_fm": (self.l_pfm_1, False), "arp_8bt": (self.l_8bt_1, False),

            "kick_808_2": (self.k_808_2, True), "kick_909_2": (self.k_909_2, True), "kick_aco_2": (self.k_aco_2, True), "kick_pnc_2": (self.k_pnc_2, True), "kick_lof_2": (self.k_lof_2, True), "kick_tec_2": (self.k_tec_2, True), "kick_dep_2": (self.k_dep_2, True),
            "snare_aco_2": (self.s_aco_2, True), "snare_ele_2": (self.s_ele_2, True), "snare_808_2": (self.s_808_2, True), "snare_trp_2": (self.s_trp_2, True), "clap_bsc_2": (self.c_bsc_2, True), "clap_rvb_2": (self.c_rvb_2, True), "rimshot_2": (self.r_sht_2, True),
            "hihat_cl_2": (self.h_cl_2, True), "hihat_op_2": (self.h_op_2, True), "cym_cr_2": (self.cy_cr_2, True), "cym_rd_2": (self.cy_rd_2, True),
            "tom_hi_2": (self.t_hi_2, True), "tom_lo_2": (self.t_lo_2, True), "bongo_2": (self.p_bgo_2, True), "cowbell_2": (self.p_cwb_2, True), "shaker_2": (self.p_shk_2, True), "claves_2": (self.p_clv_2, True),
            "fx_wind_2": (self.x_wnd_2, True), "fx_rain_2": (self.x_ran_2, True), "fx_ocean_2": (self.x_ocn_2, True), "fx_thunder_2": (self.x_thn_2, True), "fx_fire_2": (self.x_fir_2, True),
            "fx_laser_2": (self.g_lsr_2, True), "fx_explosion_2": (self.g_exp_2, True), "fx_jump_2": (self.g_jmp_2, True), "fx_coin_2": (self.g_con_2, True), "fx_helicopter_2": (self.g_hcp_2, True), "fx_ufo_2": (self.g_ufo_2, True),
            
            "bass_sub_2": (self.b_sub_2, False), "bass_808_2": (self.b_808_2, False), "bass_slap_2": (self.b_slp_2, False), "bass_syn_2": (self.b_syn_2, False), "bass_res_2": (self.b_res_2, False), "bass_acd_2": (self.b_acd_2, False), "bass_fm_2": (self.b_fm_2, False), "bass_wob_2": (self.b_wob_2, False), "bass_mog_2": (self.b_mog_2, False), "bass_frt_2": (self.b_frt_2, False),
            "piano_grd_2": (self.k_pno_2, False), "piano_rhd_2": (self.k_rhd_2, False), "piano_dx7_2": (self.k_dx7_2, False), "organ_ham_2": (self.k_ham_2, False), "organ_chu_2": (self.k_chu_2, False), "clavinet_2": (self.k_clv_2, False),
            "guit_aco_2": (self.g_aco_2, False), "guit_nyl_2": (self.g_nyl_2, False), "guit_ovd_2": (self.g_ovd_2, False), "guit_fuz_2": (self.g_fuz_2, False), "harp_2": (self.g_hrp_2, False), "str_syn_2": (self.s_syn_2, False), "violin_2": (self.s_vio_2, False), "cello_2": (self.s_cel_2, False),
            "flute_2": (self.w_flu_2, False), "trumpet_2": (self.w_tru_2, False), "brass_2": (self.w_brs_2, False), "sax_2": (self.w_sax_2, False), "pan_flu_2": (self.w_pan_2, False),
            "lead_saw_2": (self.l_saw_2, False), "lead_sqr_2": (self.l_sqr_2, False), "lead_hvr_2": (self.l_hvr_2, False), "lead_spr_2": (self.l_spr_2, False), "pad_wrm_2": (self.p_wrm_2, False), "pad_cho_2": (self.p_cho_2, False), "pluck_sin_2": (self.l_plk_2, False), "pluck_fm_2": (self.l_pfm_2, False), "arp_8bt_2": (self.l_8bt_2, False)
        }

    # =====================================================================
    # ANA MASTER RENDER MOTORU
    # =====================================================================
    def render(self, sarki_verisi, hedef_dakika=2):
        tempo = sarki_verisi.get("tempo", 120)
        global_fx = sarki_verisi.get("global_fx", [])
        adim_suresi = (60.0 / tempo) / 4.0
        loop_suresi = 16 * adim_suresi
        tekrar_sayisi = max(4, int((hedef_dakika * 60) / loop_suresi))
        samples_per_step = int(self.sr * adim_suresi)
        
        toplam_samples = tekrar_sayisi * 16 * samples_per_step
        master_ses = np.zeros(toplam_samples, dtype=np.float32)
        
        def g_lst(isim):
            l = sarki_verisi.get(isim, ["-"]*16)
            if len(l) < 16: l += ["-"] * (16 - len(l))
            return l

        aktif = {}
        for k, v in sarki_verisi.items():
            if k in self.inst:
                aktif[k] = (g_lst(k), self.inst[k][0], self.inst[k][1])

        t_dizi = np.linspace(0, adim_suresi, samples_per_step, endpoint=False)

        # Gelişmiş Yapay Aranjman Katmanı
        for loop_idx in range(tekrar_sayisi):
            c_int = loop_idx < int(tekrar_sayisi * 0.15)
            c_bld = int(tekrar_sayisi * 0.15) <= loop_idx < int(tekrar_sayisi * 0.3)
            c_drp = int(tekrar_sayisi * 0.3) <= loop_idx < int(tekrar_sayisi * 0.6)
            c_brd = int(tekrar_sayisi * 0.6) <= loop_idx < int(tekrar_sayisi * 0.75)
            c_dr2 = int(tekrar_sayisi * 0.75) <= loop_idx < int(tekrar_sayisi * 0.9)
            
            d_akt = c_bld or c_drp or c_dr2
            b_akt = c_drp or c_dr2 or (c_brd and loop_idx % 2 == 0)
            l_akt = c_drp or c_dr2 or c_int
            p_akt = True 
            
            for i in range(16):
                zb = (loop_idx * 16 + i) * samples_per_step
                ze = zb + samples_per_step
                katman = np.zeros(samples_per_step, dtype=np.float32)
                
                for kanal_adi, (n_lst, fnc, is_drum) in aktif.items():
                    n_ist = n_lst[i]
                    if n_ist == "-": continue
                    
                    if is_drum:
                        if not d_akt and "kick" in kanal_adi: continue
                        # Davul kanalına özgü filtreler veya sıkıştırma uygulanabilir
                        signal = fnc(t_dizi)
                        katman += signal
                    else:
                        if "bass" in kanal_adi and not b_akt: continue
                        if ("lead" in kanal_adi or "guit" in kanal_adi or "piano" in kanal_adi) and not l_akt: continue
                        if "pad" in kanal_adi and not p_akt: continue
                        
                        frq = self.notes.get(n_ist, 0.0)
                        signal = fnc(frq, t_dizi)
                        katman += signal
                
                master_ses[zb:ze] += katman

        # GLOBAL MASTERING FX PROCESSOR CHAIN
        if "compressor" in global_fx:
            master_ses = self.fx.compressor(master_ses, threshold=0.25, ratio=4.0)
        if "chorus" in global_fx:
            master_ses = self.fx.chorus(master_ses, freq=1.0, depth=0.002)
        if "flanger" in global_fx:
            master_ses = self.fx.flanger(master_ses, freq=0.2, depth=0.003)
        if "phaser" in global_fx:
            master_ses = self.fx.phaser(master_ses, freq=0.5, depth=0.5)
        if "reverb" in global_fx:
            master_ses = self.fx.reverb_room(master_ses)

        # Fade Out ve Hard Limiter Mastering
        fos = int(self.sr * 10) 
        if fos < len(master_ses): 
            master_ses[-fos:] *= np.linspace(1, 0, fos)
        
        mv = np.max(np.abs(master_ses))
        if mv > 0: 
            master_ses = np.int16(master_ses / mv * 32767 * 0.95) 
        else: 
            master_ses = np.int16(master_ses)
            
        byte_io = io.BytesIO()
        wav.write(byte_io, self.sr, master_ses)
        return byte_io.getvalue()

def motoru_calistir(sarki_verisi, hedef_dakika=2):
    m = ColossusEngine()
    return m.render(sarki_verisi, hedef_dakika)

# Örnek Kullanım ve Entegrasyon Test Şablonu
if __name__ == "__main__":
    test_song = {
        "tempo": 128,
        "global_fx": ["compressor", "chorus"],
        "kick_808":  ["X", "-", "-", "-", "X", "-", "-", "-", "X", "-", "-", "-", "X", "-", "-", "-"],
        "hihat_cl":  ["-", "X", "-", "X", "-", "X", "-", "X", "-", "X", "-", "X", "-", "X", "-", "X"],
        "bass_sub":  ["A1", "A1", "-", "G1", "C2", "-", "-", "D2", "A1", "-", "-", "-", "E1", "-", "-", "-"],
        "lead_spr":  ["A4", "-", "B4", "C5", "-", "E5", "-", "D5", "A4", "-", "B4", "C5", "-", "G5", "-", "-"],
        "pad_wrm":   ["A3", "-", "-", "-", "-", "-", "-", "-", "C3", "-", "-", "-", "G3", "-", "-", "-"]
    }
    # Test çalıştırması (Çıktıyı kaydetmek isterseniz byte verisini dosyaya yazabilirsiniz)
    wav_bytes = motoru_calistir(test_song, hedef_dakika=0.5)
    print(f"Sentez Tamamlandı! Toplam Boyut: {len(wav_bytes)} byte.")
