# NoiseLens: a multi-sensor noise exposure meter

A phone web app that shows **how loud it is**, **what is making the noise** (on-device AI), and **how much of
today's safe hearing allowance each source has used up**. The motion sensors and GPS check how far each
reading can be trusted and show where the exposure happened.

**The decision it supports:** *Is this place harming my hearing, which source is responsible, and how long can I
safely stay?*

## Sensors used

| Sensor | What it is used for |
|---|---|
| Microphone | A-weighted sound level (FFT, IEC 61672 A-curve), live spectrogram, input to the AI |
| On-device AI (YAMNet via MediaPipe) | Identifies 521 sound classes, grouped into 7 source groups, once per second |
| Accelerometer / gyroscope | Measurement trust (flat / in hand / walking / in pocket), tap rejection, vibration RMS |
| GPS | Exposure map: path coloured by level |
| Vibration motor | Haptic alert at 85 dB(A) (1-minute Leq) and at 50% / 100% of the daily dose |

## Screens

- **Live:** source-coloured dose ring with the live level arc, "safe time left" forecast, trust KPI, scrolling
  spectrogram with an AI source strip, and a 3-minute level timeline with an uncertainty band and excluded taps.
- **Insights:** share of time vs share of dose for each source, level histogram with L90/L50/L10/Leq, session
  summary, CSV export.
- **Sensors:** trust gauge with the reasons behind it, 30-second motion trace, vibration co-exposure
  (ISO 2631-1 comfort bands), calibration.
- **Map:** exposure trail on OpenStreetMap.

## Run it on your phone

Phone browsers only allow the microphone and motion sensors on **https** pages.

**GitHub Pages (free):**
1. Create a public repository and upload `index.html` (and this README).
2. Go to Settings → Pages → Branch: `main` / root → Save.
3. Open `https://<your-username>.github.io/<repo>/` on the phone and tap **Start measuring**. Allow the
   microphone, motion and location permissions when asked.

Alternative: drag the folder onto <https://app.netlify.com/drop>.

An internet connection is needed the first time, to load the AI model (~4 MB), Leaflet and the map tiles. The
level meter itself runs fully on the phone, and no audio is recorded or uploaded.

## Suggested 1-minute video

1. (0–10 s) Open the app and tap Start. Phone flat on a table: "Resting flat, trust 100%".
2. (10–25 s) Talk, then play music. The source chip and spectrogram strip switch between Speech and Music, and
   the ring fills with those colours.
3. (25–40 s) Run a mixer, hair dryer or pressure cooker close by. The level crosses 85, the status turns red, and
   "safe time left" collapses. Open **Insights**: the noisy source has a small share of the time but a large
   share of the dose.
4. (40–50 s) Tap the phone. The **Sensors** tab shows the spike flagged and the second excluded. Pick up the phone
   and put it in a pocket: trust drops.
5. (50–60 s) The **Map** shows where it was loud. Close with why it's useful: it identifies the source using up
   your hearing allowance, so you can act on it.

## How the numbers were checked

`python3 tests/test_dsp.py` runs 32 unit tests in headless Chromium against the app's own functions, and all pass:
- Parseval: a 1 kHz sine of amplitude 0.5 gives mean-square 0.1250 (expected 0.125).
- A-weighting matches IEC 61672 reference values: 63 Hz −26.2, 100 Hz −19.1, 1 kHz 0.0, 4 kHz +1.0,
  10 kHz −2.5 dB (all within 0.15 dB). A 250 Hz tone reads −8.67 dB relative to Z (expected −8.6).
- NIOSH dose: 8 h at 85 dB = 100.0%, 100 dB allows 900 s (15 min), 88 dB allows 4 h.
- Leq of 80 and 90 dB = 87.40 dB. Step-rhythm autocorrelation: 2 Hz walking 0.875, noise < 0.3.
- Placement rules, and the YAMNet index → source group mapping checked against the official class map.

`python3 tests/test_e2e.py <scenario.wav> <out_dir>` feeds a WAV file into Chromium's fake microphone, with
simulated motion and GPS, at a 390×844 phone viewport. Results: speech was identified as Speech at 94–100%
confidence and a cat recording as Cat at 85–94%. The flat → tap → pocket motion sequence was classified correctly
(taps excluded, pocket at 35% trust), the map trail was drawn, and there were no console errors.

**Not yet checked:** absolute dB accuracy on a real phone. Calibrate against a reference meter (Sensors →
Calibration). Until then the app shows ±6 dB.

## Limits (stated in the app)

- Phone microphones are not Class 1/2 meters. Uncalibrated built-in mics are within about 2 dB on iPhones but up
  to about 6 dB off on some Android phones (Kardous & Shaw, NIOSH 2014; Jacobs et al. 2020).
- YAMNet is a general-purpose classifier and can confuse similar sounds (e.g. brown noise → "Ocean"). The
  confidence is shown next to every label.
- Pocket detection is a rule-based heuristic (after Ear-Phone, Rana et al.), not a trained classifier.
- Vibration comfort bands are indicative: unweighted RMS, not ISO 2631 frequency-weighted.
- Whether noise and vibration together raise hearing-loss risk is not settled; the app says so.

## References

- NIOSH, *Criteria for a Recommended Standard: Occupational Noise Exposure* (REL 85 dBA, 3 dB exchange rate).
- WHO, *Environmental Noise Guidelines for the European Region* (2018).
- Kardous C.A., Shaw P.B., "Evaluation of smartphone sound measurement applications", JASA 2014 / NIOSH blog.
- Rana R. et al., "Ear-Phone: a context-aware noise mapping using smart phones", Pervasive and Mobile Computing 2015.
- Gemmeke J.F. et al., AudioSet (2017); YAMNet model, TensorFlow / MediaPipe Audio Classifier.
- ISO 2631-1:1997, mechanical vibration: whole-body vibration comfort reactions (Annex C).
