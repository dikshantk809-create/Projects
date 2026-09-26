"""Build a single-file preview of the console that runs with no rover.

    python3 scripts/build_preview.py  [out.html]

It inlines the stylesheet and both scripts into one HTML file, then adds a small
shim that answers the console's own calls with made-up data. The console code
itself is not changed, so the preview always looks exactly like the real thing.

Useful for showing someone the rover's website without the rover, and for
checking a design change without booting the Pi.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATIC = os.path.join(ROOT, "ar750", "web", "static")

SHIM = r"""
<script>
/* ------------------------------------------------------------------------
   Preview shim. There is no rover behind this page, so every call the
   console makes is answered here with invented data. The console's own code
   is untouched: what you see is what the real one does.
   --------------------------------------------------------------------- */
(function () {
  var t0 = Date.now() / 1000;
  var LABELS = [
    ['healthy', 'Healthy plant', 1, '', 'Nothing to do. Keep watering evenly.'],
    ['tomato_early_blight', 'Tomato early blight', 0, 'Mancozeb 75% WP  2 g per litre',
     'Pick off the spotted lower leaves and bin them. Do not wet the leaves when you water.'],
    ['aphid', 'Aphids', 0, 'Neem oil 1500 ppm  3 ml per litre',
     'Squash the cluster or wash it off with plain water first. Ladybirds finish the job.'],
    ['powdery_mildew', 'Powdery mildew', 0, 'Wettable sulphur 80% WP  2 g per litre',
     'Cut out the worst leaves and give the plants more room to breathe.'],
    ['water_stress', 'Short of water', 0, 'no chemical needed',
     'Water it. Check the soil reading the rover took before you do more.'],
    ['weed', 'Weed', 0, '', 'Pull it out by hand. The AR-750 has a boom, not a gripper.']
  ];
  var plants = [], samples = [], missions = [], alerts = [];
  var mode = 'AUTO';
  var ARM = [
    ['pan', 'Camera left / right', 'camera', 20, 160, 90],
    ['base', 'Base (turn)', 'arm', 10, 170, 90],
    ['shoulder', 'Shoulder', 'arm', 20, 160, 140],
    ['elbow', 'Elbow', 'arm', 20, 160, 40],
    ['wrist', 'Wrist up / down', 'arm', 10, 170, 90],
    ['grip', 'Gripper', 'arm', 30, 110, 60]
  ].map(function (a) {
    return { name: a[0], label: a[1], group: a[2], min: a[3], max: a[4], park: a[5],
      deg: a[5], target: a[5], awake: false, moving: false,
      open: a[0] === 'grip' ? 110 : null, closed: a[0] === 'grip' ? 30 : null };
  });
  var POSES = { park: { base: 90, shoulder: 140, elbow: 40, wrist: 90, grip: 60 },
    ready: { base: 90, shoulder: 100, elbow: 80, wrist: 90 },
    reach: { base: 90, shoulder: 60, elbow: 110, wrist: 60 } };
  var SAVED = {}, lastWalk = Date.now();
  function jt(n) { return ARM.filter(function (j) { return j.name === n; })[0]; }
  function walk() {
    var dt = (Date.now() - lastWalk) / 1000; lastWalk = Date.now();
    ARM.forEach(function (j) {
      var step = (j.group === 'camera' ? 90 : 40) * dt, d = j.target - j.deg;
      j.deg = Math.abs(d) <= step ? j.target : j.deg + (d > 0 ? step : -step);
      j.moving = Math.abs(j.target - j.deg) > 0.4;
    });
  }
  function servoCmd(b) {
    var a = b.args || {};
    if (b.cmd === 'mode') { mode = a.mode || 'IDLE'; return { ok: true }; }
    if (/^servo/.test(b.cmd) && b.cmd !== 'servo_relax' && b.cmd !== 'servo_pose_delete' &&
        b.cmd !== 'servo_pose_save' && mode === 'AUTO')
      return { ok: false, error: 'The arm stays still while it drives itself' };
    if (b.cmd === 'servo') {
      var j = jt(a.name);
      if (!j) return { ok: false, error: 'there is no joint called ' + a.name };
      if (!j.awake) { j.awake = true; j.deg = j.park; }
      var to = a.delta != null ? j.target + a.delta : a.deg;
      j.target = Math.max(j.min, Math.min(j.max, to));
      return { ok: true };
    }
    if (b.cmd === 'servo_pose') {
      var p = POSES[a.pose];
      if (!p) return { ok: false, error: 'no pose called ' + a.pose };
      Object.keys(p).forEach(function (n) { servoCmd({ cmd: 'servo', args: { name: n, deg: p[n] } }); });
      return { ok: true };
    }
    if (b.cmd === 'servo_relax') { ARM.forEach(function (j) { j.awake = false; j.target = j.deg; }); return { ok: true }; }
    if (b.cmd === 'servo_pose_save') {
      var nm = String(a.name || '').trim().slice(0, 24);
      if (!nm) return { ok: false, error: 'Give the pose a name' };
      if (POSES[nm] && !SAVED[nm]) return { ok: false, error: nm + ' is one of the built-in poses - pick another name' };
      var q = {};
      ARM.forEach(function (j) { if (j.group !== 'camera' && j.awake) q[j.name] = Math.round(j.target); });
      if (!Object.keys(q).length) return { ok: false, error: 'Move the arm first - nothing is holding a position yet' };
      POSES[nm] = SAVED[nm] = q;
      return { ok: true, message: 'Saved ' + nm + ' (preview only, forgotten on reload)' };
    }
    if (b.cmd === 'servo_pose_delete') {
      if (!SAVED[a.name]) return { ok: false, error: 'The built-in poses live in config.yaml' };
      delete SAVED[a.name]; delete POSES[a.name];
      return { ok: true, message: 'Deleted ' + a.name };
    }
    return null;
  }
  var seq = 0, dist = 1.9, x = 1.9, y = 0.1, hdg = 4, batt = 16.10, soil = 44, tank = 88;

  function addPlant(back, forceIdx) {
    var L = LABELS[forceIdx === undefined ? (Math.random() * LABELS.length) | 0 : forceIdx];
    seq++;
    var healthy = !!L[2];
    var conf = healthy ? 0.93 : 0.62 + Math.random() * 0.34;
    var sprayed = !healthy && L[3] && conf > 0.85;
    return {
      id: seq, db_id: seq, plot: 'r1p' + ('0' + seq).slice(-2),
      ts: t0 - back, time: t0 - back,
      x: 0.35 * seq, y: 0.04 * seq - 0.1, x_m: 0.35 * seq, y_m: 0.04 * seq - 0.1,
      label: L[0], common_name: L[1], confidence: +conf.toFixed(2),
      healthy: healthy,
      severity: healthy ? 'none' : conf > 0.9 ? 'severe' : conf > 0.78 ? 'moderate' : 'mild',
      treatment: L[3], advice: L[4],
      action: healthy ? 'none' : sprayed ? 'sprayed' : 'needs_you',
      dose_ml: sprayed ? 12 : 0, sprayed: !!sprayed, soil_pct: 40 + (seq % 9),
      photo: ''
    };
  }
  for (var i = 9; i >= 1; i--) plants.push(addPlant(i * 240, i % 6));
  for (var s = 360; s >= 0; s--) {
    samples.push({ ts: t0 - s * 10, battery_v: +(16.4 - s * 0.0009).toFixed(2),
      battery_pct: Math.round(88 - s * 0.02), soil_pct: Math.round(44 + 7 * Math.sin(s / 30)),
      tank_pct: Math.min(100, 88 + s * 0.03), speed_mps: 0.05,
      distance_m: dist, cpu_temp_c: 50 + (s % 4), current_a: 1.4 });
  }
  for (var m = 0; m < 6; m++) {
    missions.push({ id: 6 - m, started: t0 - m * 86400 - 3000, ended: t0 - m * 86400 - 1900,
      kind: m % 3 === 0 ? 'patrol' : 'manual', plants_checked: 8 + (m % 5),
      problems: (m % 4), sprayed_ml: (m % 4) * 12, distance_m: 7.4 + m,
      note: 'row finished' });
  }
  var patrols = [{ id: 1, name: 'Morning check', days: '0,1,2,3,4', at: '07:00',
    plants: 12, spray: false, enabled: true, last_run: t0 - 70000 }];
  var pending = {
    title: 'Aphids on plant r1p08',
    question: 'Spray 8 ml of Neem oil 1500 ppm (3 ml per litre) on this plant? ' +
              'Do not pick the crop for 3 days after.',
    plan: {}, record: 8, photo: '', time: t0
  };

  function state() {
    var now = Date.now() / 1000;
    x += 0.004; dist += 0.004; batt -= 0.00002; soil += (Math.random() - 0.5) * 0.2;
    return {
      t: now, mode: mode, estop: false, estop_reason: '', sim: false, auto_blind_cap: 0.3,
      spray_armed: true, auto_spray: false, pump_on: false, lamps_on: false,
      rc_live: false, rc: [0, 0, 0, 0, 0, 0],
      drive: { throttle: 0.42, steer_deg: -8.4, steer_stick: -0.34 },
      ai_ready: true, ai_reason: '', recording: true, rec_frames: 128,
      returning: false, speed_limit: 0.6, auto_weed_pull: false,
      fitted: { encoders: true, imu: true, range: true, camera: true },
      next_patrol: { name: 'Morning check', at: nextSeven() },
      telemetry: { battery_v: +batt.toFixed(2), battery_pct: 78, current_a: 1.4,
        soil_pct: Math.round(soil), tank_pct: 88, tank_ml: 1540,
        heading_deg: hdg, tilt_deg: 2.1, speed_mps: 0.05,
        distance_m: +dist.toFixed(2), x_m: +x.toFixed(2), y_m: y,
        range_front_cm: 92, cpu_temp_c: 52, uptime_s: 4210,
        odometry_measured: true, turn_radius_mm: 3650 },
      steering: { max_wheel_deg: 24.7, min_turn_radius_mm: 1174,
        turning_circle_mm: 2779, wheelbase_mm: 540, track_mm: 430,
        can_spin_on_the_spot: false },
      drive_hw: { throttle: 0.42, steer_deg: -8.4, front_us: 1710,
        rear_us: 1710, steer_us: 1420, armed: true },
      boom: { pump_on: true, sections: ['centre'], used_ml: 212, nozzles: 5,
        remaining_ml: 4788, duty: 0.17, pwm_hz: 10, target_l_per_ha: 200,
        fitted: true },
      probe_hw: { state: 'up', moving: 'stopped', busy: false, fitted: true,
        travel_mm: 190 },
      mission: { running: true, step: 'inspect', plants_done: 9, plants_target: 0,
        row: 1, sprayed_ml: 24, mission_id: 7, message: 'Looking at the plant' },
      pending: pending,
      servos: (walk(), { live: true, reason: '', driver: 'gpio',
        joints: ARM.map(function (j) { return Object.assign({}, j); }),
        poses: Object.keys(POSES), saved_poses: Object.keys(SAVED).sort() }),
      plants: plants.map(function (p) { return p; }),
      alerts: alerts,
      log: [
        { time: now - 8, level: 'warn', text: 'Waiting for you: Aphids' },
        { time: now - 46, level: 'info', text: 'Sprayed the centre section over plant r1p06 at 200 l/ha' },
        { time: now - 180, level: 'info', text: 'Recording the run' },
        { time: now - 181, level: 'info', text: 'AUTO started. Target as many as it finds' },
        { time: now - 899, level: 'info', text: 'Steering: 24.7 deg at the wheels, 2.78 m turning circle. It cannot turn on the spot.' },
        { time: now - 900, level: 'info', text: 'AR-750 ready' }
      ]
    };
  }
  function nextSeven() {
    var d = new Date(); d.setDate(d.getDate() + 1); d.setHours(7, 0, 0, 0);
    return d.getTime() / 1000;
  }

  function days() {
    var out = [];
    for (var i = 13; i >= 0; i--) {
      var d = new Date(Date.now() - i * 86400000);
      out.push({ day: d.toISOString().slice(0, 10),
        checked: 4 + ((i * 7) % 11), problems: (i * 3) % 5,
        sprayed: (i * 2) % 3, ml: ((i * 5) % 4) * 12 });
    }
    return out;
  }
  function tally() {
    var by = {};
    plants.forEach(function (p) {
      if (p.healthy) return;
      by[p.label] = by[p.label] || { label: p.label, common_name: p.common_name, n: 0 };
      by[p.label].n++;
    });
    return Object.keys(by).map(function (k) { return by[k]; })
      .sort(function (a, b) { return b.n - a.n; });
  }

  var ROUTES = {
    '/api/state': state,
    '/api/me': function () { return { ok: true, user: { name: 'you', must_change: false } }; },
    '/api/field': function () { return { ok: true, plants: plants }; },
    '/api/missions': function () { return { ok: true, missions: missions }; },
    '/api/recordings': function () { return { ok: true, recordings: [] }; },
    '/api/photos': function () {
      return { ok: true, total: plants.length, photos: plants.map(function (p) {
        return { photo: '', label: p.label, common_name: p.common_name,
                 plot: p.plot, ts: p.ts, confidence: p.confidence,
                 healthy: p.healthy };
      }) };
    },
    '/api/alerts': function () { return { ok: true, alerts: alerts }; },
    '/api/patrols': function () {
      return { ok: true, patrols: patrols, next: { name: 'Morning check', at: nextSeven() },
        day_names: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] };
    },
    '/api/settings': function () {
      var S = {}, defs = {
        'drive.max_speed_mps': [0.45, 'float', 0.02, 1.2],
        'drive.speed_limit': [0.6, 'float', 0.1, 1],
        'drive.reverse_on_low_batt': [true, 'bool'],
        'boom.target_l_per_ha': [200, 'float', 20, 600],
        'boom.max_l_per_ha': [400, 'float', 20, 600],
        'boom.max_ml_per_session': [4000, 'float', 50, 6000],
        'boom.ml_per_min_per_nozzle': [350, 'float', 20, 3000],
        'boom.tank_litres': [5.0, 'float', 0.5, 50],
        'boom.band_seconds': [1.2, 'float', 0.2, 10],
        'boom.pwm_hz': [10, 'float', 2, 50],
        'boom.min_duty': [0.15, 'float', 0.05, 0.9],
        'boom.require_arm_switch': [true, 'bool'],
        'probe.every_n_plants': [10, 'int', 0, 200],
        'probe.settle_s': [2.0, 'float', 0.2, 30],
        'probe.timeout_s': [25, 'float', 5, 120],
        'ai.min_confidence': [0.6, 'float', 0.3, 0.99],
        'ai.auto_spray_confidence': [0.85, 'float', 0.7, 0.99],
        'ai.inspect_seconds': [2, 'float', 0.5, 20],
        'ai.plant_spacing_mm': [350, 'int', 50, 3000],
        'ai.row_length_m': [20, 'float', 1, 500],
        'ai.rows': [2, 'int', 1, 40],
        'ai.row_gap_mm': [700, 'int', 200, 5000],
        'safety.battery.warn_v': [14.4, 'float', 6, 25],
        'safety.battery.stop_v': [13.6, 'float', 6, 25],
        'safety.return_home_pct': [25, 'int', 0, 90],
        'safety.tilt_stop_deg': [20, 'float', 5, 60],
        'record.enabled': [true, 'bool'],
        'record.every_seconds': [2, 'float', 0.5, 60],
        'record.keep_days': [30, 'int', 1, 365],
        'notify.on_problem': [true, 'bool'], 'notify.on_finish': [true, 'bool'],
        'notify.on_low_battery': [true, 'bool'], 'notify.on_estop': [true, 'bool'],
        'notify.telegram_token': ['', 'str'], 'notify.telegram_chat_id': ['', 'str']
      };
      Object.keys(defs).forEach(function (k) {
        var d = defs[k];
        S[k] = { value: d[0], type: d[1], min: d[2] === undefined ? null : d[2],
                 max: d[3] === undefined ? null : d[3] };
      });
      return { ok: true, settings: S, user: { name: 'you' },
        fitted: { encoders: true, imu: true, range: true, probe: true,
                  boom: true, drive: true, camera_measured: true },
        steering: { turning_circle_mm: 2779, max_wheel_deg: 24.7,
                    min_turn_radius_mm: 1174 },
        why: { encoders: '', imu: '', range: '', ai: '', probe: '',
               boom: '', drive: '', camera_measured: '' } };
    }
  };

  var realFetch = window.fetch;
  window.fetch = function (url, opts) {
    var path = String(url).replace(location.origin, '').split('?')[0];
    var body = {};
    try { body = JSON.parse((opts && opts.body) || '{}'); } catch (e) {}

    if (path === '/api/command') {
      var sv = servoCmd(body);
      if (sv) return json(sv);
      if (body.cmd === 'answer') pending = null;
      if (body.cmd === 'estop') alert1('The real one stops everything here.');
      return json({ ok: true, message: 'Preview only, nothing moved.' });
    }
    if (path === '/api/history') return json({ ok: true, days: days(), problems: tally() });
    if (path === '/api/samples') return json({ ok: true, samples: samples });
    if (path.indexOf('/api/plant/') === 0) {
      var plot = decodeURIComponent(path.split('/').pop());
      var h = plants.filter(function (p) { return p.plot === plot; });
      var extra = h.length ? [Object.assign({}, h[0], { ts: h[0].ts - 604800,
        label: 'healthy', common_name: 'Healthy plant', healthy: true,
        severity: 'none', action: 'none', sprayed: false, dose_ml: 0,
        advice: 'Nothing to do. Keep watering evenly.', treatment: '' })] : [];
      return json({ ok: true, plot: plot, history: h.concat(extra),
        summary: { n: h.length + extra.length, ill: h.filter(function (p) {
          return !p.healthy; }).length, sp: h.filter(function (p) {
          return p.sprayed; }).length, ml: 12 } });
    }
    if (path === '/api/settings' && opts && opts.method === 'POST')
      return fetch('/api/settings');
    if (path === '/api/notify/test')
      return json({ ok: false, message: 'Preview only - no rover to send it.' });
    if (path === '/api/logout') return json({ ok: true });
    if (ROUTES[path]) return json(ROUTES[path]());
    return realFetch.apply(window, arguments);
  };
  function json(o) {
    return Promise.resolve({ ok: true, status: 200, json: function () {
      return Promise.resolve(o); } });
  }
  function alert1() {}

  /* the console opens a websocket for live telemetry; answer it here */
  window.WebSocket = function () {
    var self = this;
    this.close = function () {};
    setTimeout(function () { if (self.onopen) self.onopen(); }, 30);
    setInterval(function () {
      if (self.onmessage) self.onmessage({ data: JSON.stringify(state()) });
    }, 500);
  };

  /* the camera images: draw a crop row instead of a video stream */
  function fakeCam(img, tag) {
    var c = document.createElement('canvas');
    c.width = 480; c.height = 360;
    c.id = img.id;
    img.parentNode.replaceChild(c, img);
    // the real console shows an "offline" panel when /cam/front 404s, which
    // it always does in a file:// preview - the canvas below is the picture
    var off = document.getElementById('camOff');
    if (off) off.hidden = true;
    var g = c.getContext('2d'), t = 0;
    setInterval(function () {
      t += 0.06;
      g.fillStyle = '#6b5340'; g.fillRect(0, 0, 480, 360);
      for (var i = 0; i < 420; i += 7) {
        g.fillStyle = 'rgba(0,0,0,.05)'; g.fillRect(0, i, 480, 3);
      }
      for (var col = 0; col < 2; col++) {
        for (var k = 0; k < 8; k++) {
          var yy = ((k * 52 + t * 26) % 420) - 30;
          var r = 9 + yy / 16;
          if (r < 2) continue;
          g.beginPath();
          g.arc(150 + col * 180 + Math.sin(k + t / 3) * 7, yy, r, 0, 6.2832);
          g.fillStyle = (k % 5 === 1) ? '#9aa83a' : '#4f9e3f';
          g.fill();
        }
      }
      g.strokeStyle = 'rgba(217,164,65,.75)'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(240, 360); g.lineTo(240 + Math.sin(t / 4) * 26, 120);
      g.stroke();
      g.fillStyle = 'rgba(0,0,0,.55)'; g.fillRect(0, 0, 150, 20);
      g.fillStyle = '#d7e6da'; g.font = '12px ui-monospace,monospace';
      g.fillText(tag + '  ' + new Date().toLocaleTimeString(), 6, 14);
    }, 90);
  }
  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
      var f = document.getElementById('camF');
      if (f) fakeCam(f, 'FRONT');
    }, 400);
  });
}());
</script>
"""

BANNER = """
  <div class="wrap" style="padding-bottom:0">
    <div class="card" style="border-color:var(--amber-dim);background:#1b1710">
      <div class="body" style="gap:6px">
        <div class="row"><b style="color:var(--amber)">Preview</b>
          <span class="note">Every reading, camera and plant on this page is
          invented, so you can click through the whole console without a rover.
          The real one is served by the Pi on the rover at
          <span class="num">http://&lt;pi-address&gt;:8080</span>, behind a sign
          in, showing the live camera and the real sensors.</span></div>
      </div>
    </div>
  </div>
"""


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview.html")
    html = open(os.path.join(STATIC, "index.html"), encoding="utf-8").read()
    css = open(os.path.join(STATIC, "style.css"), encoding="utf-8").read()
    charts = open(os.path.join(STATIC, "charts.js"), encoding="utf-8").read()
    app = open(os.path.join(STATIC, "app.js"), encoding="utf-8").read()

    html = html.replace('<link rel="stylesheet" href="/static/fonts.css">\n', "")
    html = re.sub(r'<link rel="stylesheet" href="/static/style\.css">',
                  "<style>\n" + css + "\n</style>", html)
    html = html.replace('<script src="/static/charts.js"></script>',
                        "<script>\n" + charts + "\n</script>")
    html = html.replace('<script src="/static/app.js"></script>',
                        SHIM + "<script>\n" + app + "\n</script>")
    anchor = re.search(r'<div id="banner" class="banner">.*?</div>', html, re.S)
    if anchor:
        html = html.replace(anchor.group(0), anchor.group(0) + BANNER)

    # the preview has no rover to download a file from, and the viewer it runs
    # in blocks downloads anyway, so the links become plain text
    html = html.replace(
        '<a class="note" href="/api/report.csv">Download everything as CSV</a>',
        '<span class="note">The real one downloads the whole log as a CSV here</span>')
    html = html.replace(
        '<a class="note" href="/api/report.csv">Download the log as CSV</a>',
        '<span class="note">CSV download works on the rover itself</span>')

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote %s  (%d KB)" % (out, len(html) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
