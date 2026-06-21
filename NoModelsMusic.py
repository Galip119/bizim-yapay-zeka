import numpy as np
import scipy.io.wavfile as wav
import io

# =====================================================================
# NOMODELSMUSIC V3 - ULTIMATE MEGA STUDIO EDITION 
# SIFIR YAPAY ZEKA MODELİ - %100 MATEMATİKSEL FİZİK MODELLEME
# =====================================================================

class DSP_Effects:
    def __init__(self, sample_rate):
        self.sr = sample_rate

    def delay(self, ses, gecikme_saniye=0.3, azalma=0.5, tekrar=4):
        gecikme_sample = int(gecikme_saniye * self.sr)
        yeni_ses = np.copy(ses)
        for i in range(1, tekrar + 1):
            if i * gecikme_sample < len(yeni_ses):
                yeni_ses[i * gecikme_sample:] += ses[:-i * gecikme_sample] * (azalma ** i)
        return yeni_ses

    def reverb_basit(self, ses, oda_boyutu=0.8):
        delays = [int(0.015 * self.sr), int(0.022 * self.sr), int(0.035 * self.sr), int(0.041 * self.sr)]
        yeni_ses = np.copy(ses)
        for d in delays:
            if d < len(ses):
                yeni_ses[d:] += ses[:-d] * oda_boyutu
        return self.lowpass_filter(yeni_ses, 5000)

    def distortion(self, ses, gain=10.0, mix=0.8):
        distorted = np.tanh(ses * gain) / np.tanh(gain)
        return (ses * (1 - mix)) + (distorted * mix)

    def bitcrush(self, ses, bit_derinligi=4, downsample=4):
        step = 2.0 ** bit_derinligi
        crushed = np.round(ses * step) / step
        if downsample > 1:
            crushed[1::downsample] = crushed[0::downsample]
        return crushed

    def lowpass_filter(self, ses, kesme_frekansi=2000):
        rc = 1.0 / (2 * np.pi * kesme_frekansi)
        dt = 1.0 / self.sr
        alpha = dt / (rc + dt)
        filtreli = np.zeros_like(ses)
        filtreli[0] = ses[0]
        for i in range(1, len(ses)):
            filtreli[i] = alpha * ses[i] + (1 - alpha) * filtreli[i-1]
        return filtreli

    def tremolo(self, ses, hiz=5, derinlik=0.5):
        t = np.arange(len(ses)) / self.sr
        lfo = 1.0 - derinlik * 0.5 * (1.0 + np.sin(2 * np.pi * hiz * t))
        return ses * lfo

class NoModelsMusicEngine:
    def __init__(self, sample_rate=44100):
        self.sr = sample_rate
        self.efektler = DSP_Effects(self.sr)
        self.notalar = self._mega_nota_sozlugu_olustur()

    def _mega_nota_sozlugu_olustur(self):
        notalar_listesi = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        sozluk = {"-": 0.0}
        for oktav in range(0, 10):
            for i, nota in enumerate(notalar_listesi):
                n = (oktav - 4) * 12 + (i - 9) 
                sozluk[f"{nota}{oktav}"] = 440.0 * (2.0 ** (n / 12.0))
        return sozluk

    def sine(self, f, t): return np.sin(2 * np.pi * f * t)
    def square(self, f, t): return np.sign(np.sin(2 * np.pi * f * t))
    def saw(self, f, t): return 2 * (t * f - np.floor(t * f + 0.5))
    def triangle(self, f, t): return 2 * np.abs(2 * (t * f - np.floor(t * f + 0.5))) - 1
    def noise_white(self, t): return np.random.uniform(-1, 1, len(t))
    def pulse(self, f, t, width=0.3): return np.where((t * f) % 1 < width, 1.0, -1.0)

    def adsr(self, t, a, d, s, r):
        zaman_a, zaman_d, zaman_r = int(a * self.sr), int(d * self.sr), int(r * self.sr)
        zarf = np.ones_like(t)
        toplam = len(t)
        if zaman_a > 0: zarf[:zaman_a] = np.linspace(0, 1, zaman_a)
        if zaman_d > 0 and zaman_a + zaman_d < toplam:
            zarf[zaman_a:zaman_a+zaman_d] = np.linspace(1, s, zaman_d)
            zarf[zaman_a+zaman_d:] = s
        if zaman_r > 0 and toplam - zaman_r > 0:
            zarf[-zaman_r:] = np.linspace(s, 0, zaman_r)
        return zarf

    # --- DAVULLAR VE KICKLER ---
    def kick_808(self, t): return self.sine(np.linspace(150, 20, len(t)), t) * self.adsr(t, 0.01, 0.4, 0.0, 0.1) * 2.5
    def kick_909(self, t): return self.efektler.distortion(self.sine(np.linspace(200, 40, len(t)), t) * np.exp(-15 * t), 2.0) * 1.8
    def kick_acoustic(self, t): return self.sine(np.linspace(100, 50, len(t)), t) * np.exp(-25 * t) * 2.0
    def kick_punchy(self, t): return (self.sine(np.linspace(300, 40, len(t)), t) + self.noise_white(t)*0.1) * np.exp(-30 * t) * 2.2
    def kick_lofi(self, t): return self.efektler.bitcrush(self.sine(np.linspace(120, 30, len(t)), t) * np.exp(-10 * t), 4) * 1.5
    def kick_techno(self, t): return self.saw(np.linspace(150, 40, len(t)), t) * np.exp(-20 * t) * 1.4
    def kick_deep(self, t): return self.sine(np.linspace(80, 20, len(t)), t) * np.exp(-8 * t) * 2.5

    def snare_acoustic(self, t): return (self.sine(np.linspace(250, 180, len(t)), t) * 0.4 + self.noise_white(t) * 0.6) * np.exp(-25 * t) * 1.5
    def snare_electronic(self, t): return (self.triangle(np.linspace(300, 200, len(t)), t) * 0.5 + self.noise_white(t) * 0.8) * np.exp(-30 * t) * 1.4
    def snare_808(self, t): return (self.sine(np.linspace(350, 250, len(t)), t) * 0.7 + self.noise_white(t) * 0.3) * np.exp(-20 * t) * 1.2
    def snare_trap(self, t): return self.efektler.lowpass_filter(self.noise_white(t) * np.exp(-40 * t) * 2.0, 8000)
    def clap_basic(self, t): return self.noise_white(t) * np.exp(-35 * t) * (self.sine(40, t) > 0) * 1.5
    def clap_layered(self, t): return self.efektler.reverb_basit(self.noise_white(t) * np.exp(-25 * t) * (self.sine(60, t) > 0.5)) * 1.3
    def rimshot(self, t): return self.sine(np.linspace(800, 600, len(t)), t) * np.exp(-40 * t) * 1.5

    def hihat_closed(self, t): return self.efektler.lowpass_filter(self.noise_white(t), 12000) * np.exp(-60 * t) * 0.8
    def hihat_open(self, t): return self.efektler.lowpass_filter(self.noise_white(t), 10000) * np.exp(-10 * t) * 0.6
    def hihat_808(self, t): return self.noise_white(t) * np.exp(-45 * t) * 0.9
    def hihat_trap(self, t): return self.efektler.bitcrush(self.noise_white(t) * np.exp(-70 * t), 6) * 1.0
    def crash_cymbal(self, t): return self.noise_white(t) * np.exp(-3 * t) * 1.2
    def ride_cymbal(self, t): return (self.noise_white(t) * 0.4 + self.sine(500, t) * 0.1) * np.exp(-4 * t) * 0.9
    def splash_cymbal(self, t): return self.noise_white(t) * np.exp(-8 * t) * 1.1

    def tom_high(self, t): return self.sine(np.linspace(250, 150, len(t)), t) * np.exp(-15 * t) * 1.6
    def tom_mid(self, t): return self.sine(np.linspace(150, 90, len(t)), t) * np.exp(-12 * t) * 1.8
    def tom_low(self, t): return self.sine(np.linspace(100, 60, len(t)), t) * np.exp(-10 * t) * 2.0
    def bongo_high(self, t): return self.sine(np.linspace(400, 350, len(t)), t) * np.exp(-20 * t) * 1.4
    def bongo_low(self, t): return self.sine(np.linspace(300, 250, len(t)), t) * np.exp(-18 * t) * 1.5
    def cowbell(self, t): return (self.sine(800, t) + self.sine(540, t)) * np.exp(-15 * t) * 1.0
    def woodblock(self, t): return self.square(np.linspace(1000, 800, len(t)), t) * np.exp(-40 * t) * 0.8
    def shaker(self, t): return self.noise_white(t) * np.exp(-20 * t) * (self.sine(10, t) > 0) * 0.5
    def tambourine(self, t): return self.efektler.lowpass_filter(self.noise_white(t) * np.exp(-15 * t) * (self.sine(15, t)>0), 8000) * 0.7
    def triangle_perc(self, t): return self.sine(4000, t) * np.exp(-5 * t) * 0.6
    def claves(self, t): return self.sine(2500, t) * np.exp(-50 * t) * 1.2
    def guiro(self, t): return self.noise_white(t) * self.saw(10, t) * np.exp(-5 * t) * 0.5
    def maracas(self, t): return self.noise_white(t) * np.exp(-30 * t) * 0.6

    # --- BAS ENSTRÜMANLARI ---
    def sub_bass(self, f, t): return self.sine(f, t) * self.adsr(t, 0.05, 0.1, 0.8, 0.1) * 1.8 if f > 0 else 0
    def slap_bass(self, f, t): return (self.saw(f, t)*0.6 + self.square(f, t)*0.4) * np.exp(-10 * t) * 1.2 if f > 0 else 0
    def synth_bass(self, f, t): return self.square(f, t) * self.adsr(t, 0.02, 0.2, 0.3, 0.1) * 1.0 if f > 0 else 0
    def reese_bass(self, f, t): return (self.saw(f*0.98, t) + self.saw(f*1.02, t)) * self.adsr(t, 0.1, 0.3, 0.8, 0.2) * 0.8 if f > 0 else 0
    def acid_bass(self, f, t): return self.efektler.distortion(self.saw(f, t) * self.adsr(t, 0.01, 0.1, 0.0, 0.1), 3.0) * 0.9 if f > 0 else 0
    def fm_bass(self, f, t): return self.sine(f + self.sine(f*2, t)*100, t) * self.adsr(t, 0.01, 0.2, 0.5, 0.1) * 1.2 if f > 0 else 0
    def upright_bass(self, f, t): return (self.sine(f, t) + 0.3*self.triangle(f*2, t)) * np.exp(-4 * t) * 1.5 if f > 0 else 0
    def fretless_bass(self, f, t): return self.sine(f, t) * self.adsr(t, 0.1, 0.5, 0.6, 0.3) * 1.4 if f > 0 else 0
    def moog_bass(self, f, t): return self.efektler.lowpass_filter(self.saw(f, t) * self.adsr(t, 0.05, 0.3, 0.5, 0.1), 1000) * 1.1 if f > 0 else 0
    def wobble_bass(self, f, t): 
        lfo = 500 + 400 * self.sine(3, t)
        return self.efektler.lowpass_filter(self.saw(f, t), np.mean(lfo)) * self.adsr(t, 0.1, 0.1, 0.8, 0.1) * 0.9 if f > 0 else 0

    # --- PİYANOLAR VE KLAVYELER ---
    def grand_piano(self, f, t):
        if f == 0: return 0
        ses = self.sine(f, t) + 0.4*self.sine(f*2, t) + 0.2*self.sine(f*3, t) + 0.1*self.sine(f*4, t)
        return ses * np.exp(-3 * t) * 1.2
    def upright_piano(self, f, t):
        if f == 0: return 0
        ses = self.sine(f, t) + 0.5*self.triangle(f*2, t) + 0.1*self.noise_white(t[:len(t)//10])
        return ses * np.exp(-4 * t) * 1.0
    def rhodes_piano(self, f, t):
        if f == 0: return 0
        return (self.sine(f, t) + 0.5*self.sine(f*3, t)) * self.adsr(t, 0.02, 0.5, 0.3, 0.4) * 1.1
    def wurlitzer(self, f, t):
        if f == 0: return 0
        return self.efektler.distortion((self.triangle(f, t) + 0.3*self.square(f*2, t)) * np.exp(-3 * t), 1.5) * 0.9
    def dx7_piano(self, f, t):
        if f == 0: return 0
        return self.sine(f + 200*self.sine(f*4, t)*np.exp(-5*t), t) * np.exp(-2*t) * 1.0
    def clavinet(self, f, t):
        if f == 0: return 0
        return self.pulse(f, t, 0.1) * np.exp(-5 * t) * 0.8
    def harpsichord(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * np.exp(-6 * t) * 0.7
    def celesta(self, f, t):
        if f == 0: return 0
        return self.sine(f, t) * np.exp(-2 * t) * 0.9
    def church_organ(self, f, t):
        if f == 0: return 0
        ses = self.sine(f, t) + self.sine(f*2, t) + self.sine(f*4, t) + self.sine(f*8, t)
        return self.efektler.reverb_basit(ses * self.adsr(t, 0.1, 0.1, 1.0, 0.3) * 0.5)
    def hammond_organ(self, f, t):
        if f == 0: return 0
        ses = self.sine(f, t) + 0.8*self.sine(f*1.5, t) + 0.5*self.sine(f*3, t)
        return self.efektler.tremolo(ses * self.adsr(t, 0.05, 0.1, 1.0, 0.1), hiz=6, derinlik=0.4) * 0.6
    def reed_organ(self, f, t):
        if f == 0: return 0
        return self.triangle(f, t) * self.adsr(t, 0.2, 0.1, 1.0, 0.2) * 0.8

    # --- YAYLILAR VE ORKESTRA ---
    def violin(self, f, t):
        if f == 0: return 0
        vibrato = self.sine(6, t) * (f * 0.01)
        return self.saw(f + vibrato, t) * self.adsr(t, 0.2, 0.1, 0.9, 0.3) * 0.6
    def cello(self, f, t):
        if f == 0: return 0
        vibrato = self.sine(4, t) * (f * 0.01)
        return (self.saw(f + vibrato, t) + self.triangle(f, t)) * self.adsr(t, 0.3, 0.2, 0.8, 0.4) * 0.7
    def contrabass(self, f, t):
        if f == 0: return 0
        return (self.saw(f, t)*0.5 + self.sine(f, t)*0.5) * self.adsr(t, 0.4, 0.2, 0.8, 0.5) * 0.9
    def pizzicato(self, f, t):
        if f == 0: return 0
        return self.triangle(f, t) * np.exp(-15 * t) * 1.2
    def harp(self, f, t):
        if f == 0: return 0
        return (self.sine(f, t) + 0.2*self.saw(f, t)) * np.exp(-4 * t) * 1.0
    def timpani(self, f, t):
        if f == 0: return 0
        return self.sine(f, t) * np.exp(-3 * t) * 2.0
    def brass_section(self, f, t):
        if f == 0: return 0
        return self.efektler.lowpass_filter(self.saw(f, t) + self.saw(f*1.01, t), 3000) * self.adsr(t, 0.1, 0.1, 0.9, 0.2) * 0.7
    def french_horn(self, f, t):
        if f == 0: return 0
        return self.triangle(f, t) * self.adsr(t, 0.2, 0.1, 0.8, 0.3) * 0.8
    def trumpet(self, f, t):
        if f == 0: return 0
        return self.pulse(f, t, 0.2) * self.adsr(t, 0.05, 0.1, 0.9, 0.1) * 0.6
    def trombone(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.1, 0.2, 0.8, 0.2) * 0.7
    def tuba(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.15, 0.2, 0.9, 0.3) * 1.1
    def synth_strings(self, f, t):
        if f == 0: return 0
        return (self.saw(f*0.99, t) + self.saw(f*1.01, t) + self.saw(f, t)) * self.adsr(t, 0.4, 0.1, 0.9, 0.5) * 0.4
    def mellotron(self, f, t):
        if f == 0: return 0
        return self.efektler.lowpass_filter(self.triangle(f, t) + self.noise_white(t)*0.05, 2000) * self.adsr(t, 0.2, 0.1, 1.0, 0.3) * 0.8

    # --- GİTARLAR VE TELLER ---
    def acoustic_guitar(self, f, t):
        if f == 0: return 0
        return (self.triangle(f, t) + 0.1*self.noise_white(t[:len(t)//20])) * np.exp(-5 * t) * 0.9
    def nylon_guitar(self, f, t):
        if f == 0: return 0
        return self.sine(f, t) * np.exp(-4 * t) * 1.0
    def electric_clean(self, f, t):
        if f == 0: return 0
        return self.efektler.reverb_basit(self.triangle(f, t) * self.adsr(t, 0.01, 0.3, 0.4, 0.2) * 0.8)
    def electric_overdrive(self, f, t):
        if f == 0: return 0
        ses = self.saw(f, t) + 0.5*self.square(f, t)
        return self.efektler.distortion(ses * self.adsr(t, 0.05, 0.2, 0.8, 0.2), gain=4.0) * 0.4
    def electric_distortion(self, f, t):
        if f == 0: return 0
        ses = self.saw(f, t) + self.saw(f*2, t)*0.5
        return self.efektler.distortion(ses * self.adsr(t, 0.01, 0.1, 0.9, 0.1), gain=8.0) * 0.3
    def electric_fuzz(self, f, t):
        if f == 0: return 0
        return self.efektler.bitcrush(self.efektler.distortion(self.square(f, t) * self.adsr(t, 0.01, 0.1, 0.9, 0.1), 10.0), 4) * 0.3
    def electric_muted(self, f, t):
        if f == 0: return 0
        return self.efektler.lowpass_filter(self.saw(f, t), 1500) * np.exp(-15 * t) * 0.8
    def banjo(self, f, t):
        if f == 0: return 0
        return self.pulse(f, t, 0.1) * np.exp(-8 * t) * 0.7
    def ukulele(self, f, t):
        if f == 0: return 0
        return self.triangle(f, t) * np.exp(-6 * t) * 0.9
    def sitar(self, f, t):
        if f == 0: return 0
        ses = self.saw(f, t) + self.sine(f*0.5, t)*0.5
        return self.efektler.delay(ses * np.exp(-3 * t), gecikme_saniye=0.1, azalma=0.6, tekrar=5) * 0.5

    # --- ÜFLEMELİLER ---
    def flute_acoustic(self, f, t):
        if f == 0: return 0
        return (self.sine(f, t) + 0.1*self.noise_white(t)) * self.adsr(t, 0.2, 0.1, 0.9, 0.2) * 0.8
    def clarinet(self, f, t):
        if f == 0: return 0
        return self.pulse(f, t, 0.5) * self.adsr(t, 0.1, 0.1, 0.8, 0.2) * 0.7
    def oboe(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.1, 0.1, 0.9, 0.1) * 0.5
    def bassoon(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.2, 0.1, 0.9, 0.2) * 0.8
    def piccolo(self, f, t):
        if f == 0: return 0
        return self.sine(f, t) * self.adsr(t, 0.1, 0.1, 0.9, 0.1) * 0.9
    def recorder(self, f, t):
        if f == 0: return 0
        return self.triangle(f, t) * self.adsr(t, 0.15, 0.1, 0.9, 0.2) * 0.8
    def pan_flute(self, f, t):
        if f == 0: return 0
        return (self.sine(f, t) + 0.3*self.noise_white(t)) * self.adsr(t, 0.3, 0.1, 0.8, 0.3) * 0.9
    def sax_alto(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.1, 0.2, 0.8, 0.2) * 0.6
    def sax_tenor(self, f, t):
        if f == 0: return 0
        return (self.saw(f, t) + self.pulse(f, t, 0.3)) * self.adsr(t, 0.15, 0.2, 0.8, 0.2) * 0.5
    def sax_baritone(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.2, 0.2, 0.8, 0.2) * 0.7

    # --- SYNTH LEADLER VE PADLER (ELEKTRONİK) ---
    def saw_lead(self, f, t):
        if f == 0: return 0
        return self.saw(f, t) * self.adsr(t, 0.05, 0.1, 0.8, 0.2) * 0.5
    def square_lead(self, f, t):
        if f == 0: return 0
        return self.square(f, t) * self.adsr(t, 0.05, 0.1, 0.8, 0.2) * 0.4
    def sine_pluck(self, f, t):
        if f == 0: return 0
        return self.sine(f, t) * np.exp(-10 * t) * 1.2
    def trance_gate_pad(self, f, t):
        if f == 0: return 0
        gate = self.square(8, t) > 0 
        ses = (self.saw(f, t) + self.saw(f*1.01, t)) * self.adsr(t, 0.1, 0.1, 1.0, 0.1)
        return ses * gate * 0.4
    def warm_pad(self, f, t):
        if f == 0: return 0
        ses = self.sine(f, t) + 0.5*self.triangle(f*1.02, t) + 0.5*self.triangle(f*0.98, t)
        return self.efektler.reverb_basit(ses * self.adsr(t, 0.8, 0.5, 0.8, 0.8)) * 0.3
    def choir_pad_synth(self, f, t):
        if f == 0: return 0
        ses = self.triangle(f, t) + self.noise_white(t)*0.02
        return self.efektler.lowpass_filter(ses * self.adsr(t, 1.0, 0.2, 0.9, 1.0), 3000) * 0.5
    def sweep_pad(self, f, t):
        if f == 0: return 0
        lfo = self.sine(0.5, t)
        ses = self.saw(f + lfo*10, t) + self.saw(f*0.5, t)
        return self.efektler.lowpass_filter(ses * self.adsr(t, 2.0, 0.0, 1.0, 2.0), 2000) * 0.4
    def scifi_fx(self, f, t):
        if f == 0: return 0
        return self.sine(f + 1000*self.sine(10, t), t) * self.adsr(t, 0.1, 0.5, 0.2, 0.5) * 0.6
    def noise_sweep(self, t):
        return self.noise_white(t) * np.linspace(0, 1, len(t)) * 0.5
    def arp_8bit(self, f, t):
        if f == 0: return 0
        return self.square(f, t) * np.exp(-15 * t) * 0.5
    def chiptune_square(self, f, t):
        if f == 0: return 0
        return self.efektler.bitcrush(self.square(f, t) * self.adsr(t, 0.01, 0.1, 0.5, 0.1), 4) * 0.6
    def hoover_lead(self, f, t):
        if f == 0: return 0
        ses = self.saw(f, t) + self.saw(f*1.02, t) + self.saw(f*0.98, t) + self.saw(f*2, t)
        return self.efektler.distortion(ses * self.adsr(t, 0.1, 0.2, 0.8, 0.2), 2.0) * 0.2
    def supersaw(self, f, t):
        if f == 0: return 0
        ses = np.zeros_like(t)
        for detune in [-0.03, -0.015, 0, 0.015, 0.03]:
            ses += self.saw(f * (1 + detune), t)
        return ses * self.adsr(t, 0.1, 0.1, 0.8, 0.2) * 0.15

    # --- DOĞA VE AMBİYANS (AMBIENT FX) ---
    def wind_howl(self, t):
        noise = self.noise_white(t)
        lfo = 1000 + 800 * self.sine(0.2, t) + 400 * self.sine(0.5, t)
        ses = noise * (lfo / 2000.0) 
        return self.efektler.lowpass_filter(ses, 1500) * self.adsr(t, 2.0, 1.0, 0.8, 2.0) * 0.7
    def rain_drops(self, t):
        noise = self.noise_white(t)
        damlalar = noise * (self.noise_white(t) > 0.8)
        arkaplan = self.efektler.lowpass_filter(self.noise_white(t), 800) * 0.2
        return (damlalar * 0.5 + arkaplan) * self.adsr(t, 0.5, 0.5, 1.0, 1.0) * 0.6
    def ocean_waves(self, t):
        noise = self.noise_white(t)
        dalga_lfo = 0.5 + 0.5 * self.sine(0.15, t) 
        ses = self.efektler.lowpass_filter(noise, 600 + 400 * dalga_lfo)
        return ses * dalga_lfo * self.adsr(t, 2.0, 1.0, 0.9, 3.0) * 0.8
    def thunder_strike(self, t):
        noise = self.noise_white(t)
        patlama = self.efektler.lowpass_filter(noise, 400) * np.exp(-1 * t)
        distorted = self.efektler.distortion(patlama, gain=15.0)
        return self.efektler.reverb_basit(distorted * self.adsr(t, 0.01, 1.0, 0.5, 3.0)) * 2.0
    def fire_crackle(self, t):
        arkaplan = self.efektler.lowpass_filter(self.noise_white(t), 300) * 0.3
        citirti = self.noise_white(t) * (np.random.uniform(0, 1, len(t)) > 0.995) * np.exp(-50 * t)
        return (arkaplan + citirti * 1.5) * self.adsr(t, 0.1, 0.1, 1.0, 0.1) * 0.8

    # --- HAYVAN SESLERİ (SYNTH ANIMAL FX) ---
    def bird_chirp(self, t):
        f_base = 3000
        chirp_lfo = 1000 * self.saw(10, t) * np.exp(-5 * t)
        ses = self.sine(f_base + chirp_lfo, t)
        return ses * self.adsr(t, 0.01, 0.1, 0.0, 0.1) * 0.6
    def dog_bark(self, t):
        noise = self.noise_white(t)
        pitch_drop = np.linspace(600, 200, len(t))
        ton = self.saw(pitch_drop, t)
        ses = self.efektler.lowpass_filter((ton * 0.4 + noise * 0.6), 1200)
        return ses * self.adsr(t, 0.01, 0.15, 0.0, 0.05) * 1.5
    def cat_meow(self, t):
        f_curve = 600 + 300 * np.sin(np.pi * (t / (t[-1]+0.001))) 
        ses = self.triangle(f_curve, t) + 0.2 * self.saw(f_curve, t)
        return self.efektler.lowpass_filter(ses, 2000) * self.adsr(t, 0.1, 0.3, 0.6, 0.2) * 0.8
    def cricket_chirp(self, t):
        pulsing = self.square(20, t) > 0 
        ses = self.sine(4500, t) * pulsing
        return ses * self.adsr(t, 0.05, 0.2, 0.5, 0.1) * 0.4
    def frog_croak(self, t):
        pulsing = self.square(35, t) > 0.5
        ton = self.saw(np.linspace(120, 80, len(t)), t)
        ses = self.efektler.lowpass_filter(ton * pulsing, 800)
        return ses * self.adsr(t, 0.05, 0.15, 0.0, 0.1) * 1.5
    def wolf_howl(self, t):
        uzunluk = t[-1] + 0.001
        f_curve = 350 + 150 * np.sin(np.pi * (t / uzunluk)) + 10 * self.sine(4, t) 
        ses = self.triangle(f_curve, t)
        return self.efektler.reverb_basit(ses * self.adsr(t, 0.5, 1.0, 0.8, 1.0)) * 0.9
    def fly_buzz(self, t):
        lfo = 10 * self.sine(15, t) 
        ses = self.pulse(250 + lfo, t, width=0.1)
        return self.efektler.lowpass_filter(ses, 3000) * self.adsr(t, 0.2, 0.5, 0.8, 0.5) * 0.5

    # --- OYUN EFEKTLERİ (GAME FX) ---
    def fx_laser_pew(self, t):
        f_drop = np.linspace(2000, 100, len(t))
        return self.square(f_drop, t) * np.exp(-15 * t) * 0.8
    def fx_coin_pickup(self, t):
        ses = np.zeros_like(t)
        yari = len(t) // 6
        if yari > 0:
            ses[:yari] = self.square(987, t[:yari])
            ses[yari:yari*3] = self.square(1318, t[yari:yari*3])
        return ses * np.exp(-10 * t) * 0.6
    def fx_jump(self, t):
        f_rise = np.linspace(300, 800, len(t))
        return self.pulse(f_rise, t, 0.5) * np.exp(-10 * t) * 0.7
    def fx_explosion(self, t):
        noise = self.efektler.bitcrush(self.noise_white(t), bit_derinligi=3, downsample=8)
        return self.efektler.lowpass_filter(noise, 1000) * np.exp(-4 * t) * 1.5
    def fx_helicopter(self, t):
        pervane = self.square(12, t) > 0 
        noise = self.efektler.lowpass_filter(self.noise_white(t), 400)
        return noise * pervane * self.adsr(t, 0.5, 1.0, 0.8, 1.0) * 1.5

    # =====================================================================
    # ANA MOTOR: RENDER (DEVASA UZUN ŞARKI VE KANALLAR)
    # =====================================================================
    def render_sarki(self, sarki_verisi):
        tekrar_sayisi = 128 # 128 Loop x 16 = Dev gibi parça
        tempo = sarki_verisi.get("tempo", 120)
        adim_suresi = (60.0 / tempo) / 4.0
        samples_per_step = int(self.sr * adim_suresi)
        
        toplam_samples = tekrar_sayisi * 16 * samples_per_step
        master_ses = np.zeros(toplam_samples, dtype=np.float32)
        
        def guvenli_liste(isim):
            liste = sarki_verisi.get(isim, ["-"]*16)
            if len(liste) < 16: liste += ["-"] * (16 - len(liste))
            return liste

        # Kütüphanedeki Yüzlerce Enstrümanın Eşleşmesi (True = Saniye Bazlı/Davul-FX, False = Nota Bazlı)
        enstrumanlar = {
            "kick_808": (self.kick_808, True), "kick_909": (self.kick_909, True), "kick_acoustic": (self.kick_acoustic, True),
            "kick_punchy": (self.kick_punchy, True), "kick_lofi": (self.kick_lofi, True), "kick_techno": (self.kick_techno, True), "kick_deep": (self.kick_deep, True),
            "snare_acoustic": (self.snare_acoustic, True), "snare_electronic": (self.snare_electronic, True), "snare_808": (self.snare_808, True), "snare_trap": (self.snare_trap, True),
            "clap_basic": (self.clap_basic, True), "clap_layered": (self.clap_layered, True), "rimshot": (self.rimshot, True),
            "hihat_closed": (self.hihat_closed, True), "hihat_open": (self.hihat_open, True), "hihat_808": (self.hihat_808, True), "hihat_trap": (self.hihat_trap, True),
            "crash_cymbal": (self.crash_cymbal, True), "ride_cymbal": (self.ride_cymbal, True), "splash_cymbal": (self.splash_cymbal, True),
            "tom_high": (self.tom_high, True), "tom_mid": (self.tom_mid, True), "tom_low": (self.tom_low, True),
            "bongo_high": (self.bongo_high, True), "bongo_low": (self.bongo_low, True), "cowbell": (self.cowbell, True),
            "woodblock": (self.woodblock, True), "shaker": (self.shaker, True), "tambourine": (self.tambourine, True),
            "triangle_perc": (self.triangle_perc, True), "claves": (self.claves, True), "guiro": (self.guiro, True), "maracas": (self.maracas, True),
            
            "wind_howl": (self.wind_howl, True), "rain_drops": (self.rain_drops, True), "ocean_waves": (self.ocean_waves, True), 
            "thunder_strike": (self.thunder_strike, True), "fire_crackle": (self.fire_crackle, True),
            "bird_chirp": (self.bird_chirp, True), "dog_bark": (self.dog_bark, True), "cat_meow": (self.cat_meow, True), 
            "cricket_chirp": (self.cricket_chirp, True), "frog_croak": (self.frog_croak, True), "wolf_howl": (self.wolf_howl, True), "fly_buzz": (self.fly_buzz, True),
            "fx_laser_pew": (self.fx_laser_pew, True), "fx_coin_pickup": (self.fx_coin_pickup, True), "fx_jump": (self.fx_jump, True), 
            "fx_explosion": (self.fx_explosion, True), "fx_helicopter": (self.fx_helicopter, True),

            "sub_bass": (self.sub_bass, False), "slap_bass": (self.slap_bass, False), "synth_bass": (self.synth_bass, False), "reese_bass": (self.reese_bass, False),
            "acid_bass": (self.acid_bass, False), "fm_bass": (self.fm_bass, False), "upright_bass": (self.upright_bass, False), "fretless_bass": (self.fretless_bass, False),
            "moog_bass": (self.moog_bass, False), "wobble_bass": (self.wobble_bass, False),
            
            "grand_piano": (self.grand_piano, False), "upright_piano": (self.upright_piano, False), "rhodes_piano": (self.rhodes_piano, False), "wurlitzer": (self.wurlitzer, False),
            "dx7_piano": (self.dx7_piano, False), "clavinet": (self.clavinet, False), "harpsichord": (self.harpsichord, False), "celesta": (self.celesta, False),
            "church_organ": (self.church_organ, False), "hammond_organ": (self.hammond_organ, False), "reed_organ": (self.reed_organ, False),
            
            "violin": (self.violin, False), "cello": (self.cello, False), "contrabass": (self.contrabass, False), "pizzicato": (self.pizzicato, False),
            "harp": (self.harp, False), "timpani": (self.timpani, False), "brass_section": (self.brass_section, False), "french_horn": (self.french_horn, False),
            "trumpet": (self.trumpet, False), "trombone": (self.trombone, False), "tuba": (self.tuba, False), "synth_strings": (self.synth_strings, False), "mellotron": (self.mellotron, False),
            
            "acoustic_guitar": (self.acoustic_guitar, False), "nylon_guitar": (self.nylon_guitar, False), "electric_clean": (self.electric_clean, False),
            "electric_overdrive": (self.electric_overdrive, False), "electric_distortion": (self.electric_distortion, False), "electric_fuzz": (self.electric_fuzz, False),
            "electric_muted": (self.electric_muted, False), "banjo": (self.banjo, False), "ukulele": (self.ukulele, False), "sitar": (self.sitar, False),
            
            "flute_acoustic": (self.flute_acoustic, False), "clarinet": (self.clarinet, False), "oboe": (self.oboe, False), "bassoon": (self.bassoon, False),
            "piccolo": (self.piccolo, False), "recorder": (self.recorder, False), "pan_flute": (self.pan_flute, False),
            "sax_alto": (self.sax_alto, False), "sax_tenor": (self.sax_tenor, False), "sax_baritone": (self.sax_baritone, False),
            
            "saw_lead": (self.saw_lead, False), "square_lead": (self.square_lead, False), "sine_pluck": (self.sine_pluck, False), "trance_gate_pad": (self.trance_gate_pad, False),
            "warm_pad": (self.warm_pad, False), "choir_pad_synth": (self.choir_pad_synth, False), "sweep_pad": (self.sweep_pad, False), "scifi_fx": (self.scifi_fx, False),
            "arp_8bit": (self.arp_8bit, False), "chiptune_square": (self.chiptune_square, False), "hoover_lead": (self.hoover_lead, False), "supersaw": (self.supersaw, False)
        }

        aktif_kanallar = {}
        for anahtar, deger in sarki_verisi.items():
            if anahtar in enstrumanlar:
                aktif_kanallar[anahtar] = (guvenli_liste(anahtar), enstrumanlar[anahtar][0], enstrumanlar[anahtar][1])

        t_dizi = np.linspace(0, adim_suresi, samples_per_step, endpoint=False)

        for loop_idx in range(tekrar_sayisi):
            cal_intro = loop_idx < 16
            cal_build = loop_idx >= 16 and loop_idx < 32
            cal_drop = loop_idx >= 32 and loop_idx < 64
            cal_bridge = loop_idx >= 64 and loop_idx < 80
            cal_drop2 = loop_idx >= 80 and loop_idx < 112
            cal_outro = loop_idx >= 112
            
            davul_aktif = cal_build or cal_drop or cal_drop2
            bas_aktif = cal_drop or cal_drop2 or (cal_bridge and loop_idx % 2 == 0)
            lead_aktif = cal_drop or cal_drop2 or cal_intro
            pad_aktif = True 
            
            for i in range(16):
                zaman_basla = (loop_idx * 16 + i) * samples_per_step
                zaman_bitis = zaman_basla + samples_per_step
                katman = np.zeros(samples_per_step)
                
                for kanal_adi, (nota_listesi, func, is_drum_fx) in aktif_kanallar.items():
                    nota_istegi = nota_listesi[i]
                    if nota_istegi == "-": continue
                    
                    if is_drum_fx:
                        if not davul_aktif and "kick" in kanal_adi: continue
                        katman += func(t_dizi)
                    elif not is_drum_fx:
                        if "bass" in kanal_adi and not bas_aktif: continue
                        if ("lead" in kanal_adi or "guitar" in kanal_adi or "piano" in kanal_adi) and not lead_aktif: continue
                        if "pad" in kanal_adi and not pad_aktif: continue
                        
                        frekans = self.notalar.get(nota_istegi, 0.0)
                        katman += func(frekans, t_dizi)
                
                master_ses[zaman_basla:zaman_bitis] += katman

        build_bitis_sample = 32 * 16 * samples_per_step
        build_basla_sample = 28 * 16 * samples_per_step 
        if build_bitis_sample < len(master_ses):
            sweep_uzunluk = build_bitis_sample - build_basla_sample
            t_sweep = np.linspace(0, sweep_uzunluk / self.sr, sweep_uzunluk)
            master_ses[build_basla_sample:build_bitis_sample] += self.noise_sweep(t_sweep)

        fade_out_samples = int(self.sr * 10) 
        master_ses[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        max_val = np.max(np.abs(master_ses))
        if max_val > 0:
            master_ses = np.int16(master_ses / max_val * 32767 * 0.95) 
        else:
            master_ses = np.int16(master_ses)
            
        byte_io = io.BytesIO()
        wav.write(byte_io, self.sr, master_ses)
        return byte_io.getvalue()

def motoru_calistir(sarki_verisi):
    motor = NoModelsMusicEngine()
    return motor.render_sarki(sarki_verisi)
