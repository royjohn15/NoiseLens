"""End-to-end check: fake microphone (a WAV file) + simulated motion + GPS, phone viewport.
Run:  python3 tests/test_e2e.py path/to/scenario.wav out_dir
Serves the app on http://localhost:8765 (localhost counts as a secure context).
"""
import http.server, pathlib, sys, threading, functools, json, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
wav, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
threading.Thread(target=srv.serve_forever, daemon=True).start()

MOTION = r"""
(mode) => {
  clearInterval(window.__mot); let i = 0;
  window.__mot = setInterval(() => {
    i++; let x = 0, y = 0, z = 9.81;
    if (mode === 'flat') { x = 0.015*Math.sin(i*2.1); z = 9.81 + 0.02*Math.sin(i*1.3); }
    if (mode === 'tap')  { x = 0.015*Math.sin(i); z = 9.81 + (i % 120 < 3 ? 6 : 0.02*Math.sin(i)); }
    if (mode === 'pocket') { const s = Math.sin(2*Math.PI*1.9*i/60); x = 0.3*s; y = 9.6 + 2.2*s; z = 1.0; }
    window.dispatchEvent(new DeviceMotionEvent('devicemotion', {accelerationIncludingGravity: {x, y, z}, interval: 16}));
  }, 1000/60);
}
"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                f"--use-file-for-fake-audio-capture={wav}", "--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        permissions=["microphone", "geolocation"], geolocation={"latitude": 12.9916, "longitude": 80.2337})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.goto("http://localhost:8765/index.html")
    pg.screenshot(path=str(out / "0_start.png"))
    pg.wait_for_function("document.getElementById('chipAI').textContent.includes('ready') || document.getElementById('chipAI').textContent.includes('unavailable')", timeout=60000)
    pg.click("#startBtn")
    pg.evaluate(MOTION, "flat")
    # walk a little so the map gets a path
    for k in range(30):
        ctx.set_geolocation({"latitude": 12.9916 + k*0.00004, "longitude": 80.2337 + k*0.00003})
        if k == 12: pg.evaluate(MOTION, "tap")
        if k == 18: pg.evaluate(MOTION, "flat")
        time.sleep(1)
    pg.screenshot(path=str(out / "1_live.png"), full_page=True)
    pg.click("nav button[data-tab=insights]"); time.sleep(1.2); pg.screenshot(path=str(out / "2_insights.png"), full_page=True)
    pg.click("nav button[data-tab=sensors]"); time.sleep(1.2); pg.screenshot(path=str(out / "3_sensors.png"), full_page=True)
    pg.evaluate(MOTION, "pocket"); time.sleep(5); pg.screenshot(path=str(out / "3b_sensors_pocket.png"), full_page=False)
    pg.click("nav button[data-tab=map]"); time.sleep(4); pg.screenshot(path=str(out / "4_map.png"), full_page=True)
    recs = pg.evaluate("S.rec.map(r=>({L:+r.L.toFixed(1),src:GROUPS[r.g].short,label:r.label,score:+r.score.toFixed(2),trust:r.trust,place:r.place,ex:r.excluded,vib:r.vib}))")
    info = pg.evaluate("({ai:S.aiState, sr:S.sr, dose:S.today.dose, mapPts:S.mapPts.length})")
    b.close()
srv.shutdown()
print(json.dumps(info))
for i, r in enumerate(recs): print(i, r)
print("ERRORS:", errors or "none")
