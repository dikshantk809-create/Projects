/* AR-750 console - the whole front end.
   ---------------------------------------------------------------------------
   No framework, no CDN: the rover often has no internet where it works, and a
   console that needs a download to render is a console that does not render in
   a polytunnel.

   Three habits run through the file:

     1. The websocket is the live path and polling is the fallback, so the page
        keeps updating on a flaky field wifi instead of freezing at the last
        frame it received.
     2. Numbers are tweened, never snapped. A figure that jumps is a figure you
        misread; a figure that slides tells you which way it is going.
     3. Every state that is drawn in colour is also drawn as a shape. Green and
        red are the one pair a red-green colourblind eye cannot separate, and a
        farm tool that hides "sprayed" from a third of the men who use it is a
        broken farm tool.
*/
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };

  var S = {};                     // latest snapshot from the rover
  window.S = S;
  var ws = null, poll = null, wsOK = false;
  var trail = [], page = 'live', cache = {}, lastAsk = 0, chartHours = 6;
  var hist = { batt: [], tank: [], soil: [] }, lastHist = 0;
  var plantFilter = '';
  var fieldView = null;            // {cx, cy, scale} or null for "fit"

  /* ------------------------------------------------------------- storage -- */
  function store(k, v) {
    try {
      if (v === undefined) return localStorage.getItem('ar750.' + k);
      localStorage.setItem('ar750.' + k, v);
    } catch (e) { /* private window, or storage blocked - never fatal */ }
    return null;
  }

  /* --------------------------------------------------------------- utils -- */
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function n(v, dp) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return Number(v).toFixed(dp === undefined ? 1 : dp);
  }
  function when(t) {
    var d = new Date(t * 1000), now = new Date();
    var same = d.toDateString() === now.toDateString();
    var hm = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
    return same ? hm : d.getDate() + ' ' +
      d.toLocaleString(undefined, { month: 'short' }) + ' ' + hm;
  }
  function ago(t) {
    var s = Date.now() / 1000 - t;
    if (s < 90) return 'just now';
    if (s < 5400) return Math.round(s / 60) + ' min ago';
    if (s < 172800) return Math.round(s / 3600) + ' hours ago';
    return Math.round(s / 86400) + ' days ago';
  }
  function dur(s) {
    if (!s || s < 60) return Math.round(s || 0) + ' s';
    if (s < 3600) return Math.round(s / 60) + ' min';
    var h = Math.floor(s / 3600);
    return h + ' h ' + Math.round((s - h * 3600) / 60) + ' m';
  }
  function nice(l) {
    return String(l || 'unknown').replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }
  function icon(id, cls) {
    return '<svg class="' + (cls || '') + '"><use href="#' + id + '"/></svg>';
  }
  var REDUCED = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Tween a number in place. Snapping a figure five times a second makes it
     unreadable; sliding it makes the direction obvious without reading. */
  function setNum(el, value, fmtFn) {
    if (!el) return;
    fmtFn = fmtFn || function (v) { return n(v, 1); };
    var to = Number(value);
    if (isNaN(to)) { el.textContent = '—'; el._v = undefined; return; }
    var from = el._v;
    el._v = to;
    if (REDUCED || from === undefined || Math.abs(to - from) < 1e-9) {
      el.textContent = fmtFn(to); return;
    }
    if (el._raf) cancelAnimationFrame(el._raf);
    var t0 = performance.now(), ms = 420;
    (function step(now) {
      var k = Math.min(1, (now - t0) / ms);
      var e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmtFn(from + (to - from) * e);
      if (k < 1) el._raf = requestAnimationFrame(step);
    })(t0);
  }

  /* ---------------------------------------------------------------- toast - */
  function toast(msg, kind) {
    var box = $('#toasts');
    var el = document.createElement('div');
    el.className = 'toast ' + (kind || '');
    el.innerHTML = icon(kind === 'bad' ? 'i-warn' : kind === 'good' ? 'i-check' : 'i-msg') +
      '<span>' + esc(msg) + '</span>';
    box.appendChild(el);
    setTimeout(function () {
      el.classList.add('out');
      setTimeout(function () { el.remove(); }, 300);
    }, 3400);
    while (box.children.length > 4) box.firstChild.remove();
  }
  window.toast = toast;

  /* ------------------------------------------------------------- talking -- */
  function api(path, body) {
    var o = { credentials: 'same-origin' };
    if (body) {
      o.method = 'POST';
      o.headers = { 'Content-Type': 'application/json' };
      o.body = JSON.stringify(body);
    }
    return fetch(path, o).then(function (r) {
      if (r.status === 401) { location.href = '/login'; throw new Error('signed out'); }
      return r.json();
    });
  }
  function cmd(name, args) {
    return api('/api/command', { cmd: name, args: args || {} })
      .then(function (r) {
        if (r && r.message) toast(r.message, r.ok === false ? 'bad' : '');
        else if (r && r.ok === false && r.error) toast(r.error, 'bad');
        return r;
      })
      .catch(function () { toast('That did not reach the rover', 'bad'); });
  }
  window.cmd = cmd;

  /* The websocket is the live path. If it will not open, or it drops, the page
     falls back to polling /api/state so it keeps working on a bad wifi. */
  function connect() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    try { ws = new WebSocket(proto + '://' + location.host + '/ws'); }
    catch (e) { startPolling(); return setTimeout(connect, 2500); }
    ws.onopen = function () {
      wsOK = true; stopPolling(); startCam(true);
      setLink(true);
    };
    ws.onmessage = function (ev) {
      try { S = JSON.parse(ev.data); window.S = S; draw(); } catch (e) {}
    };
    ws.onclose = function () {
      wsOK = false; setLink(false); startPolling(); setTimeout(connect, 2200);
    };
    ws.onerror = function () { try { ws.close(); } catch (e) {} };
  }
  function startPolling() {
    if (poll) return;
    poll = setInterval(function () {
      api('/api/state').then(function (s) {
        S = s; window.S = S; draw(); setLink(true, true);
      }).catch(function () { setLink(false); });
    }, 1200);
  }
  function stopPolling() { clearInterval(poll); poll = null; }

  function setLink(ok, polling) {
    var c = $('#cLink');
    if (!ok) {
      c.className = 'chip bad';
      c.lastChild.textContent = 'no connection';
      return;
    }
    // "simulation" only when the wheels are not driven. Live wheels with a
    // sensor or two still pretending say "live" first, because that is the
    // part that can hurt someone, and name the rest on hover.
    var parts = (!S.sim && S.sim_parts) ? S.sim_parts : [];
    c.className = 'chip live ' + (S.sim ? 'warn' : 'on');
    c.lastChild.textContent = (S.sim ? 'simulation' : 'live') +
      (parts.length ? ' · ' + parts.length + ' simulated' : '') +
      (polling ? ' · slow link' : '');
    c.title = S.sim ? 'Simulation: the wheels are not driven' :
      parts.length ? 'Wheels are live. Still simulated: ' + parts.join(', ') :
      'Everything is live';
  }

  /* ---------------------------------------------------------------- camera */
  var camTimer = null;
  var NO_PIC = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
  // The picture only streams while someone can see it: on the Live or the
  // Remote page, with this tab in front, and into ONE picture at a time.
  // Anywhere else it was still pulling video over the wifi and slowing down
  // everything else on the page.
  var CAMS = { live: ['#camF', '#camOff'], remote: ['#rmCam', '#rmCamOff'] };
  function camWanted() { return !!CAMS[page] && !document.hidden; }
  function streaming(img) { return !!(img && img.src && img.src.indexOf('/cam/front') !== -1); }
  function quiet(img) {
    if (!img) return;
    img.onerror = null;
    img.onload = null;
    if (streaming(img)) img.src = NO_PIC;
  }
  function stopCam() {
    clearTimeout(camTimer);
    Object.keys(CAMS).forEach(function (k) { quiet($(CAMS[k][0])); });
  }
  document.addEventListener('visibilitychange', function () {
    if (camWanted()) startCam(true); else stopCam();
  });
  // force: open a fresh stream even if one looks open - after the socket
  // reconnects, the old stream has usually died with it
  function startCam(force) {
    clearTimeout(camTimer);
    if (!camWanted()) { stopCam(); return; }
    var img = $(CAMS[page][0]), off = $(CAMS[page][1]);
    if (!img) return;                    // the offline preview swaps in a canvas
    Object.keys(CAMS).forEach(function (k) { if (k !== page) quiet($(CAMS[k][0])); });
    if (!force && streaming(img)) return;
    img.onerror = function () {
      // The rover ends the stream when it has had no frame for a few seconds,
      // so this fires instead of the picture hanging for ever. Try again on a
      // slow loop: a camera that was unplugged is usually plugged back in.
      if (off) off.hidden = false;
      clearTimeout(camTimer);
      camTimer = setTimeout(function () { startCam(true); }, 12000);
    };
    img.onload = function () { if (off) off.hidden = true; };
    img.src = '/cam/front?t=' + Date.now();
  }
  window.zoomCam = function () {
    var b = $('#camBox');
    b.classList.toggle('zoom');
    if (b.classList.contains('zoom')) {
      document.addEventListener('keydown', escCam);
    }
  };
  function escCam(ev) {
    if (ev.key === 'Escape') {
      $('#camBox').classList.remove('zoom');
      document.removeEventListener('keydown', escCam);
    }
  }
  window.snapPhoto = function () {
    var img = $('#camF');
    if (!img || !img.naturalWidth) { toast('No picture to save yet', 'bad'); return; }
    try {
      var c = document.createElement('canvas');
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      c.getContext('2d').drawImage(img, 0, 0);
      var a = document.createElement('a');
      a.download = 'ar750_' + new Date().toISOString().replace(/[:.]/g, '-') + '.png';
      a.href = c.toDataURL('image/png');
      a.click();
      toast('Frame saved', 'good');
    } catch (e) { toast('The browser would not let me save that frame', 'bad'); }
  };
  window.toggleRecord = function () {
    cmd('record', { on: !S.recording });
  };

  /* -------------------------------------------------------------- theming - */
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    var m = document.querySelector('meta[name=theme-color]');
    if (m) m.setAttribute('content', t === 'light' ? '#F4F6F3' : '#0A0F0D');
    var use = $('#btnTheme svg use');
    if (use) use.setAttribute('href', t === 'light' ? '#i-moon' : '#i-sun');
    store('theme', t);
    // charts read their colours from the tokens, so they need a repaint
    if (page === 'charts') loadCharts();
    if (page === 'field') drawField();
  }
  window.toggleTheme = function () {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'light'
      ? 'dark' : 'light');
  };

  /* ------------------------------------------------------------ the pages - */
  function go(name) {
    if (!$('#p-' + name)) name = 'live';
    page = name;
    document.body.setAttribute('data-page', name);
    $$('.navbtn').forEach(function (b) {
      if (b.dataset.page === name) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
    $$('.page').forEach(function (p) {
      var on = p.id === 'p-' + name;
      p.hidden = !on;
      if (on) { p.removeAttribute('data-anim'); void p.offsetWidth; p.setAttribute('data-anim', '1'); }
    });
    moveSlider();
    if (history.replaceState) history.replaceState(null, '', '#' + name);
    // the picture follows you between Live and Remote, and stops elsewhere
    if (CAMS[name]) startCam(); else stopCam();
    if (name === 'remote') drawRemote();
    else if (name === 'arm') drawArm();
    load(name);
    window.scrollTo({ top: 0, behavior: REDUCED ? 'auto' : 'smooth' });
  }
  window.go = go;

  function moveSlider() {
    var sl = $('#navSlider'), cur = $('.navbtn[aria-current="page"]');
    if (!sl || !cur || window.innerWidth <= 900) { if (sl) sl.style.opacity = 0; return; }
    sl.style.opacity = 1;
    sl.style.height = cur.offsetHeight + 'px';
    sl.style.transform = 'translateY(' + cur.offsetTop + 'px)';
  }

  function load(name) {
    if (name === 'field') return loadField();
    if (name === 'plants') return loadPlants();
    if (name === 'charts') return loadCharts();
    if (name === 'runs') return loadRuns();
    if (name === 'alerts') return loadAlerts();
    if (name === 'timetable') return loadPatrols();
    if (name === 'settings') return loadSettings();
  }

  /* =============================================================== LIVE === */
  function draw() {
    if (!S.mode) return;
    setLink(true, !wsOK);
    if (page === 'remote') drawRemote();
    else if (page === 'arm') drawArm();

    pill('#cMode', S.mode, S.mode === 'AUTO' ? 'on live' : S.mode === 'ESTOP' ? 'bad'
      : S.mode === 'MANUAL' ? 'amber' : '');
    pill('#cRC', S.rc_live ? 'remote live' : 'remote off', S.rc_live ? 'on live' : '');
    // a skid (tank-style) rover has no wheels to point: say how it turns,
    // and put the car-steering card away
    var skidNow = (S.drive_hw || {}).layout === 'skid';
    if ($('#steerCard')) $('#steerCard').hidden = skidNow;
    if ($('#liveHow')) $('#liveHow').textContent = skidNow
      ? 'Up and down is throttle, left and right turns it by running one side faster. Sideways on its own spins it on the spot, like a tank.'
      : 'Up and down is throttle, left and right points the front wheels. This machine steers like a car: it cannot turn on the spot.';
    pill('#cAI', S.ai_ready === true ? 'AI ready' : 'no AI model',
      S.ai_ready === true ? 'on' : 'warn');
    $('#cAI').title = S.ai_ready === true ? 'the plant model is loaded'
      : 'it will not guess a disease: ' + (S.ai_reason || 'no model');
    pill('#cSpray', S.spray_armed ? (S.auto_spray ? 'spray ARMED + auto' : 'spray ARMED')
      : 'spray locked', S.spray_armed ? 'bad' : '');

    var b = $('#banner');
    b.classList.toggle('on', !!S.estop);
    if (S.estop) $('#bannerText').textContent = 'EMERGENCY STOP — ' + (S.estop_reason || '');
    $('#btnClear').hidden = !S.estop;

    ['IDLE', 'MANUAL', 'AUTO', 'HOLD'].forEach(function (m) {
      $('#m' + m).className = S.mode === m ? 'sel' : '';
    });
    $('#btnArm').className = S.spray_armed ? 'stop' : '';
    $('#btnArm').textContent = S.spray_armed ? 'Disarm the pump' : 'Arm the pump';
    $('#btnAuto').className = S.auto_spray ? 'stop' : '';
    $('#btnLamps').className = 'sm' + (S.lamps_on ? ' sel' : '');
    $('#recDot').hidden = !S.recording;
    $('#btnRec').textContent = S.recording ? 'Stop recording' : 'Start recording';
    $('#btnRec').className = 'sm' + (S.recording ? ' stop' : '');

    var t = S.telemetry || {};

    /* -------- the four gauges */
    // A real rover with no ADC cannot measure its pack. Say so, rather than
    // draw an invented percentage that someone might trust.
    if (t.battery_measured === false && !S.sim) {
      gauge('gBatt', 0, 'var(--line)');
      $('#vBattPct').textContent = '—';
      $('#vBattPct').nextElementSibling.textContent = '';
      $('#vBatt').textContent = 'not measured - no ADC fitted';
    } else {
      gauge('gBatt', t.battery_pct,
        t.battery_pct < 20 ? 'var(--bad)' : t.battery_pct < 40 ? 'var(--attn)' : 'var(--good)');
      setNum($('#vBattPct'), t.battery_pct, function (v) { return Math.round(v); });
      $('#vBattPct').nextElementSibling.textContent = '%';
      $('#vBatt').textContent = n(t.battery_v, 2) + ' V · ' + n(t.current_a, 1) + ' A';
    }

    gauge('gTank', t.tank_pct, 'var(--spray)');
    setNum($('#vTankPct'), t.tank_pct, function (v) { return Math.round(v); });
    $('#vTank').textContent = Math.round(t.tank_ml || 0) + ' ml left';

    var soilKnown = t.soil_pct !== null && t.soil_pct !== undefined;
    gauge('gSoil', soilKnown ? t.soil_pct : 0,
      !soilKnown ? 'var(--line)' : t.soil_pct < 25 ? 'var(--bad)'
        : t.soil_pct < 40 ? 'var(--attn)' : 'var(--s-3)');
    if (soilKnown) setNum($('#vSoilPct'), t.soil_pct, function (v) { return Math.round(v); });
    else $('#vSoilPct').textContent = t.soil_state ? (t.soil_state === 'wet' ? 'wet' : 'dry') : '—';
    // a percent sign only under a percentage
    $('#vSoilPct').nextElementSibling.textContent = soilKnown ? '%' : '';
    $('#vSoil').textContent = soilKnown ? 'measured by the probe'
      : t.soil_state ? 'sensor says ' + t.soil_state + ' (no ADC, so no %)' : 'no reading yet';

    var m = S.mission || {};
    var jobPct = m.plants_target ? Math.min(100, (m.plants_done || 0) / m.plants_target * 100)
      : (m.running ? 0 : 0);
    gauge('gJob', jobPct, 'var(--amber)');
    if (m.plants_target) {
      $('#vJobPct').textContent = Math.round(jobPct) + '%';
      $('#vJobUnit').textContent = 'done';
      $('#vJobSub').textContent = (m.plants_done || 0) + ' of ' + m.plants_target + ' plants';
    } else {
      // no target set means "as many as it finds", so a percentage would be a
      // fraction of an unknown - show the count it has actually done instead
      $('#vJobPct').textContent = m.plants_done || 0;
      $('#vJobUnit').textContent = 'plants';
      $('#vJobSub').textContent = m.running ? 'the whole row' : 'not running';
    }

    /* -------- sparkline history, about every two seconds */
    var now = Date.now();
    if (now - lastHist > 1800) {
      lastHist = now;
      push(hist.batt, t.battery_pct); push(hist.tank, t.tank_pct);
      push(hist.soil, soilKnown ? t.soil_pct : null);
      if (page === 'live') {
        Chart.spark($('#spkBatt'), { points: hist.batt, colour: Chart.token('--s-1') });
        Chart.spark($('#spkTank'), { points: hist.tank, colour: Chart.token('--s-7') });
        Chart.spark($('#spkSoil'), { points: hist.soil, colour: Chart.token('--s-3') });
      }
    }

    /* -------- the stat tiles */
    setNum($('#vSpeed'), t.speed_mps, function (v) { return n(v, 2) + ' m/s'; });
    $('#sSpeed').textContent = 'limit ' + Math.round((S.speed_limit || 0) * 100) + '%';
    setNum($('#vDist'), t.distance_m, function (v) { return n(v, 1) + ' m'; });
    $('#vDistSub').textContent = t.odometry_measured ? 'measured' : 'estimated, drifts';
    $('#vDistSub').style.color = t.odometry_measured ? 'var(--good)' : 'var(--dim)';
    setNum($('#vCpu'), t.cpu_temp_c, function (v) { return Math.round(v) + ' °C'; });
    $('#vRange').textContent = t.range_front_cm == null ? '—'
      : Math.round(t.range_front_cm) + ' cm';
    $('#sRange').textContent = t.range_front_cm == null ? 'no range sensor' : 'clear';
    $('#vUp').textContent = dur(t.uptime_s);

    var plants = S.plants || [];
    $('#vChecked').textContent = plants.length;
    var bad = plants.filter(function (p) { return !p.healthy; }).length;
    $('#vAttn').textContent = bad;
    $('#navAttn').textContent = bad || '';
    $('#navAttn').hidden = !bad;
    var unseen = (S.alerts || []).filter(function (a) { return !a.seen; }).length;
    $('#navAlerts').textContent = unseen || '';
    $('#navAlerts').hidden = !unseen;

    /* -------- the camera overlay */
    $('#osdSpeed').textContent = n(t.speed_mps, 2) + ' m/s';
    $('#osdHead').textContent = Math.round(t.heading_deg || 0) + '°';
    $('#osdMode').textContent = S.mode;

    /* -------- the job */
    var R = t.turn_radius_mm;
    $('#missionKv').innerHTML =
      kv('Job', m.running ? 'running' : 'stopped') +
      kv('Step', m.step || '—') +
      kv('Row', (m.rows_target > 1
        ? ((m.rows_done || 0) + 1) + ' of ' + m.rows_target
        : (m.row || '—'))) +
      kv('Sprayed', (m.sprayed_ml || 0) + ' ml');
    ring('gMission', jobPct, 207.3);
    $('#gMissionTxt').textContent = Math.round(jobPct) + '%';
    $('#missionMsg').textContent = m.message || '';
    $('#btnGoHome').hidden = !!S.returning;
    $('#btnStopHome').hidden = !S.returning;

    /* -------- steering. This machine points its wheels; it does not spin. */
    var dr = S.drive || {}, sg = S.steering || {}, hw = S.drive_hw || {};
    $('#steerViz').innerHTML = steerSvg(dr.steer_deg || 0, sg.max_wheel_deg || 28);
    $('#steerKv').innerHTML =
      kv('Front wheels', n(dr.steer_deg, 1) + '° ' +
        (Math.abs(dr.steer_deg || 0) < 0.5 ? 'straight'
          : (dr.steer_deg > 0 ? 'left' : 'right'))) +
      kv('Turning radius', R ? n(R / 1000, 2) + ' m' : 'going straight') +
      kv('Throttle', n((dr.throttle || 0) * 100, 0) + '%') +
      (hw.driver === 'bts7960'
        ? kv('Motor drive', n((hw.front_duty || 0) * 100, 0) + '% / ' +
          n((hw.rear_duty || 0) * 100, 0) + '%  (BTS7960)')
        : kv('ESC pulses', (hw.front_us || 0) + ' / ' + (hw.rear_us || 0) + ' us')) +
      kv('Steering servo', (hw.steer_us || 0) + ' us');
    $('#steerNote').textContent = sg.max_wheel_deg
      ? ('Full lock is ' + n(sg.max_wheel_deg, 1) + '° at the wheels, which needs a '
        + n(sg.turning_circle_mm / 1000, 2) + ' m circle. It cannot turn on the spot.')
      : '';
    $('#vTurn').textContent = R ? n(R / 1000, 2) + ' m' : 'straight';
    $('#sTurn').textContent = sg.max_wheel_deg
      ? ('min ' + n(sg.min_turn_radius_mm / 1000, 2) + ' m') : '';

    /* -------- the boom */
    var bm = S.boom || {};
    var open = bm.sections || [];
    $('#nozzleRow').innerHTML = ['left', 'left', 'centre', 'right', 'right']
      .map(function (sec, i) {
        var on = bm.pump_on && open.indexOf(sec) >= 0;
        return '<span title="nozzle ' + (i + 1) + ', ' + sec + ' section" ' +
          'style="flex:1;height:26px;border-radius:7px;border:1px solid ' +
          (on ? 'var(--spray-line)' : 'var(--line)') + ';background:' +
          (on ? 'var(--spray-bg)' : 'var(--panel-2)') + ';display:grid;' +
          'place-items:center;font:500 10px var(--mono);color:' +
          (on ? 'var(--spray)' : 'var(--dim)') + '">' + (on ? '◆' : '·') + '</span>';
      }).join('');
    $('#boomKv').innerHTML =
      kv('Pump', bm.pump_on ? 'RUNNING' : 'off') +
      kv('Sections open', open.length ? open.join(' + ') : 'none') +
      kv('Target rate', bm.target_l_per_ha ? bm.target_l_per_ha + ' l/ha' : '—') +
      kv('Valves open', bm.pump_on ? n((bm.duty || 0) * 100, 0) + '% of the time' : '—') +
      kv('Used this outing', n(bm.used_ml, 0) + ' ml') +
      kv('Left in the tank', n(bm.remaining_ml, 0) + ' ml');

    /* -------- the soil probe */
    var pb = S.probe_hw || {};
    $('#probeKv').innerHTML =
      kv('Where it is', pb.state || 'unknown') +
      kv('Moving', pb.moving && pb.moving !== 'stopped' ? pb.moving : 'no') +
      kv('Travel', n(pb.travel_mm, 0) + ' mm') +
      kv('Last soil reading', soilKnown ? n(t.soil_pct, 0) + '%' : 'none yet') +
      kv('Fitted', pb.fitted ? 'yes' : 'not detected');

    var np = S.next_patrol;
    $('#nextPatrol').textContent = np
      ? 'Next patrol: ' + np.name + ', ' + when(np.at) : 'No patrol set';

    drawAsk();
    drawPlants(plants);
    drawLog();
    if (page === 'live') drawTrail(t);
  }

  function push(arr, v) {
    arr.push(v === null || v === undefined ? null : Number(v));
    if (arr.length > 80) arr.shift();
  }
  function pill(sel, text, cls) {
    var el = $(sel);
    el.className = 'chip ' + (cls || '');
    el.lastChild.textContent = text;
  }
  function kv(k, v) {
    return '<div class="kv"><span>' + esc(k) + '</span><span>' + esc(v) + '</span></div>';
  }
  function ring(id, pct, circ) {
    var el = document.getElementById(id);
    if (!el) return;
    var p = Math.max(0, Math.min(100, pct || 0));
    el.setAttribute('stroke-dashoffset', circ * (1 - p / 100));
  }
  function gauge(id, pct, colour) {
    var el = document.getElementById(id);
    if (!el) return;
    ring(id, pct, 314.16);
    el.style.stroke = colour;
  }

  /* A small top-down picture of the front axle. The number says the angle;
     the picture says which way, which is the bit you read at a glance. */
  function steerSvg(deg, max) {
    var a = Math.max(-max, Math.min(max, deg));
    return '<svg viewBox="0 0 220 96" style="width:100%;height:78px;display:block">' +
      '<rect x="86" y="18" width="48" height="60" rx="9" fill="var(--panel-2)" ' +
        'stroke="var(--line)"/>' +
      '<line x1="110" y1="30" x2="110" y2="66" stroke="var(--line-bright)" ' +
        'stroke-width="2"/>' +
      ['left', 'right'].map(function (side, i) {
        var cx = i ? 150 : 70;
        return '<g transform="translate(' + cx + ',30) rotate(' + (-a) + ')">' +
          '<rect x="-7" y="-13" width="14" height="26" rx="4" ' +
          'fill="var(--amber)" opacity=".9"/></g>';
      }).join('') +
      '<rect x="63" y="53" width="14" height="26" rx="4" fill="var(--dim)" opacity=".55"/>' +
      '<rect x="143" y="53" width="14" height="26" rx="4" fill="var(--dim)" opacity=".55"/>' +
      '<text x="110" y="92" text-anchor="middle" fill="var(--dim)" ' +
        'font-family="var(--mono)" font-size="10">front axle · ' +
        n(a, 1) + '°</text></svg>';
  }

  function drawAsk() {
    var p = S.pending;
    $('#askWrap').hidden = !p;
    if (!p) return;
    $('#askTitle').textContent = p.title || '';
    $('#askText').textContent = p.question || '';
    var img = $('#askPhoto');
    if (p.photo) { img.src = '/photos/' + p.photo; img.hidden = false; }
    else img.hidden = true;
    if (p.time && p.time > lastAsk) {
      lastAsk = p.time;
      if (page !== 'live') toast('The rover needs your answer', 'bad');
      try { if (navigator.vibrate) navigator.vibrate([90, 60, 90]); } catch (e) {}
      try {
        if (window.Notification && Notification.permission === 'granted')
          new Notification('AgriRover needs you', { body: p.question });
      } catch (e) {}
    }
  }

  function plantShape(p) {
    return p.sprayed ? '◆' : p.healthy ? '●' : '▲';
  }
  function plantTag(p) {
    if (p.sprayed) return '<span class="tag sprayed">sprayed</span>';
    var sev = p.healthy ? 'ok' : (p.severity || 'mild');
    return '<span class="tag ' + sev + '">' + (p.healthy ? 'fine' : sev) + '</span>';
  }

  function drawPlants(plants) {
    var tb = $('#tblLive');
    // The snapshot arrives five times a second. Rebuilding the table on every
    // one of them costs a full re-layout and loses any text the user has
    // selected, so only rebuild when the list has actually changed.
    var lastRow = plants[plants.length - 1] || {};
    var sig = plants.length + '|' + lastRow.id + '|' + lastRow.action;
    if (tb._sig === sig) return;
    tb._sig = sig;
    if (!plants.length) {
      tb.innerHTML = '<tr><td colspan="6"><div class="empty">' + icon('i-plant') +
        '<span>Nothing checked yet this run.</span></div></td></tr>';
      return;
    }
    tb.innerHTML = plants.slice().reverse().map(function (p) {
      return '<tr class="click" onclick="openPlant(\'' + esc(p.plot) + '\')">' +
        '<td data-l="Plant" class="num">' + esc(p.plot || p.id) + '</td>' +
        '<td data-l="Found"><b>' + esc(nice(p.label)) + '</b></td>' +
        '<td data-l="Sure" class="num">' + Math.round((p.confidence || 0) * 100) + '%</td>' +
        '<td data-l="How bad">' + plantTag(p) + '</td>' +
        '<td data-l="It did">' + esc(didWhat(p)) + '</td>' +
        '<td data-l="You do" class="note">' + esc(p.advice || '') + '</td></tr>';
    }).join('');
  }
  function didWhat(p) {
    return ({
      sprayed: 'sprayed ' + (p.dose_ml || 0) + ' ml', weed_pulled: 'weed pulled',
      needs_you: 'waiting for you', declined: 'you skipped it',
      seen_by_you: 'you marked it seen', none: 'nothing needed'
    })[p.action] || String(p.action || '').replace(/_/g, ' ') || '—';
  }

  function drawLog() {
    var box = $('#logBox'), lines = S.log || [];
    var sig = lines.length + '|' + ((lines[0] || {}).time || 0);
    if (box._sig === sig) return;
    box._sig = sig;
    box.innerHTML = lines.map(function (l) {
      return '<div class="' + (l.level || '') + '"><time>' + when(l.time) + '</time>' +
        '<span>' + esc(l.text) + '</span></div>';
    }).join('') || '<div style="color:var(--dim)">Nothing yet.</div>';
  }

  /* --------------------------------------------------------- the live map - */
  window.clearTrail = function () { trail = []; toast('Trail cleared'); };

  function drawTrail(t) {
    var c = $('#trail'); if (!c) return;
    var W = c.parentNode.clientWidth, H = 210, r = devicePixelRatio || 1;
    c.width = W * r; c.height = H * r; c.style.height = H + 'px';
    var g = c.getContext('2d'); g.setTransform(r, 0, 0, r, 0, 0);
    g.clearRect(0, 0, W, H);

    var last = trail[trail.length - 1];
    if (!last || Math.abs(last.x - t.x_m) > 0.01 || Math.abs(last.y - t.y_m) > 0.01)
      trail.push({ x: t.x_m, y: t.y_m });
    if (trail.length > 2500) trail.shift();

    var pts = (S.plants || []).map(function (p) {
      return { x: p.x_m, y: p.y_m, healthy: p.healthy, sprayed: p.sprayed };
    });
    var all = trail.concat(pts).concat([{ x: 0, y: 0 }]);
    var xs = all.map(function (p) { return p.x; }), ys = all.map(function (p) { return p.y; });
    var minx = Math.min.apply(null, xs) - 0.6, maxx = Math.max.apply(null, xs) + 0.6;
    var miny = Math.min.apply(null, ys) - 0.6, maxy = Math.max.apply(null, ys) + 0.6;
    var sc = Math.min(W / Math.max(0.4, maxx - minx), H / Math.max(0.4, maxy - miny));
    var ox = (W - (maxx - minx) * sc) / 2, oy = (H - (maxy - miny) * sc) / 2;
    var X = function (x) { return ox + (x - minx) * sc; };
    var Y = function (y) { return H - (oy + (y - miny) * sc); };

    grid(g, W, H, minx, maxx, miny, maxy, X, Y);

    if (trail.length > 1) {
      // the trail fades out behind it, so "where it has just been" is obvious
      for (var i = 1; i < trail.length; i++) {
        var k = i / trail.length;
        g.beginPath();
        g.moveTo(X(trail[i - 1].x), Y(trail[i - 1].y));
        g.lineTo(X(trail[i].x), Y(trail[i].y));
        g.strokeStyle = 'rgba(63,185,80,' + (0.12 + 0.75 * k).toFixed(3) + ')';
        g.lineWidth = 2; g.lineCap = 'round'; g.stroke();
      }
    }
    pts.forEach(function (p) { marker(g, X(p.x), Y(p.y), p, 5); });

    // where it is now, pointing where it is going
    var hx = X(t.x_m), hy = Y(t.y_m), a = -(t.heading_deg || 0) * Math.PI / 180;
    g.save(); g.translate(hx, hy);
    g.beginPath(); g.arc(0, 0, 13, 0, 6.2832);
    g.fillStyle = 'rgba(224,172,75,.16)'; g.fill();
    g.rotate(a);
    g.beginPath(); g.moveTo(11, 0); g.lineTo(-7, 6.5); g.lineTo(-7, -6.5); g.closePath();
    g.fillStyle = Chart.token('--amber', '#E0AC4B'); g.fill();
    g.strokeStyle = Chart.token('--bg-2', '#070B09'); g.lineWidth = 1.5; g.stroke();
    g.restore();

    $('#trailPos').textContent = 'x ' + n(t.x_m, 2) + ' m · y ' + n(t.y_m, 2) +
      ' m · ' + Math.round(t.heading_deg || 0) + '°';
  }

  function grid(g, W, H, minx, maxx, miny, maxy, X, Y) {
    g.strokeStyle = Chart.token('--line-soft', '#1c251f'); g.lineWidth = 1;
    for (var gx = Math.ceil(minx); gx <= maxx; gx++) {
      g.beginPath(); g.moveTo(Math.round(X(gx)) + .5, 0);
      g.lineTo(Math.round(X(gx)) + .5, H); g.stroke();
    }
    for (var gy = Math.ceil(miny); gy <= maxy; gy++) {
      g.beginPath(); g.moveTo(0, Math.round(Y(gy)) + .5);
      g.lineTo(W, Math.round(Y(gy)) + .5); g.stroke();
    }
  }

  /* Colour AND shape. Green-vs-red is invisible to a deuteranope; the shape
     is not, so the map still reads without any colour at all. */
  function marker(g, x, y, p, r) {
    var col = p.sprayed ? Chart.token('--spray', '#9085E9')
      : p.healthy ? Chart.token('--good', '#3FB950')
        : Chart.token('--attn', '#E8853A');
    g.beginPath();
    if (p.sprayed) {                                   // ◆ diamond
      g.moveTo(x, y - r * 1.25); g.lineTo(x + r * 1.15, y);
      g.lineTo(x, y + r * 1.25); g.lineTo(x - r * 1.15, y); g.closePath();
    } else if (p.healthy) {                            // ● circle
      g.arc(x, y, r, 0, 6.2832);
    } else {                                           // ▲ triangle
      g.moveTo(x, y - r * 1.3); g.lineTo(x + r * 1.2, y + r * 0.9);
      g.lineTo(x - r * 1.2, y + r * 0.9); g.closePath();
    }
    g.fillStyle = col; g.fill();
    g.strokeStyle = Chart.token('--bg-2', '#070B09'); g.lineWidth = 1.6; g.stroke();
  }

  /* ============================================================== FIELD === */
  function loadField() {
    api('/api/field').then(function (r) {
      cache.field = r.plants || [];
      fieldView = null;
      drawField();
      $('#fieldCount').textContent = cache.field.length + ' plants known';
    });
  }
  window.fieldZoom = function (k) {
    if (!k) { fieldView = null; }
    else if (fieldView) { fieldView.scale *= k; }
    drawField();
  };
  function drawField() {
    var rows = cache.field || [];
    var c = $('#fieldMap'); if (!c) return;
    var box = c.parentNode;
    var W = box.clientWidth, H = Math.max(300, Math.min(560, W * 0.55));
    var r = devicePixelRatio || 1;
    c.width = W * r; c.height = H * r; c.style.height = H + 'px';
    var g = c.getContext('2d'); g.setTransform(r, 0, 0, r, 0, 0);
    g.clearRect(0, 0, W, H);
    if (!rows.length) {
      g.fillStyle = Chart.token('--dim', '#80928a');
      g.font = '13px system-ui'; g.textAlign = 'center';
      g.fillText('No plants recorded yet. Run AUTO once and they appear here.',
        W / 2, H / 2);
      return;
    }
    var xs = rows.map(function (p) { return p.x || 0; });
    var ys = rows.map(function (p) { return p.y || 0; });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
    var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    if (!fieldView) {
      var fit = Math.min((W - 60) / Math.max(0.5, maxx - minx + 1),
        (H - 60) / Math.max(0.5, maxy - miny + 1));
      fieldView = { cx: (minx + maxx) / 2, cy: (miny + maxy) / 2, scale: fit };
    }
    var sc = fieldView.scale;
    var X = function (x) { return W / 2 + (x - fieldView.cx) * sc; };
    var Y = function (y) { return H / 2 - (y - fieldView.cy) * sc; };
    var gminx = fieldView.cx - W / 2 / sc, gmaxx = fieldView.cx + W / 2 / sc;
    var gminy = fieldView.cy - H / 2 / sc, gmaxy = fieldView.cy + H / 2 / sc;
    grid(g, W, H, gminx, gmaxx, gminy, gmaxy, X, Y);

    c._hits = [];
    rows.forEach(function (p) {
      var x = X(p.x || 0), y = Y(p.y || 0);
      if (x < -20 || x > W + 20 || y < -20 || y > H + 20) return;
      marker(g, x, y, p, Math.max(5, Math.min(11, sc / 9)));
      if (sc > 26) {
        g.fillStyle = Chart.token('--ink', '#e9efe9');
        g.font = '600 9px ui-monospace,monospace';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(String(p.plot || '').replace(/^r\d+p/, ''), x, y + 17);
      }
      c._hits.push({ x: x, y: y, plot: p.plot, p: p });
    });
    g.fillStyle = Chart.token('--dim', '#80928a');
    g.font = '11px ui-monospace,monospace';
    g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillText('1 m grid · ' + rows.length + ' plants', 12, H - 12);

    wireField(c, W, H);
  }

  function wireField(c, W, H) {
    if (c._wired) return;
    c._wired = true;
    var drag = null;
    function pick(ev) {
      var b = c.getBoundingClientRect();
      var mx = ev.clientX - b.left, my = ev.clientY - b.top, best = null, bd = 400;
      (c._hits || []).forEach(function (h) {
        var d = (h.x - mx) * (h.x - mx) + (h.y - my) * (h.y - my);
        if (d < bd) { bd = d; best = h; }
      });
      return best;
    }
    c.addEventListener('mousedown', function (ev) {
      drag = { x: ev.clientX, y: ev.clientY, moved: false };
    });
    window.addEventListener('mousemove', function (ev) {
      if (!drag || !fieldView) return;
      var dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      fieldView.cx -= dx / fieldView.scale;
      fieldView.cy += dy / fieldView.scale;
      drag.x = ev.clientX; drag.y = ev.clientY;
      drawField();
    });
    window.addEventListener('mouseup', function (ev) {
      if (drag && !drag.moved) {
        var h = pick(ev);
        if (h) openPlant(h.plot);
      }
      drag = null;
    });
    c.addEventListener('wheel', function (ev) {
      if (!fieldView) return;
      ev.preventDefault();
      fieldView.scale *= ev.deltaY < 0 ? 1.12 : 1 / 1.12;
      fieldView.scale = Math.max(4, Math.min(400, fieldView.scale));
      drawField();
    }, { passive: false });
    c.addEventListener('mousemove', function (ev) {
      c.style.cursor = pick(ev) ? 'pointer' : 'grab';
    });
  }

  /* ============================================================= PLANTS === */
  function loadPlants() {
    api('/api/field').then(function (r) {
      cache.field = r.plants || [];
      renderPlantList();
    });
  }
  window.setPlantFilter = function (f) {
    plantFilter = f;
    $$('#plantFilter button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.f === f ? 'true' : 'false');
    });
    renderPlantList();
  };
  function renderPlantList() {
    var q = ($('#plantSearch').value || '').toLowerCase();
    var rows = (cache.field || []).filter(function (p) {
      if (plantFilter === 'bad' && p.healthy) return false;
      if (plantFilter === 'sprayed' && !p.sprayed) return false;
      if (!q) return true;
      return (String(p.plot) + ' ' + p.label + ' ' + (p.common_name || ''))
        .toLowerCase().indexOf(q) >= 0;
    });
    $('#plantCount').textContent = rows.length + ' shown';
    $('#tblField').innerHTML = rows.length ? rows.map(function (p) {
      return '<tr class="click" onclick="openPlant(\'' + esc(p.plot) + '\')">' +
        '<td data-l="Plant" class="num">' + plantShape(p) + ' ' + esc(p.plot) + '</td>' +
        '<td data-l="Last seen"><b>' + esc(p.common_name || nice(p.label)) + '</b>' +
        '<div class="note">' + ago(p.ts) + '</div></td>' +
        '<td data-l="How bad">' + plantTag(p) + '</td>' +
        '<td data-l="It did">' + esc(didWhat(p)) + '</td>' +
        '<td data-l="Treatment" class="note">' + esc(p.treatment || '—') + '</td></tr>';
    }).join('') : '<tr><td colspan="5"><div class="empty">' + icon('i-search') +
      '<span>No plants match that.</span></div></td></tr>';
  }
  window.renderPlantList = renderPlantList;

  function openPlant(plot) {
    if (!plot) return;
    $('#drawerBody').innerHTML = '<div class="sk sk-line" style="height:26px"></div>' +
      '<div class="sk sk-line"></div><div class="sk sk-line"></div>' +
      '<div class="sk" style="height:180px"></div>';
    $('#drawer').classList.add('on');
    api('/api/plant/' + encodeURIComponent(plot)).then(function (r) {
      var h = r.history || [], s = r.summary || {}, first = h[0] || {};
      $('#drawerBody').innerHTML =
        '<div class="row"><h2 style="font-size:21px">' + plantShape(first) +
        ' Plant ' + esc(plot) + '</h2><span class="spacer"></span>' +
        '<button class="iconbtn" onclick="closeDrawer()">' + icon('i-x') + '</button></div>' +
        '<div class="stats">' +
        tile('Times checked', s.n || 0) +
        tile('Problems', s.ill || 0) +
        tile('Sprayed', (s.sp || 0) + '×') +
        tile('Total dose', n(s.ml || 0, 0) + ' ml') +
        '</div>' +
        (first.photo ? '<img src="/photos/' + esc(first.photo) +
          '" alt="last photo of plant ' + esc(plot) + '" ' +
          'style="width:100%;border-radius:12px;border:1px solid var(--line)">' : '') +
        '<div class="card"><h2>What happened, newest first</h2><div class="body">' +
        h.map(function (x, i) {
          return '<div style="display:grid;gap:5px;padding:10px 0;border-bottom:' +
            '1px solid var(--line-soft);animation:fadein .3s ' + (i * 0.04) + 's both">' +
            '<div class="row"><b>' + esc(x.common_name || nice(x.label)) + '</b>' +
            plantTag(x) + '<span class="spacer"></span>' +
            '<span class="note">' + when(x.ts) + '</span></div>' +
            '<div class="note">' + esc(didWhat(x)) +
            (x.treatment ? ' — ' + esc(x.treatment) : '') + '</div>' +
            (x.advice ? '<div class="note">' + esc(x.advice) + '</div>' : '') +
            '</div>';
        }).join('') + '</div></div>';
    }).catch(function () {
      $('#drawerBody').innerHTML = '<div class="empty">' + icon('i-warn') +
        '<span>No history for that plant yet.</span>' +
        '<button class="sm" onclick="closeDrawer()">Close</button></div>';
    });
  }
  window.openPlant = openPlant;
  window.closeDrawer = function () { $('#drawer').classList.remove('on'); };
  function tile(label, value) {
    return '<div class="stat"><i>' + esc(label) + '</i><b>' + esc(value) + '</b></div>';
  }

  /* ============================================================= CHARTS === */
  window.setRange = function (h) {
    chartHours = h;
    $$('#chartRange button').forEach(function (b) {
      b.setAttribute('aria-pressed', +b.dataset.h === h ? 'true' : 'false');
    });
    loadCharts();
  };
  function delta(el, arr, unit, dp) {
    var vals = arr.filter(function (v) { return v !== null && !isNaN(v); });
    if (vals.length < 2) { el.textContent = '—'; el.className = 'delta'; return; }
    var d = vals[vals.length - 1] - vals[0];
    el.textContent = (d >= 0 ? '+' : '') + n(d, dp) + unit;
    el.className = 'delta ' + (Math.abs(d) < 1e-9 ? '' : d > 0 ? 'up' : 'down');
  }
  function loadCharts() {
    api('/api/samples?hours=' + chartHours).then(function (r) {
      var s = r.samples || [];
      var pick = function (k) {
        return s.map(function (x) { return { x: x.ts, y: x[k] }; });
      };
      var latest = s[s.length - 1] || {};
      $('#nowBatt').textContent = n(latest.battery_v, 2) + ' V';
      $('#nowSoil').textContent = latest.soil_pct == null ? '—' : n(latest.soil_pct, 0) + ' %';
      $('#nowTank').textContent = n(latest.tank_pct, 0) + ' %';
      delta($('#dBatt'), s.map(function (x) { return x.battery_v; }), ' V', 2);
      delta($('#dSoil'), s.map(function (x) { return x.soil_pct; }), ' %', 0);
      delta($('#dTank'), s.map(function (x) { return x.tank_pct; }), ' %', 0);
      Chart.line($('#chBatt'), { points: pick('battery_v'), colour: Chart.token('--s-1'),
        unit: ' V', dp: 2, height: 156 });
      Chart.line($('#chSoil'), { points: pick('soil_pct'), colour: Chart.token('--s-3'),
        unit: ' %', dp: 0, min: 0, max: 100, height: 156 });
      Chart.line($('#chTank'), { points: pick('tank_pct'), colour: Chart.token('--s-7'),
        unit: ' %', dp: 0, min: 0, max: 100, height: 156 });
    });
    api('/api/history?days=14').then(function (r) {
      var rows = (r.days || []).map(function (d) {
        return { label: d.day, short: d.day.slice(5).replace('-', '/'),
          a: d.checked || 0, b: d.problems || 0 };
      });
      Chart.bars($('#chDays'), { rows: rows, aName: 'checked', bName: 'problems',
        aColour: Chart.token('--s-1'), bColour: Chart.token('--s-2'), height: 196 });
      Chart.tally($('#tally'), (r.problems || []).map(function (p) {
        return { name: p.common_name || nice(p.label), n: p.n };
      }));
      var tot = (r.days || []).reduce(function (a, d) {
        a.c += d.checked || 0; a.p += d.problems || 0;
        a.s += d.sprayed || 0; a.m += d.ml || 0; return a;
      }, { c: 0, p: 0, s: 0, m: 0 });
      $('#sumStats').innerHTML =
        tile('Plants checked', tot.c) + tile('Problems', tot.p) +
        tile('Sprayed', tot.s) + tile('Chemical used', n(tot.m, 0) + ' ml');
    });
  }
  window.loadCharts = loadCharts;

  /* =============================================================== RUNS === */
  function loadRuns() {
    api('/api/missions').then(function (r) {
      $('#tblRuns').innerHTML = (r.missions || []).length ? r.missions.map(function (m) {
        var mins = m.ended ? Math.max(1, Math.round((m.ended - m.started) / 60)) : null;
        return '<tr>' +
          '<td data-l="When">' + when(m.started) + '<div class="note">' +
          (m.kind === 'patrol' ? 'timetabled patrol' : 'you started it') + '</div></td>' +
          '<td data-l="Lasted" class="num">' + (mins ? mins + ' min' : 'running') + '</td>' +
          '<td data-l="Plants" class="num">' + (m.plants_checked || 0) + '</td>' +
          '<td data-l="Problems" class="num">' + (m.problems || 0) + '</td>' +
          '<td data-l="Sprayed" class="num">' + n(m.sprayed_ml, 0) + ' ml</td>' +
          '<td data-l="Went" class="num">' + n(m.distance_m, 1) + ' m</td>' +
          '<td data-l="Ended" class="note">' + esc(m.note || '') + '</td></tr>';
      }).join('') : '<tr><td colspan="7"><div class="empty">' + icon('i-runs') +
        '<span>No runs yet.</span></div></td></tr>';
    });
    api('/api/photos?limit=400').then(function (r) {
      var ph = r.photos || [];
      $('#photoCount').textContent = ph.length
        ? ph.length + ' photos saved so far'
        : 'no photos yet';
      $('#gallery').innerHTML = ph.slice(0, 60).map(function (p) {
        return '<figure onclick="openPlant(\'' + esc(p.plot) + '\')">' +
          '<img loading="lazy" src="/photos/' + esc(p.photo) + '" alt="plant ' +
          esc(p.plot) + '">' +
          '<figcaption><span style="color:var(--' +
          (p.healthy ? 'good' : 'attn') + ')">' + (p.healthy ? '●' : '▲') + '</span>' +
          esc(p.plot) + '</figcaption></figure>';
      }).join('') || '<div class="empty">' + icon('i-cam') +
        '<span>They appear after the first AUTO run.</span></div>';
    });
    api('/api/recordings').then(function (r) {
      var rows = (r.recordings || []).filter(function (v) { return v.exists; });
      $('#recList').innerHTML = rows.length ? rows.map(function (v) {
        return '<div class="card"><h2>' + when(v.started) +
          '<span class="spacer"></span><span class="note">' + v.frames +
          ' frames · ' + v.size_mb + ' MB</span></h2><div class="body">' +
          '<video controls preload="none" style="width:100%;border-radius:10px" ' +
          'src="/video/' + esc(v.path) + '"></video>' +
          '<a class="note" href="/video/' + esc(v.path) + '" download>Download this run</a>' +
          '</div></div>';
      }).join('') : '<div class="empty">' + icon('i-runs') +
        '<span>No recordings yet.</span>' +
        '<span class="note">They are made automatically while AUTO is running, ' +
        'if recording is on in Settings.</span></div>';
    });
  }

  /* ============================================================= ALERTS === */
  function loadAlerts() {
    api('/api/alerts').then(function (r) {
      var rows = r.alerts || [];
      $('#alertList').innerHTML = rows.length ? rows.map(function (a, i) {
        var lv = a.level === 'error' ? 'bad' : a.level === 'warn' ? 'attn' : 'good';
        var sym = a.level === 'error' ? '■' : a.level === 'warn' ? '▲' : '●';
        return '<div class="row" style="align-items:flex-start;gap:12px;padding:12px 14px;' +
          'border:1px solid var(--line);border-radius:11px;background:var(--panel-2);' +
          'animation:rise .3s ' + (i * 0.04) + 's both">' +
          '<span style="color:var(--' + lv + ');font-size:13px;line-height:1.5">' +
          sym + '</span>' +
          '<div style="flex:1;min-width:0"><div>' + esc(a.text) + '</div>' +
          '<div class="note">' + when(a.ts) + ' · ' + ago(a.ts) + '</div></div>' +
          (a.seen ? '' : '<span class="badge-soft">new</span>') + '</div>';
      }).join('') : '<div class="empty">' + icon('i-bell') +
        '<span>Nothing flagged yet.</span></div>';
    });
  }
  window.loadAlerts = loadAlerts;

  /* ========================================================== TIMETABLE === */
  function loadPatrols() {
    api('/api/patrols').then(function (r) {
      cache.days = r.day_names || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      var rows = r.patrols || [];
      $('#patrolNext').textContent = r.next
        ? 'Next: ' + (r.next.name || 'patrol') + ', ' + when(r.next.at)
        : 'Nothing scheduled';
      $('#patrolList').innerHTML = rows.length ? rows.map(patrolRow).join('')
        : '<div class="empty">' + icon('i-clock') +
          '<span>No patrols yet. Add one below.</span></div>';
    });
  }
  function patrolRow(p, i) {
    var days = String(p.days || '').split(',').filter(function (x) { return x !== ''; })
      .map(function (d) { return cache.days[+d]; }).join(' ') || 'every day';
    return '<div class="card" style="animation:rise .32s ' + (i * 0.05) + 's both">' +
      '<div class="body" style="gap:10px">' +
      '<div class="row"><b style="font-size:17px">' + esc(p.name || 'patrol') + '</b>' +
      '<span class="tag ' + (p.enabled ? 'ok' : '') + '">' +
      (p.enabled ? 'on' : 'off') + '</span>' +
      (p.spray ? '<span class="tag sprayed">may spray</span>'
        : '<span class="tag">look only</span>') +
      '<span class="spacer"></span>' +
      '<span class="num" style="font-size:21px">' + esc(p.at) + '</span></div>' +
      '<div class="note">' + esc(days) + ' · ' +
      (p.plants ? p.plants + ' plants' : 'the whole row') +
      (p.last_run ? ' · last ran ' + ago(p.last_run) : ' · never run') + '</div>' +
      '<div class="row">' +
      '<button class="sm" onclick="togglePatrol(' + p.id + ',' + (p.enabled ? 0 : 1) + ')">' +
      (p.enabled ? 'Turn off' : 'Turn on') + '</button>' +
      '<button class="sm ghost" onclick="deletePatrol(' + p.id + ')">Delete</button>' +
      '</div></div></div>';
  }
  window.togglePatrol = function (id, on) {
    api('/api/patrols').then(function (r) {
      var p = (r.patrols || []).filter(function (x) { return x.id === id; })[0];
      if (!p) return;
      p.enabled = !!on;
      api('/api/patrols', p).then(loadPatrols);
    });
  };
  window.deletePatrol = function (id) {
    api('/api/patrols', { delete: id }).then(function () {
      loadPatrols(); toast('Patrol deleted');
    });
  };
  window.addPatrol = function () {
    var days = $$('#dayPick input:checked').map(function (i) { return i.value; }).join(',');
    var body = {
      name: $('#pName').value || 'Morning check',
      at: $('#pAt').value || '07:00',
      days: days,
      plants: parseInt($('#pPlants').value || '0', 10) || 0,
      spray: $('#pSpray').checked, enabled: true
    };
    api('/api/patrols', body).then(function () {
      $('#pName').value = ''; loadPatrols(); toast('Patrol added', 'good');
    });
  };

  /* =========================================================== SETTINGS === */
  var LABELS = {
    'drive.max_speed_mps': ['Top speed', 'metres per second at full throttle'],
    'drive.speed_limit': ['Speed limit', 'fraction of top speed the sticks can ask for'],
    'drive.reverse_on_low_batt': ['Come home on low battery', 'reverse back to the start'],
    'boom.target_l_per_ha': ['Spray rate', 'litres per hectare you want on the crop'],
    'boom.max_l_per_ha': ['Never exceed', 'litres per hectare, a hard stop'],
    'boom.max_ml_per_session': ['Most ml in one outing', 'a hard stop'],
    'boom.ml_per_min_per_nozzle': ['Nozzle flow', 'MEASURE IT: one nozzle into a jug for a minute'],
    'boom.tank_litres': ['Tank size', 'litres'],
    'boom.band_seconds': ['Band length over a plant', 'seconds the valves stay open'],
    'boom.pwm_hz': ['Valve pulse rate', 'times a second'],
    'boom.min_duty': ['Warn below this duty', 'under this the band goes stripey'],
    'boom.require_arm_switch': ['Pump must be armed first', 'leave this on'],
    'probe.every_n_plants': ['Probe the soil every', 'plants. 0 turns it off'],
    'probe.settle_s': ['Let the reading settle', 'seconds with the spike in'],
    'probe.timeout_s': ['Call it jammed after', 'seconds without hitting a switch'],
    'ai.min_confidence': ['Ask below this confidence', '0 to 1'],
    'ai.auto_spray_confidence': ['Never spray alone below', '0 to 1'],
    'ai.inspect_seconds': ['Seconds looking at each plant', ''],
    'ai.plant_spacing_mm': ['Gap between plants', 'millimetres'],
    'ai.row_length_m': ['Row length', 'metres, a hard cap on one row'],
    'ai.rows': ['How many rows', 'it turns into the next one at the end'],
    'ai.row_gap_mm': ['Gap between rows', 'millimetres, for the turn'],
    'safety.battery.warn_v': ['Warn at', 'volts'],
    'safety.battery.stop_v': ['Stop at', 'volts, must be below the warning'],
    'safety.return_home_pct': ['Come home at battery %', '0 turns it off'],
    'safety.tilt_stop_deg': ['Stop if leaning more than', 'degrees, needs a tilt sensor'],
    'record.enabled': ['Record every run', 'a frame every couple of seconds'],
    'record.every_seconds': ['Seconds between frames', ''],
    'record.keep_days': ['Keep recordings for', 'days'],
    'notify.on_problem': ['Tell me about problems', ''],
    'notify.on_finish': ['Tell me when a run ends', ''],
    'notify.on_low_battery': ['Tell me about low battery', ''],
    'notify.on_estop': ['Tell me about emergency stops', ''],
    'notify.telegram_token': ['Telegram bot token', 'from @BotFather'],
    'notify.telegram_chat_id': ['Telegram chat id', 'the number the bot sees']
  };
  var GROUPS = [
    ['Driving and steering', 'drive.', 'i-wheel'],
    ['The spray boom', 'boom.', 'i-spray'],
    ['The soil probe', 'probe.', 'i-drop'],
    ['Deciding', 'ai.', 'i-plant'],
    ['Looking after itself', 'safety.', 'i-warn'],
    ['Recording', 'record.', 'i-cam'],
    ['Telling you', 'notify.', 'i-msg']
  ];

  function loadSettings() {
    api('/api/settings').then(function (r) {
      cache.settings = r.settings;
      $('#accName').value = (r.user && r.user.name) || '';
      $('#fitted').innerHTML = [
        ['Wheel encoders', r.fitted.encoders, r.why.encoders,
          'without them the distance is estimated and drifts'],
        ['Tilt sensor', r.fitted.imu, r.why.imu,
          'without it the leaning cut-out can never fire'],
        ['Front range sensor', r.fitted.range, r.why.range,
          'without it nothing stops it driving into something'],
        ['Soil probe', r.fitted.probe, r.why.probe,
          'without it there is no soil reading at all'],
        ['Boom valves', r.fitted.boom, r.why.boom,
          'without them nothing can be sprayed'],
        ['Drive and steering', r.fitted.drive, r.why.drive,
          'without them it cannot move'],
        ['Plant AI model', S.ai_ready === true, r.why.ai,
          'without it every plant is logged as not checked'],
        ['Front camera measured', r.fitted.camera_measured, r.why.camera_measured,
          'without it the arm cannot aim at what the camera sees']
      ].map(function (f) {
        return '<div class="kv"><span>' + esc(f[0]) + '<div class="note">' +
          esc(f[1] ? 'working' : f[3]) + '</div></span>' +
          '<span class="tag ' + (f[1] ? 'ok' : '') + '">' +
          (f[1] ? 'fitted' : 'not fitted') + '</span></div>';
      }).join('') + (r.steering ? '<div class="kv"><span>Turning circle' +
        '<div class="note">worked out from the steering linkage in the CAD</div></span>' +
        '<span>' + n(r.steering.turning_circle_mm / 1000, 2) + ' m</span></div>' : '');

      $('#setForm').innerHTML = GROUPS.map(function (grp) {
        var keys = Object.keys(r.settings).filter(function (k) {
          return k.indexOf(grp[1]) === 0;
        });
        if (!keys.length) return '';
        return '<div class="card"><h2>' + icon(grp[2]) + esc(grp[0]) +
          '</h2><div class="body">' +
          '<div class="formgrid">' + keys.map(function (k) {
            return field(k, r.settings[k]);
          }).join('') + '</div></div></div>';
      }).join('');
    });
  }
  function field(key, s) {
    var lab = LABELS[key] || [key, ''];
    var id = 'set_' + key.replace(/\./g, '_');
    if (s.type === 'bool') {
      return '<label class="switch" for="' + id + '"><input type="checkbox" id="' + id +
        '" data-key="' + key + '"' + (s.value ? ' checked' : '') + '>' +
        '<span>' + esc(lab[0]) + (lab[1] ? '<div class="hint">' + esc(lab[1]) +
          '</div>' : '') + '</span></label>';
    }
    var limits = (s.min !== null && s.min !== undefined)
      ? ' (' + s.min + ' to ' + s.max + ')' : '';
    var type = s.type === 'str' ? 'text' : 'number';
    var step = s.type === 'int' ? '1' : '0.01';
    return '<label for="' + id + '">' + esc(lab[0]) +
      '<input type="' + type + '" id="' + id + '" data-key="' + key +
      '" value="' + esc(s.value) + '"' +
      (type === 'number' ? ' step="' + step + '" min="' + s.min + '" max="' + s.max + '"' : '') +
      '><span class="hint">' + esc(lab[1]) + esc(limits) + '</span></label>';
  }
  window.saveSettings = function () {
    var changes = {};
    $$('#setForm [data-key]').forEach(function (el) {
      changes[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
    });
    api('/api/settings', { changes: changes }).then(function (r) {
      var bad = Object.keys(r.refused || {});
      if (bad.length) toast(bad[0] + ': ' + r.refused[bad[0]], 'bad');
      else toast('Saved. It is using the new settings now.', 'good');
      loadSettings();
    });
  };
  window.testNotify = function () {
    api('/api/notify/test').then(function (r) {
      toast(r.message || 'sent', r.ok ? 'good' : 'bad');
    });
  };
  window.changeAccount = function () {
    var body = { old: $('#accOld').value, new: $('#accNew').value,
      username: $('#accName').value };
    api('/api/account', body).then(function (r) {
      if (!r.ok) return toast(r.error || 'could not change it', 'bad');
      toast('Changed. Signing you out.', 'good');
      setTimeout(function () { location.href = '/login'; }, 1200);
    });
  };
  window.signOut = function () {
    api('/api/logout', {}).then(function () { location.href = '/login'; });
  };
  window.testSpray = function (sections) {
    api('/api/command', { cmd: 'spray_now', args: { sections: sections, seconds: 1.5 } })
      .then(function (r) { toast(r.message || (r.ok ? 'done' : 'could not'),
        r.ok ? 'good' : 'bad'); });
  };
  window.enableNotifications = function () {
    Notification.requestPermission().then(function () { $('#askNotify').hidden = true; });
  };

  /* ========================================================== the joypad == */
  var padVec = { x: 0, y: 0 };
  // Driving goes down the websocket when it is open - one small message
  // instead of a whole HTTP request, ten times a second - and falls back to
  // a normal command when it is not.
  function driveSend(t, s) {
    if (ws && wsOK && ws.readyState === 1) {
      try { ws.send(JSON.stringify({ cmd: 'drive', throttle: t, steer: s })); return; }
      catch (e) {}
    }
    api('/api/command', { cmd: 'drive', args: { throttle: t, steer: s } }).catch(function () {});
  }
  function sendDrive() { driveSend(padVec.y, padVec.x); }

  function joypad() {
    var pad = $('#pad'), knob = $('#knob'), on = false, timer = null;
    function at(ev) {
      var r = pad.getBoundingClientRect();
      var p = ev.touches ? ev.touches[0] : ev;
      return { x: (p.clientX - r.left) / r.width * 2 - 1,
        y: -((p.clientY - r.top) / r.height * 2 - 1) };
    }
    function move(ev) {
      if (!on) return;
      var v = at(ev);
      v.x = Math.max(-1, Math.min(1, v.x)); v.y = Math.max(-1, Math.min(1, v.y));
      padVec = v;
      paint();
      if (ev.cancelable) ev.preventDefault();
    }
    function start(ev) {
      if (S.rc_live) { toast('The remote is on, so it is driving', 'bad'); return; }
      on = true; pad.classList.add('grabbed'); move(ev);
      timer = setInterval(sendDrive, 130);
    }
    function end() {
      if (!on) return;
      on = false; pad.classList.remove('grabbed');
      clearInterval(timer);
      padVec = { x: 0, y: 0 }; paint(); sendDrive();
    }
    pad.addEventListener('mousedown', start);
    pad.addEventListener('touchstart', start, { passive: false });
    document.addEventListener('mousemove', move);
    pad.addEventListener('touchmove', move, { passive: false });
    document.addEventListener('mouseup', end);
    pad.addEventListener('touchend', end);
  }
  function paint() {
    $('#knob').style.left = (50 + padVec.x * 42) + '%';
    $('#knob').style.top = (50 - padVec.y * 42) + '%';
    $('#padVal').textContent = 'throttle ' + Math.round(padVec.y * 100) +
      '% · steer ' + Math.round(padVec.x * 100) + '%';
  }

  /* Keyboard driving. W A S D or the arrows, held down; release and it stops.
     The same interlock as the pad: the remote always wins. */
  var keysDown = {}, keyTimer = null;
  var DRIVE_KEYS = { w: 'up', s: 'down', a: 'left', d: 'right',
    arrowup: 'up', arrowdown: 'down', arrowleft: 'left', arrowright: 'right' };
  function keyDrive() {
    padVec = {
      x: (keysDown.left ? -1 : 0) + (keysDown.right ? 1 : 0),
      y: (keysDown.up ? 1 : 0) + (keysDown.down ? -1 : 0)
    };
    paint();
    if (!padVec.x && !padVec.y) { clearInterval(keyTimer); keyTimer = null; sendDrive(); }
    else if (!keyTimer) keyTimer = setInterval(sendDrive, 130);
  }

  /* ========================================================= the REMOTE == */
  /* The whole machine from a phone: the camera and where it is looking, a
     thumb stick, and every joint of the arm. Everything here is a thin skin
     over commands the rover already checks - the stick only drives in
     Manual with the remote off, and the arm refuses in Auto or in a stop -
     so the page cannot talk the rover into anything unsafe. */
  var rm = { vec: { x: 0, y: 0 }, held: false, timer: null, joints: '', drag: {},
    sweep: [], relaxArm: 0 };
  var POSE_NAMES = { park: 'Fold away', ready: 'Ready', reach: 'Reach down' };

  function joint(name) {
    var js = (S.servos && S.servos.joints) || [];
    for (var i = 0; i < js.length; i++) if (js[i].name === name) return js[i];
    return null;
  }
  function servoCmd(name, args) {
    args.name = name;
    return cmd('servo', args);
  }
  function remoteGate() {
    // why the stick will not drive right now, or '' when it will
    if (S.estop) return 'stop';
    if (S.rc_live) return 'rc';
    if (S.mode !== 'MANUAL') return 'mode';
    return '';
  }

  function remoteStick() {
    var pad = $('#rmStick'), id = null;
    if (!pad) return;
    function at(ev) {
      var r = pad.getBoundingClientRect();
      var x = (ev.clientX - r.left) / r.width * 2 - 1;
      var y = -((ev.clientY - r.top) / r.height * 2 - 1);
      var m = Math.sqrt(x * x + y * y);
      if (m > 1) { x /= m; y /= m; }           // keep the knob inside the ring
      // a small dead zone, so a resting thumb does not creep the rover
      if (Math.abs(x) < 0.08) x = 0;
      if (Math.abs(y) < 0.08) y = 0;
      return { x: x, y: y };
    }
    pad.addEventListener('pointerdown', function (ev) {
      if (remoteGate()) { drawRemote(); return; }
      if (id !== null) return;
      id = ev.pointerId;
      try { pad.setPointerCapture(id); } catch (e) {}
      rm.held = true; pad.classList.add('grabbed');
      if (navigator.vibrate) navigator.vibrate(12);
      rm.vec = at(ev); paintStick();
      driveSend(rm.vec.y, rm.vec.x);
      clearInterval(rm.timer);
      rm.timer = setInterval(function () {
        if (remoteGate()) return release();
        driveSend(rm.vec.y, rm.vec.x);
      }, 110);
      ev.preventDefault();
    });
    pad.addEventListener('pointermove', function (ev) {
      if (ev.pointerId !== id) return;
      rm.vec = at(ev); paintStick();
      ev.preventDefault();
    });
    function release(ev) {
      if (ev && ev.pointerId !== id) return;
      id = null;
      rm.held = false; pad.classList.remove('grabbed');
      clearInterval(rm.timer); rm.timer = null;
      rm.vec = { x: 0, y: 0 }; paintStick();
      // twice: a stop that gets lost on a bad wifi is the one that matters
      driveSend(0, 0);
      setTimeout(function () { if (!rm.held) driveSend(0, 0); }, 150);
    }
    rm.release = release;
    pad.addEventListener('pointerup', release);
    pad.addEventListener('pointercancel', release);
    pad.addEventListener('lostpointercapture', release);
    window.addEventListener('blur', function () { if (rm.held) release(); });
  }
  function paintStick() {
    var k = $('#rmKnob');
    if (!k) return;
    k.style.left = (50 + rm.vec.x * 40) + '%';
    k.style.top = (50 - rm.vec.y * 40) + '%';
    var t = Math.round(rm.vec.y * 100), s = Math.round(rm.vec.x * 100);
    $('#rmThr').textContent = t === 0 ? 'stopped' : (t > 0 ? 'forward ' + t + '%' : 'back ' + (-t) + '%');
    $('#rmStr').textContent = s === 0 ? 'straight' : (s > 0 ? 'right ' + s + '%' : 'left ' + (-s) + '%');
  }

  /* ---------- the camera's pan servo: offsets from straight ahead */
  window.lookAt = function (offset) {
    rm.sweep.forEach(clearTimeout); rm.sweep = [];
    $('#rmSweep').classList.remove('sel');
    var j = joint('pan');
    if (!j) return;
    servoCmd('pan', { deg: j.park + offset });
  };
  window.lookStep = function (delta) {
    rm.sweep.forEach(clearTimeout); rm.sweep = [];
    $('#rmSweep').classList.remove('sel');
    if (joint('pan')) servoCmd('pan', { delta: delta });
  };
  window.lookAround = function () {
    var j = joint('pan');
    if (!j) return;
    rm.sweep.forEach(clearTimeout); rm.sweep = [];
    // left, right, then back to straight ahead - each leg waits long enough
    // for the servo to get there at its own speed
    var legs = [j.min, j.max, j.park], at = j.deg, wait = 0;
    var speed = 90;                                // matches config speed_deg_s
    $('#rmSweep').classList.add('sel');
    legs.forEach(function (to, i) {
      rm.sweep.push(setTimeout(function () {
        servoCmd('pan', { deg: to });
        if (i === legs.length - 1) $('#rmSweep').classList.remove('sel');
      }, wait));
      wait += Math.abs(to - at) / speed * 1000 + 900;   // + a moment to look
      at = to;
    });
  };
  window.takeControl = function () { pickMode('MANUAL'); };

  /* ---------- who drives: you (Manual), the rover itself (AI), or nobody (Hold)
     AI mode follows the crop row with the camera and stops at each plant.
     Without a distance sensor at the front it cannot see a person or a wall,
     so it asks once before it starts, and the rover itself keeps it slow. */
  window.pickMode = function (mode, sure) {
    var ask = $('#rmAiAsk');
    if (mode === 'AUTO' && S.mode !== 'AUTO' && !sure) {
      var f = S.fitted || {};
      if (!S.sim && f.camera === false) {
        toast('AI mode needs the camera, and it is not working. Check its cable.', 'bad');
        return;
      }
      if (!S.sim && !f.range) {
        $('#rmAiAskText').textContent = 'There is no distance sensor at the front, so it ' +
          'cannot see a wall, an animal or a person in its way. It will keep to ' +
          Math.round((S.auto_blind_cap || 0.3) * 100) + '% speed. Stay beside it with STOP in reach.';
        ask.hidden = false;
        return;
      }
    }
    ask.hidden = true;
    if (mode === S.mode) return;
    cmd('mode', { mode: mode });
  };

  /* ---------- on a phone, Drive and Arm take turns under the picture */
  window.rmTab = function (t) {
    if (t !== 'arm') t = 'drive';
    if (rm.held && rm.release) rm.release();          // never leave it driving
    var box = $('.rm');
    if (box) box.setAttribute('data-tab', t);
    $('#rmTabDrive').setAttribute('aria-selected', t === 'drive' ? 'true' : 'false');
    $('#rmTabArm').setAttribute('aria-selected', t === 'arm' ? 'true' : 'false');
    store('rmtab', t);
  };

  /* ---------- the arm. The same controls sit on the Remote page and on the
     Arm page, so everything below works on every copy at once. */
  function buildJoints() {
    var js = ((S.servos && S.servos.joints) || []).filter(function (j) { return j.group !== 'camera'; });
    var sig = js.map(function (j) { return j.name + j.min + j.max; }).join('|');
    if (sig === rm.joints) return;
    rm.joints = sig;
    $$('.armJoints').forEach(function (box) {
      box.innerHTML = js.length ? js.map(function (j) {
        return '<div class="rm-joint" data-j="' + esc(j.name) + '">' +
          '<div class="rm-jhead"><b>' + esc(j.label) + '</b>' +
            '<span class="num"><span data-v>' + Math.round(j.deg) + '</span>&deg;' +
            '<i class="rm-moving" data-m hidden>moving</i></span></div>' +
          '<div class="rm-jctl">' +
            '<button class="rm-step" data-d="-1" aria-label="' + esc(j.label) + ' less">&minus;</button>' +
            '<div class="rm-slide"><input type="range" min="' + j.min + '" max="' + j.max +
              '" step="1" value="' + Math.round(j.target) + '" aria-label="' + esc(j.label) + '">' +
              '<i class="rm-at" data-at></i></div>' +
            '<button class="rm-step" data-d="1" aria-label="' + esc(j.label) + ' more">+</button>' +
          '</div></div>';
      }).join('') : '<div class="empty" style="padding:14px">No arm joints in config.yaml.</div>';
    });

    $$('.armJoints .rm-joint').forEach(function (row) {
      var name = row.dataset.j, input = $('input', row), last = 0, pend = null;
      function send(final) {
        var now = Date.now();
        clearTimeout(pend);
        if (final || now - last > 140) {
          last = now;
          servoCmd(name, { deg: parseFloat(input.value) });
        } else {
          pend = setTimeout(function () { send(true); }, 140);
        }
      }
      input.addEventListener('pointerdown', function () { rm.drag[name] = true; });
      input.addEventListener('input', function () { rm.drag[name] = true; send(false); });
      input.addEventListener('change', function () { send(true); rm.drag[name] = false; });
      input.addEventListener('pointerup', function () { setTimeout(function () { rm.drag[name] = false; }, 400); });
      // hold a step button and the joint keeps going, a little at a time
      $$('.rm-step', row).forEach(function (b) {
        var rep = null;
        function stop() { clearInterval(rep); rep = null; }
        b.addEventListener('pointerdown', function (ev) {
          ev.preventDefault();
          var d = parseFloat(b.dataset.d) * 4;
          servoCmd(name, { delta: d });
          clearInterval(rep);
          rep = setInterval(function () { servoCmd(name, { delta: d }); }, 160);
        });
        ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (e) { b.addEventListener(e, stop); });
      });
    });
  }
  window.armPose = function (p) { cmd('servo_pose', { pose: p }); };
  window.armGrip = function (open) {
    var g = joint('grip');
    if (!g) return;
    var to = open ? (g.open != null ? g.open : g.max) : (g.closed != null ? g.closed : g.min);
    servoCmd('grip', { deg: to });
  };
  function relaxLabel(armed) {
    $$('.armRelax').forEach(function (b) {
      b.textContent = armed ? 'Tap again - it will drop' : 'Relax (go limp)';
      b.classList.toggle('stop', armed);
    });
  }
  window.armRelax = function () {
    // two taps: going limp drops whatever the arm is holding up
    if (Date.now() - rm.relaxArm > 3000) {
      rm.relaxArm = Date.now();
      relaxLabel(true);
      setTimeout(function () { if (Date.now() - rm.relaxArm >= 2900) relaxLabel(false); }, 3000);
      return;
    }
    rm.relaxArm = 0;
    relaxLabel(false);
    cmd('servo_relax', {});
  };
  window.armSavePose = function () {
    var inp = $('#armPoseName'), name = (inp.value || '').trim();
    if (!name) { inp.focus(); toast('Type a name for this pose first', 'bad'); return; }
    cmd('servo_pose_save', { name: name }).then(function (r) {
      if (r && r.ok) inp.value = '';
    });
  };
  window.armForget = function (btn) {
    // two taps as well: a pose you taught it by hand is work to redo
    var name = btn.getAttribute('data-p');
    if (btn.dataset.armed !== '1') {
      btn.dataset.armed = '1';
      btn.textContent = 'delete?';
      btn.classList.add('stop');
      setTimeout(function () {
        if (btn.isConnected) { btn.dataset.armed = ''; btn.innerHTML = '&times;'; btn.classList.remove('stop'); }
      }, 3000);
      return;
    }
    cmd('servo_pose_delete', { name: name });
  };
  function poseLabel(p) {
    return POSE_NAMES[p] || (p.charAt(0).toUpperCase() + p.slice(1));
  }

  function drawArm() {
    var sv = S.servos || {};
    buildJoints();
    var locked = S.mode === 'AUTO' || !!S.estop;
    var arm = (sv.joints || []).filter(function (j) { return j.group !== 'camera'; });
    var awake = arm.some(function (j) { return j.awake; });
    $$('.armState').forEach(function (e) {
      e.textContent = locked ? 'locked' : !sv.live ? 'simulated' : awake ? 'live' : 'live, resting';
      e.title = sv.reason || '';
      e.classList.toggle('ok', !!sv.live && !locked);
    });
    var note = S.estop ? 'Emergency stop: the arm is holding still. Clear the stop to move it.'
      : S.mode === 'AUTO' ? 'The arm is locked while the rover drives itself (AI mode). Switch to Manual to use it.'
      : !sv.live ? (sv.driver === 'gpio'
          ? 'The servo pins did not start, so these move on screen only.'
          : 'No PCA9685 servo board answered, so these move on screen only.') +
        (sv.reason && sv.reason !== 'simulation' ? ' (' + sv.reason + ')' : '')
      : !awake ? 'The joints have no power until you first move one - then each wakes at its fold-away angle.'
      : 'Each joint walks to where you send it, slowly. Hold + or − to keep it going.';
    $$('.armNote').forEach(function (e) { e.textContent = note; });

    arm.forEach(function (j) {
      $$('.rm-joint[data-j="' + j.name + '"]').forEach(function (row) {
        $('[data-v]', row).textContent = Math.round(j.deg);
        $('[data-m]', row).hidden = !j.moving;
        var input = $('input', row);
        if (!rm.drag[j.name]) input.value = Math.round(j.target);
        var pct = (j.deg - j.min) / Math.max(1, j.max - j.min) * 100;
        $('[data-at]', row).style.left = pct + '%';
        row.classList.toggle('asleep', !j.awake);
        input.disabled = locked;
        $$('.rm-step', row).forEach(function (b) { b.disabled = locked; });
      });
    });
    var hasGrip = !!joint('grip');
    $$('.armGrip').forEach(function (e) { e.hidden = !hasGrip; });

    // the poses: the ones in config.yaml, then the ones you taught it
    var poses = sv.poses || [], saved = sv.saved_poses || [];
    var psig = poses.join('|') + '#' + saved.join('|');
    $$('.armPoses').forEach(function (box) {
      if (box.dataset.sig !== psig) {
        box.dataset.sig = psig;
        var canForget = !!box.closest('#p-arm');
        box.innerHTML = poses.map(function (p) {
          var mine = saved.indexOf(p) !== -1;
          var btn = '<button class="sm' + (mine ? ' mine' : '') + '" data-pose="' + esc(p) + '">' +
            esc(poseLabel(p)) + '</button>';
          if (!mine || !canForget) return btn;
          return '<span class="posepair">' + btn +
            '<button class="sm ghost forget" data-p="' + esc(p) + '" aria-label="Delete ' + esc(p) +
            '" onclick="armForget(this)">&times;</button></span>';
        }).join('');
        $$('button[data-pose]', box).forEach(function (b) {
          b.addEventListener('click', function () { armPose(b.getAttribute('data-pose')); });
        });
      }
      $$('button', box).forEach(function (b) { if (!b.classList.contains('forget')) b.disabled = locked; });
    });
    $$('.armGrip button').forEach(function (b) { b.disabled = locked; });
    $$('.armsave button, .armsave input').forEach(function (b) { b.disabled = locked || !awake; });
    if (page === 'arm') drawArmPicture(arm);
  }

  /* A side view drawn from the joint angles, so it is plain which slider
     moves which part. Shoulder 90 is straight up; elbow 180 is straight on;
     wrist 90 is in line with the forearm. The lengths are a sketch. */
  function armPoints(get) {
    var P = { x: 130, y: 222 }, pts = [P], a = 0, R = Math.PI / 180;
    var sh = get('shoulder'), el = get('elbow'), wr = get('wrist');
    var legs = [];
    if (sh != null) { a = sh; legs.push([100, a]); }
    if (sh != null && el != null) { a = a - (180 - el); legs.push([88, a]); }
    if (sh != null && el != null && wr != null) { a = a + (wr - 90); legs.push([40, a]); }
    legs.forEach(function (l) {
      P = { x: P.x + l[0] * Math.cos(l[1] * R), y: P.y - l[0] * Math.sin(l[1] * R) };
      pts.push(P);
    });
    return { pts: pts, tipDeg: a };
  }
  function jaws(tip, dir, open) {
    var R = Math.PI / 180, spread = 7 + 24 * open, L = 15, s = '';
    [-1, 1].forEach(function (k) {
      var d = (dir + k * spread) * R;
      s += '<line class="ad-jaw" x1="' + tip.x.toFixed(1) + '" y1="' + tip.y.toFixed(1) +
        '" x2="' + (tip.x + L * Math.cos(d)).toFixed(1) + '" y2="' + (tip.y - L * Math.sin(d)).toFixed(1) + '"/>';
    });
    return s;
  }
  function gripOpen(g, v) {
    if (!g) return 0.5;
    var lo = g.closed != null ? g.closed : g.min, hi = g.open != null ? g.open : g.max;
    return Math.max(0, Math.min(1, (v - lo) / ((hi - lo) || 1)));
  }
  function drawArmPicture(arm) {
    var svg = $('#armDraw');
    if (!svg) return;
    var by = {};
    arm.forEach(function (j) { by[j.name] = j; });
    function now(k) { return by[k] ? by[k].deg : null; }
    function goal(k) { return by[k] ? by[k].target : null; }
    var A = armPoints(now), G = armPoints(goal), g = by.grip;
    function path(pts) {
      return pts.map(function (p, i) { return (i ? 'L' : 'M') + p.x.toFixed(1) + ' ' + p.y.toFixed(1); }).join(' ');
    }
    var moving = arm.some(function (j) { return j.moving; });
    var ghost = moving ? '<path d="' + path(G.pts) + '"/>' +
      (G.pts.length > 1 ? jaws(G.pts[G.pts.length - 1], G.tipDeg, gripOpen(g, g ? g.target : 0)) : '') : '';
    $('#adGhost').innerHTML = ghost;
    var names = ['shoulder', 'elbow', 'wrist'], h = '<path class="ad-link" d="' + path(A.pts) + '"/>';
    A.pts.forEach(function (p, i) {
      var nm = names[i];
      h += '<circle class="ad-joint' + (nm && by[nm] && !by[nm].awake ? ' asleep' : '') +
        '" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + (i ? 5 : 7) + '"/>';
      if (nm && by[nm] && i < A.pts.length - 1)
        h += '<text class="ad-t lbl" x="' + (p.x + 9).toFixed(1) + '" y="' + (p.y - 9).toFixed(1) + '">' +
          nm + ' ' + Math.round(by[nm].deg) + '°</text>';
    });
    if (A.pts.length > 1) {
      var tip = A.pts[A.pts.length - 1];
      h += jaws(tip, A.tipDeg, gripOpen(g, g ? g.deg : 0));
      if (g) h += '<text class="ad-t lbl" x="' + (tip.x + 12).toFixed(1) + '" y="' + (tip.y + 20).toFixed(1) +
        '">grip ' + Math.round(gripOpen(g, g.deg) * 100) + '% open</text>';
      if (tip.y > 248) h += '<text class="ad-t warn" x="200" y="274" text-anchor="middle">' +
        'the gripper may be touching the ground</text>';
    }
    $('#adArm').innerHTML = h;
    svg.classList.toggle('asleep', !arm.some(function (j) { return j.awake; }));
    var base = by.base;
    $('#adBase').setAttribute('transform', 'rotate(' + (base ? (base.deg - (base.park || 90)) : 0).toFixed(1) + ')');
  }

  function drawRemote() {
    if (!$('#p-remote') || !S.mode) return;
    var gate = remoteGate();

    // who is driving: the three buttons, and in AI mode what it is doing
    $$('.rm-modes button').forEach(function (b) {
      var on = b.dataset.mode === S.mode;
      b.classList.toggle('sel', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.disabled = !!S.estop;
    });
    if (S.mode === 'AUTO') $('#rmAiAsk').hidden = true;
    var ai = $('#rmAi');
    ai.hidden = S.mode !== 'AUTO';
    if (S.mode === 'AUTO') {
      var m = S.mission || {}, f = S.fitted || {};
      $('#rmMode').lastChild.textContent = 'AI is driving';
      $('#rmAiCount').textContent = (m.plants_done || 0) +
        (m.plants_target ? ' of ' + m.plants_target : '') + ' plants';
      $('#rmAiStep').textContent = (m.step ? m.step + ' - ' : '') + (m.message || 'following the row') +
        (!f.range && !S.sim ? '  ·  no distance sensor, held to ' +
          Math.round((S.auto_blind_cap || 0.3) * 100) + '% speed' : '');
    }

    var g = $('#rmGate');
    g.hidden = !gate || rm.held;
    if (gate === 'stop') {
      $('#rmGateText').textContent = 'The emergency stop is on.';
      $('#rmTake').textContent = 'Clear the stop';
      $('#rmTake').onclick = function () { cmd('clear_estop'); };
    } else if (gate === 'rc') {
      $('#rmGateText').textContent = 'The hand remote is on, so it drives. Switch it off to use the phone.';
      $('#rmTake').hidden = true;
    } else if (gate === 'mode') {
      $('#rmGateText').textContent = S.mode === 'AUTO'
        ? 'AI mode: it is driving itself. Take control stops the row and gives you the stick.'
        : S.mode === 'HOLD' ? 'Hold: the wheels are locked still. Switch to Manual to drive.'
        : 'The stick drives only in Manual.';
      $('#rmTake').textContent = S.mode === 'AUTO' ? 'Take control' : 'Switch to Manual';
      $('#rmTake').onclick = takeControl;
    }
    if (gate !== 'rc') $('#rmTake').hidden = false;
    $('#rmStick').classList.toggle('locked', !!gate);

    var skid = (S.drive_hw || {}).layout === 'skid';
    $('#rmHow').textContent = skid
      ? 'Let go and it stops. Push sideways to turn - sideways on its own spins it on the spot, like a tank.'
      : 'Let go and it stops. It steers like a car, so it cannot turn on the spot.';
    var sp = $('#rmSpeed');
    if (sp && !rm.drag.speed && S.speed_limit) {
      sp.value = S.speed_limit;
      $('#rmSpeedTxt').textContent = Math.round(S.speed_limit * 100) + '%';
    }

    // camera
    var pan = joint('pan');
    $('#rmLookWrap').hidden = !pan;
    if (pan) {
      var off = Math.round(pan.deg - pan.park), camLocked = S.mode === 'AUTO' || !!S.estop;
      $('#rmNeedle').style.transform = 'rotate(' + Math.max(-90, Math.min(90, off)) + 'deg)';
      $('#rmLookTxt').textContent = Math.abs(off) < 3 ? 'ahead' :
        (off < 0 ? 'left ' : 'right ') + Math.abs(off) + '°';
      $('#rmAhead').hidden = Math.abs(pan.target - pan.park) < 2 || camLocked;
      $$('#rmLookWrap button').forEach(function (b) { b.disabled = camLocked; });
      $('.rm-pan.l').classList.toggle('end', pan.target <= pan.min + 0.5);
      $('.rm-pan.r').classList.toggle('end', pan.target >= pan.max - 0.5);
    }
    drawArm();
  }

  function remoteBoot() {
    if (!$('#p-remote')) return;
    remoteStick();
    var sp = $('#rmSpeed');
    sp.addEventListener('pointerdown', function () { rm.drag.speed = true; });
    sp.addEventListener('input', function () {
      rm.drag.speed = true;
      $('#rmSpeedTxt').textContent = Math.round(this.value * 100) + '%';
    });
    sp.addEventListener('change', function () {
      cmd('speed_limit', { value: parseFloat(this.value) });
      setTimeout(function () { rm.drag.speed = false; }, 600);
    });
  }

  /* ==================================================== the command palette */
  var PAL = [
    { t: 'Live', s: 'page', go: 'live', ic: 'i-live' },
    { t: 'Remote - drive, arm and camera from your phone', s: 'page', go: 'remote', ic: 'i-joy' },
    { t: 'Robotic arm - move each joint, save poses', s: 'page', go: 'arm', ic: 'i-arm' },
    { t: 'AI mode - let it drive itself along the row', s: 'command', run: function () { go('remote'); pickMode('AUTO'); }, ic: 'i-joy' },
    { t: 'Manual mode - you drive', s: 'command', run: function () { pickMode('MANUAL'); }, ic: 'i-joy' },
    { t: 'Field map', s: 'page', go: 'field', ic: 'i-map' },
    { t: 'Plants', s: 'page', go: 'plants', ic: 'i-plant' },
    { t: 'Charts', s: 'page', go: 'charts', ic: 'i-chart' },
    { t: 'Runs and photos', s: 'page', go: 'runs', ic: 'i-runs' },
    { t: 'Alerts', s: 'page', go: 'alerts', ic: 'i-bell' },
    { t: 'Timetable', s: 'page', go: 'timetable', ic: 'i-clock' },
    { t: 'Settings', s: 'page', go: 'settings', ic: 'i-cog' },
    { t: 'EMERGENCY STOP', s: 'command', run: function () { cmd('estop'); }, ic: 'i-warn' },
    { t: 'Clear the emergency stop', s: 'command', run: function () { cmd('clear_estop'); }, ic: 'i-check' },
    { t: 'Start the row', s: 'command', run: function () { cmd('mission_start', { plants: 0 }); }, ic: 'i-runs' },
    { t: 'Stop the row', s: 'command', run: function () { cmd('mission_stop'); }, ic: 'i-x' },
    { t: 'Go to Idle', s: 'mode', run: function () { cmd('mode', { mode: 'IDLE' }); }, ic: 'i-wheel' },
    { t: 'Go to Manual', s: 'mode', run: function () { cmd('mode', { mode: 'MANUAL' }); }, ic: 'i-wheel' },
    { t: 'Go to Auto', s: 'mode', run: function () { cmd('mode', { mode: 'AUTO' }); }, ic: 'i-wheel' },
    { t: 'Go to Hold', s: 'mode', run: function () { cmd('mode', { mode: 'HOLD' }); }, ic: 'i-wheel' },
    { t: 'Arm the pump', s: 'spray', run: function () { cmd('spray_arm', { on: true }); }, ic: 'i-spray' },
    { t: 'Disarm the pump', s: 'spray', run: function () { cmd('spray_arm', { on: false }); }, ic: 'i-spray' },
    { t: 'Read the soil now', s: 'command', run: function () { cmd('probe_soil'); }, ic: 'i-drop' },
    { t: 'Come home', s: 'command', run: function () { cmd('go_home'); }, ic: 'i-home' },
    { t: 'Mark home here', s: 'command', run: function () { cmd('mark_home'); }, ic: 'i-home' },
    { t: 'Start recording', s: 'command', run: function () { cmd('record', { on: true }); }, ic: 'i-cam' },
    { t: 'Stop recording', s: 'command', run: function () { cmd('record', { on: false }); }, ic: 'i-cam' },
    { t: 'Switch light / dark', s: 'view', run: function () { window.toggleTheme(); }, ic: 'i-sun' },
    { t: 'Download the log as CSV', s: 'file', run: function () { location.href = '/api/report.csv'; }, ic: 'i-down' },
    { t: 'Download the photo set', s: 'file', run: function () { location.href = '/api/photoset.zip'; }, ic: 'i-down' },
    { t: 'Sign out', s: 'account', run: function () { window.signOut(); }, ic: 'i-out' }
  ];
  var palSel = 0, palRows = [];

  window.openPalette = function () {
    $('#palette').classList.add('on');
    $('#palInput').value = '';
    palFill('');
    setTimeout(function () { $('#palInput').focus(); }, 30);
  };
  window.closePalette = function () { $('#palette').classList.remove('on'); };

  function palFill(q) {
    q = (q || '').toLowerCase();
    palRows = PAL.filter(function (r) {
      return !q || (r.t + ' ' + r.s).toLowerCase().indexOf(q) >= 0;
    }).slice(0, 12);
    palSel = 0;
    $('#palHits').innerHTML = palRows.length ? palRows.map(function (r, i) {
      return '<div class="hit" data-i="' + i + '" aria-selected="' +
        (i === 0) + '">' + icon(r.ic, 'ic') + '<span>' + esc(r.t) +
        '</span><small>' + esc(r.s) + '</small></div>';
    }).join('') : '<div class="empty" style="padding:22px">Nothing matches that.</div>';
    $$('#palHits .hit').forEach(function (el) {
      el.onclick = function () { palRun(+el.dataset.i); };
      el.onmouseenter = function () { palMove(+el.dataset.i); };
    });
  }
  function palMove(i) {
    palSel = Math.max(0, Math.min(palRows.length - 1, i));
    $$('#palHits .hit').forEach(function (el, k) {
      el.setAttribute('aria-selected', k === palSel);
      if (k === palSel) el.scrollIntoView({ block: 'nearest' });
    });
  }
  function palRun(i) {
    var r = palRows[i];
    if (!r) return;
    window.closePalette();
    if (r.go) go(r.go); else if (r.run) r.run();
  }

  /* ================================================================ boot == */
  function boot() {
    applyTheme(store('theme') === 'light' ? 'light' : 'dark');

    $$('.navbtn').forEach(function (b) {
      b.onclick = function () { go(b.dataset.page); };
    });

    $('#speed').oninput = function () {
      $('#speedTxt').textContent = Math.round(this.value * 100) + '%';
    };
    $('#speed').onchange = function () {
      cmd('speed_limit', { value: parseFloat(this.value) });
    };
    remoteBoot();
    rmTab(store('rmtab') || 'drive');

    $('#dayPick').innerHTML = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
      .map(function (d, i) {
        return '<label class="switch" style="padding:7px 10px"><input type="checkbox" ' +
          'value="' + i + '" checked><span>' + d + '</span></label>';
      }).join('');

    // press feedback on every button, positioned where the pointer landed
    document.addEventListener('pointerdown', function (ev) {
      var b = ev.target.closest && ev.target.closest('button, .btn');
      if (!b) return;
      var r = b.getBoundingClientRect();
      b.style.setProperty('--rx', (ev.clientX - r.left) + 'px');
      b.style.setProperty('--ry', (ev.clientY - r.top) + 'px');
      b.classList.remove('rippling'); void b.offsetWidth; b.classList.add('rippling');
    });

    // the command palette
    $('#palInput').addEventListener('input', function () { palFill(this.value); });
    $('#palInput').addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); palMove(palSel + 1); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); palMove(palSel - 1); }
      else if (ev.key === 'Enter') { ev.preventDefault(); palRun(palSel); }
    });

    document.addEventListener('keydown', function (ev) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((ev.target.tagName || ''));
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') {
        ev.preventDefault(); window.openPalette(); return;
      }
      if (ev.key === 'Escape') {
        window.closePalette(); window.closeDrawer();
        $('#camBox').classList.remove('zoom');
        return;
      }
      if (typing) return;
      if (ev.key === ' ') { ev.preventDefault(); cmd('estop'); toast('Emergency stop sent', 'bad'); return; }
      if (ev.key >= '1' && ev.key <= '8') {
        var b = $$('.navbtn')[+ev.key - 1];
        if (b) go(b.dataset.page);
        return;
      }
      var k = DRIVE_KEYS[ev.key.toLowerCase()];
      if (k && page === 'live') {
        if (S.rc_live) return;
        ev.preventDefault();
        if (!keysDown[k]) { keysDown[k] = true; keyDrive(); }
      }
    });
    document.addEventListener('keyup', function (ev) {
      var k = DRIVE_KEYS[(ev.key || '').toLowerCase()];
      if (k) { keysDown[k] = false; keyDrive(); }
    });
    window.addEventListener('blur', function () { keysDown = {}; keyDrive(); });

    joypad();
    paint();
    connect();
    startPolling();                // until the socket opens, so it is never blank
    api('/api/me').then(function (r) {
      var nm = (r.user && r.user.name) || 'signed in';
      $('#whoName').textContent = nm;
      $('#whoInitial').textContent = nm.slice(0, 1).toUpperCase();
      // still on the password printed in the instructions: say so on every page
      if ($('#pwWarn')) $('#pwWarn').hidden = !(r.user && r.user.must_change);
    }).catch(function () {});

    // Seed the gauge sparklines from the last couple of hours in the database,
    // so they show a trend on the first frame instead of filling up over the
    // next two minutes.
    api('/api/samples?hours=2').then(function (r) {
      var s = r.samples || [];
      var step = Math.max(1, Math.floor(s.length / 60));
      for (var i = 0; i < s.length; i += step) {
        push(hist.batt, s[i].battery_pct);
        push(hist.tank, s[i].tank_pct);
        push(hist.soil, s[i].soil_pct);
      }
      Chart.spark($('#spkBatt'), { points: hist.batt, colour: Chart.token('--s-1') });
      Chart.spark($('#spkTank'), { points: hist.tank, colour: Chart.token('--s-7') });
      Chart.spark($('#spkSoil'), { points: hist.soil, colour: Chart.token('--s-3') });
    }).catch(function () {});

    go((location.hash || '#live').slice(1) || 'live');

    window.addEventListener('resize', function () {
      clearTimeout(window._rs);
      window._rs = setTimeout(function () {
        moveSlider();
        if (page === 'charts') loadCharts();
        if (page === 'field') drawField();
      }, 220);
    });
    window.addEventListener('hashchange', function () {
      var h = (location.hash || '#live').slice(1);
      if (h && h !== page) go(h);
    });

    if (window.Notification && Notification.permission === 'default') {
      $('#askNotify').hidden = false;
    }
  }

  document.addEventListener('DOMContentLoaded', boot);
}());
