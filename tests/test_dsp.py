"""Unit tests for NoiseLens maths, executed inside headless Chromium.
Run:  python3 tests/test_dsp.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

APP = pathlib.Path(__file__).resolve().parent.parent / "index.html"

JS = r"""
() => {
  const out = [];
  const ok = (name, got, want, tol) => out.push({name, got, want, pass: Math.abs(got - want) <= tol});
  const sr = 48000, N = 2048;
  const sine = (f, A) => Float32Array.from({length: N}, (_, i) => A * Math.sin(2 * Math.PI * f * i / sr));
  // 1) Parseval: a sine of amplitude A has mean-square A^2/2
  let m = blockMeanSquare(sine(1000, 0.5), sr);
  ok("Z mean-square of 1 kHz sine (A=0.5)", m.z, 0.125, 0.125 * 0.03);
  ok("A-weighting at 1 kHz = 0 dB", toDb(m.a) - toDb(m.z), 0, 0.15);
  // 2) A-weighting reference values (IEC 61672): 100 Hz -19.1, 63 Hz -26.2, 4 kHz +1.0, 10 kHz -2.5
  for (const [f, want] of [[100, -19.1], [63, -26.2], [4000, 1.0], [10000, -2.5]])
    ok(`A-curve formula at ${f} Hz`, 10 * Math.log10(aWeightPow(f)), want, 0.15);
  m = blockMeanSquare(sine(250, 0.3), sr);
  ok("A-weighted level of 250 Hz sine vs Z (-8.6 dB)", toDb(m.a) - toDb(m.z), -8.6, 0.3);
  // 3) NIOSH dose: 85 dB for 8 h = 100 %, 100 dB allowed 15 min, 88 dB 4 h
  ok("Allowed time at 85 dB (s)", allowedSeconds(85), 28800, 1e-6);
  ok("Allowed time at 100 dB (s)", allowedSeconds(100), 900, 1e-6);
  ok("Allowed time at 88 dB (s)", allowedSeconds(88), 14400, 1e-6);
  let d = 0; for (let i = 0; i < 28800; i++) d += dosePerSecond(85);
  ok("8 h at 85 dB -> dose %", d, 100, 1e-6);
  // 4) Leq energy average: 80 dB and 90 dB for equal time -> 87.4 dB
  ok("Leq of [80, 90]", leqOf([80, 90]), 87.40, 0.01);
  ok("Percentile p50 of 1..9", percentile([1,2,3,4,5,6,7,8,9], 0.5), 5, 1e-9);
  // 5) Step periodicity: 2 Hz signal at 60 Hz sampling -> strong autocorrelation
  const walk = Array.from({length: 240}, (_, i) => 9.8 + 2 * Math.sin(2 * Math.PI * 2 * i / 60));
  ok("ACF peak of 2 Hz walking signal", acfPeak(walk, 21, 54), 0.85, 0.15);
  const noise = Array.from({length: 240}, () => Math.random());
  out.push({name: "ACF peak of random noise < 0.3", got: acfPeak(noise, 21, 54), want: "<0.3", pass: acfPeak(noise, 21, 54) < 0.3});
  // 6) Placement rules
  const P = f => classifyPlacement(f).key;
  for (const [f, want] of [[{dynRms:.02,tilt:5,acf:0}, "flat"], [{dynRms:1.5,tilt:80,acf:.7}, "pocket"],
                           [{dynRms:1.2,tilt:40,acf:.7}, "walk"], [{dynRms:.2,tilt:45,acf:.1}, "hand"], [null, "unknown"]])
    out.push({name: `placement ${JSON.stringify(f)}`, got: P(f), want, pass: P(f) === want});
  // 7) YAMNet index -> group, checked against class names
  for (const [i, name, g] of [[0,"Speech",0],[69,"Dog",5],[132,"Music",2],[301,"Car",1],[321,"Traffic noise",1],
                              [341,"Chainsaw",3],[363,"Blender",4],[371,"Vacuum cleaner",4],[390,"Siren",6],[406,"Mechanical fan",3],[494,"Silence",7]])
    out.push({name: `group of #${i} ${name}`, got: groupOfIndex(i), want: g, pass: groupOfIndex(i) === g});
  out.push({name: "pickSource skips generic top label", got: pickSource([{index:500,displayName:"Inside, small room",score:.6},{index:0,displayName:"Speech",score:.3}]).g, want: 0,
            pass: pickSource([{index:500,displayName:"Inside, small room",score:.6},{index:0,displayName:"Speech",score:.3}]).g === 0});
  return out;
}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(APP.as_uri())
    res = pg.evaluate(JS)
    b.close()

fails = 0
for r in res:
    got = r["got"]
    got = f"{got:.4f}" if isinstance(got, float) else got
    print(("PASS " if r["pass"] else "FAIL ") + f'{r["name"]}: got {got}, want {r["want"]}')
    fails += not r["pass"]
print(f"\n{len(res) - fails}/{len(res)} passed")
sys.exit(1 if fails else 0)
