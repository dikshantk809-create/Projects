/* AR-750 charts, drawn on a canvas, with no library.
   ---------------------------------------------------------------------------
   The rover often has no internet where it works, so nothing here is fetched
   from anywhere. Roughly 400 lines instead of a 300 KB download.

   Rules kept to throughout:
     - one y scale per chart, never two. Two units means two charts.
     - every axis label names a value the chart actually reaches.
     - the grid and the axes recede, the data does not.
     - the last point is emphasised, because on a rover the last point is now.
     - two series always get a legend; one series never needs one.
     - hover gives a crosshair and the real numbers, on touch as well as mouse.
     - the first draw animates in; redraws of live data do not, because a
       chart that re-animates five times a second is unreadable.
*/
(function (global) {
  'use strict';

  /* Tokens are read live, not cached, so the light/dark toggle is honoured
     without a reload. */
  function tok(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }
  function T() {
    return {
      ink: tok('--ink', '#e9efe9'),
      dim: tok('--dim', '#80928a'),
      line: tok('--line-soft', '#1c251f'),
      panel: tok('--panel-solid', '#141b17'),
      mono: tok('--mono', 'monospace'),
      sans: tok('--sans', 'sans-serif')
    };
  }

  function dpi(canvas, cssW, cssH) {
    var r = global.devicePixelRatio || 1;
    canvas.width = Math.round(cssW * r);
    canvas.height = Math.round(cssH * r);
    canvas.style.height = cssH + 'px';
    canvas.style.width = '100%';
    // willReadFrequently: the hover layer reads the chart back with
    // getImageData on every pointer move, which is slow on a GPU-backed canvas
    var c = canvas.getContext('2d', { willReadFrequently: true });
    c.setTransform(r, 0, 0, r, 0, 0);
    return c;
  }

  var REDUCED = global.matchMedia &&
    global.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* One shared easing + frame loop, so ten charts animating do not each
     start their own requestAnimationFrame chain. */
  function animate(ms, step, done) {
    if (REDUCED) { step(1); if (done) done(); return; }
    var t0 = performance.now();
    function frame(now) {
      var k = Math.min(1, (now - t0) / ms);
      step(1 - Math.pow(1 - k, 3));            // ease-out cubic
      if (k < 1) requestAnimationFrame(frame);
      else if (done) done();
    }
    requestAnimationFrame(frame);
  }

  function niceTop(v) {
    if (v <= 0) return 1;
    var mag = Math.pow(10, Math.floor(Math.log10(v)));
    var n = v / mag;
    var step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
    return step * mag;
  }
  function fmt(v, dp) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return Number(v).toFixed(dp === undefined ? 1 : dp);
  }
  function clock(t) {
    var d = new Date(t * 1000);
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function hex(col, alpha) {
    // accepts #rgb / #rrggbb / rgb(); returns rgba() so gradients work anywhere
    var c = col.trim();
    if (c[0] === '#') {
      if (c.length === 4) c = '#' + c[1] + c[1] + c[2] + c[2] + c[3] + c[3];
      var n = parseInt(c.slice(1), 16);
      return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' +
        (n & 255) + ',' + alpha + ')';
    }
    return c;
  }

  /* ----------------------------------------------------------------- line --
     opts: {points:[{x,y}], colour, unit, dp, min, max, height, animate}
     x is a unix time in seconds.                                           */
  function line(box, opts) {
    var canvas = box.querySelector('canvas') || document.createElement('canvas');
    if (!canvas.parentNode) box.appendChild(canvas);
    var tip = box.querySelector('.tip');
    if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; box.appendChild(tip); }

    var t = T();
    var pts = (opts.points || []).filter(function (p) {
      return p && p.y !== null && p.y !== undefined && !isNaN(p.y);
    });
    var W = box.clientWidth || 320, H = opts.height || 150;
    var c = dpi(canvas, W, H);

    var padL = 46, padR = 14, padT = 12, padB = 22;
    var iw = Math.max(10, W - padL - padR), ih = Math.max(10, H - padT - padB);

    if (pts.length < 2) {
      c.clearRect(0, 0, W, H);
      c.fillStyle = t.dim; c.font = '12px ' + t.sans; c.textAlign = 'center';
      c.fillText('Nothing recorded yet', W / 2, H / 2);
      return;
    }

    var ys = pts.map(function (p) { return p.y; });
    var lo = opts.min !== undefined ? opts.min : Math.min.apply(null, ys);
    var hi = opts.max !== undefined ? opts.max : Math.max.apply(null, ys);
    if (hi - lo < 1e-6) hi = lo + 1;
    var padv = (hi - lo) * 0.12;
    lo -= padv; hi += padv;
    if (opts.min !== undefined) lo = opts.min;
    if (opts.max !== undefined) hi = opts.max;

    var x0 = pts[0].x, x1 = pts[pts.length - 1].x;
    if (x1 - x0 < 1) x1 = x0 + 1;
    var X = function (x) { return padL + (x - x0) / (x1 - x0) * iw; };
    var Y = function (y) { return padT + (1 - (y - lo) / (hi - lo)) * ih; };
    var col = opts.colour || tok('--s-1', '#3987e5');

    function paint(k) {
      c.clearRect(0, 0, W, H);

      // grid: three lines, each labelled with a value the chart reaches
      c.strokeStyle = t.line; c.lineWidth = 1;
      c.fillStyle = t.dim; c.font = '11px ' + t.mono;
      c.textAlign = 'right'; c.textBaseline = 'middle';
      for (var i = 0; i <= 2; i++) {
        var v = lo + (hi - lo) * (i / 2), y = Math.round(Y(v)) + 0.5;
        c.beginPath(); c.moveTo(padL, y); c.lineTo(padL + iw, y); c.stroke();
        c.fillText(fmt(v, opts.dp), padL - 8, y);
      }

      var shown = Math.max(2, Math.round(pts.length * k));
      var seen = pts.slice(0, shown);

      // area under the line, then the line
      var grad = c.createLinearGradient(0, padT, 0, padT + ih);
      grad.addColorStop(0, hex(col, .30));
      grad.addColorStop(1, hex(col, .02));
      c.beginPath();
      c.moveTo(X(seen[0].x), Y(seen[0].y));
      seen.forEach(function (p) { c.lineTo(X(p.x), Y(p.y)); });
      c.lineTo(X(seen[seen.length - 1].x), padT + ih);
      c.lineTo(X(seen[0].x), padT + ih);
      c.closePath(); c.fillStyle = grad; c.fill();

      c.beginPath();
      seen.forEach(function (p, i) {
        var fx = X(p.x), fy = Y(p.y);
        if (i === 0) c.moveTo(fx, fy); else c.lineTo(fx, fy);
      });
      c.strokeStyle = col; c.lineWidth = 2;
      c.lineJoin = 'round'; c.lineCap = 'round';
      c.stroke();

      // the newest reading, marked with a 2px surface ring
      var last = seen[seen.length - 1];
      c.beginPath(); c.arc(X(last.x), Y(last.y), 4.5, 0, 6.2832);
      c.fillStyle = col; c.fill();
      c.strokeStyle = t.panel; c.lineWidth = 2; c.stroke();

      // time at each end
      c.fillStyle = t.dim; c.textAlign = 'left'; c.textBaseline = 'alphabetic';
      c.font = '11px ' + t.mono;
      c.fillText(clock(x0), padL, H - 6);
      c.textAlign = 'right';
      c.fillText(clock(x1), padL + iw, H - 6);
    }

    function wire() {
      hover(box, canvas, tip, function (mx) {
        if (mx < padL || mx > padL + iw) return null;
        var want = x0 + (mx - padL) / iw * (x1 - x0), best = pts[0], bd = 1e18;
        pts.forEach(function (p) {
          var d = Math.abs(p.x - want);
          if (d < bd) { bd = d; best = p; }
        });
        return {
          x: X(best.x), y: Y(best.y), top: padT, bottom: padT + ih,
          text: fmt(best.y, opts.dp) + (opts.unit || '') + '   ' + clock(best.x),
          colour: col
        };
      });
    }

    if (opts.animate === false) { paint(1); wire(); }
    else animate(650, paint, wire);
  }

  /* ------------------------------------------------------------- sparkline --
     A bare trend line for a stat tile. No axes, no hover, no labels: it says
     "which way is this going", and the number beside it says the rest.      */
  function spark(box, opts) {
    var canvas = box.querySelector('canvas') || document.createElement('canvas');
    if (!canvas.parentNode) box.appendChild(canvas);
    var pts = (opts.points || []).filter(function (v) {
      return v !== null && v !== undefined && !isNaN(v);
    });
    var W = box.clientWidth || 120, H = opts.height || 26;
    var c = dpi(canvas, W, H);
    c.clearRect(0, 0, W, H);
    // under about five readings there is no trend to show, and a two-point
    // "sparkline" is a straight bar that lies about the data
    if (pts.length < 5) return;
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts);
    if (hi - lo < 1e-9) { hi = lo + 1; lo -= 1; }
    var col = opts.colour || tok('--s-1', '#3987e5');
    var X = function (i) { return (i / (pts.length - 1)) * (W - 2) + 1; };
    var Y = function (v) { return H - 3 - ((v - lo) / (hi - lo)) * (H - 6); };

    var grad = c.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, hex(col, .34));
    grad.addColorStop(1, hex(col, 0));
    c.beginPath();
    c.moveTo(X(0), Y(pts[0]));
    pts.forEach(function (v, i) { c.lineTo(X(i), Y(v)); });
    c.lineTo(X(pts.length - 1), H); c.lineTo(X(0), H);
    c.closePath(); c.fillStyle = grad; c.fill();

    c.beginPath();
    pts.forEach(function (v, i) { i ? c.lineTo(X(i), Y(v)) : c.moveTo(X(i), Y(v)); });
    c.strokeStyle = col; c.lineWidth = 1.5; c.lineJoin = 'round'; c.stroke();
  }

  /* ------------------------------------------------------------------ bars --
     opts: {rows:[{label, short, a, b}], aName, bName, aColour, bColour}
     Two series side by side, one y scale, a legend, and a 2px surface gap
     between neighbouring bars so they read as separate objects.            */
  function bars(box, opts) {
    var canvas = box.querySelector('canvas') || document.createElement('canvas');
    if (!canvas.parentNode) box.appendChild(canvas);
    var tip = box.querySelector('.tip');
    if (!tip) { tip = document.createElement('div'); tip.className = 'tip'; box.appendChild(tip); }

    var t = T();
    var rows = opts.rows || [];
    var W = box.clientWidth || 320, H = opts.height || 180;
    var c = dpi(canvas, W, H);
    var padL = 36, padR = 12, padT = 12, padB = 26;
    var iw = Math.max(10, W - padL - padR), ih = Math.max(10, H - padT - padB);

    if (!rows.length) {
      c.clearRect(0, 0, W, H);
      c.fillStyle = t.dim; c.font = '12px ' + t.sans;
      c.textAlign = 'center'; c.fillText('Nothing recorded yet', W / 2, H / 2);
      return;
    }

    var top = 0;
    rows.forEach(function (r) { top = Math.max(top, r.a || 0, r.b || 0); });
    top = niceTop(Math.max(1, top));

    var aCol = opts.aColour || tok('--s-1', '#3987e5');
    var bCol = opts.bColour || tok('--s-2', '#d95926');
    var slot = iw / rows.length;
    var bw = Math.max(3, Math.min(17, slot / 2 - 3));
    var hits = [];

    function paint(k) {
      c.clearRect(0, 0, W, H);
      hits.length = 0;

      c.strokeStyle = t.line; c.fillStyle = t.dim;
      c.font = '11px ' + t.mono;
      c.textAlign = 'right'; c.textBaseline = 'middle';
      for (var i = 0; i <= 2; i++) {
        var v = top * i / 2, y = Math.round(padT + ih - (v / top) * ih) + 0.5;
        c.beginPath(); c.moveTo(padL, y); c.lineTo(padL + iw, y); c.stroke();
        c.fillText(String(Math.round(v)), padL - 7, y);
      }

      var every = Math.ceil(rows.length / 7);
      rows.forEach(function (r, idx) {
        var cx = padL + slot * idx + slot / 2;
        [['a', aCol, -1], ['b', bCol, 1]].forEach(function (s) {
          var val = r[s[0]] || 0;
          if (val <= 0) return;
          var h = (val / top) * ih * k;
          var x = cx + (s[2] < 0 ? -bw - 1 : 1);
          var y = padT + ih - h;
          c.fillStyle = s[1];
          roundTop(c, x, y, bw, h, 4);
          hits.push({
            x: x + bw / 2, y: y, w: bw, h: h, colour: s[1],
            text: r.label + '   ' + (s[0] === 'a' ? opts.aName : opts.bName) + ' ' + val
          });
        });
        if (idx % every === 0) {
          c.fillStyle = t.dim; c.textAlign = 'center'; c.textBaseline = 'alphabetic';
          c.font = '10.5px ' + t.mono;
          c.fillText(r.short || r.label, cx, H - 8);
        }
      });
    }

    function wire() {
      hover(box, canvas, tip, function (mx) {
        var best = null, bd = 1e9;
        hits.forEach(function (h) {
          var d = Math.abs(h.x - mx);
          if (d < bd && d < 26) { bd = d; best = h; }
        });
        if (!best) return null;
        return {
          x: best.x, y: best.y, top: padT, bottom: padT + ih,
          text: best.text, colour: best.colour, noline: true
        };
      });
    }

    if (opts.animate === false) { paint(1); wire(); }
    else animate(700, paint, wire);
  }

  /* 4px rounded data-end, anchored square to the baseline. */
  function roundTop(c, x, y, w, h, r) {
    r = Math.min(r, w / 2, Math.max(0, h));
    c.beginPath();
    c.moveTo(x, y + h);
    c.lineTo(x, y + r);
    c.quadraticCurveTo(x, y, x + r, y);
    c.lineTo(x + w - r, y);
    c.quadraticCurveTo(x + w, y, x + w, y + r);
    c.lineTo(x + w, y + h);
    c.closePath(); c.fill();
  }

  /* ------------------------------------------------------------- tally bars
     A horizontal list: one series, labelled directly, so no legend needed. */
  function tally(el, rows, opts) {
    opts = opts || {};
    if (!rows || !rows.length) {
      el.innerHTML = '<div class="empty">Nothing found yet.</div>';
      return;
    }
    var top = rows.reduce(function (m, r) { return Math.max(m, r.n); }, 1);
    el.innerHTML = rows.map(function (r, i) {
      var pc = Math.max(3, Math.round(r.n / top * 100));
      return '<div style="display:grid;gap:5px">' +
        '<div style="display:flex;gap:10px;font-size:13px">' +
          '<span>' + esc(r.name) + '</span>' +
          '<span class="num" style="margin-left:auto;color:var(--dim)">' + r.n + '</span>' +
        '</div>' +
        '<div class="meter" style="height:8px;margin-top:0">' +
          '<span style="width:0;background:' + (opts.colour || 'var(--s-2)') +
          '" data-w="' + pc + '"></span></div>' +
      '</div>';
    }).join('');
    // let the layout settle, then run the bars out to width
    requestAnimationFrame(function () {
      [].slice.call(el.querySelectorAll('.meter>span')).forEach(function (s, i) {
        setTimeout(function () { s.style.width = s.dataset.w + '%'; }, i * 55);
      });
    });
  }

  /* ----------------------------------------------------------- hover layer */
  function hover(box, canvas, tip, find) {
    if (canvas._unwire) canvas._unwire();
    function at(ev) {
      var r = canvas.getBoundingClientRect();
      var p = ev.touches ? ev.touches[0] : ev;
      return { x: p.clientX - r.left, y: p.clientY - r.top };
    }
    var saved = null;
    function snapshot() {
      try {
        saved = canvas.getContext('2d')
          .getImageData(0, 0, canvas.width, canvas.height);
      } catch (e) { saved = null; }
    }
    function redraw(hit) {
      if (!saved) return;
      var c = canvas.getContext('2d');
      c.save(); c.setTransform(1, 0, 0, 1, 0, 0);
      c.putImageData(saved, 0, 0); c.restore();
      if (!hit) return;
      if (!hit.noline) {
        c.save();
        c.strokeStyle = T().dim; c.lineWidth = 1; c.setLineDash([3, 3]);
        c.beginPath(); c.moveTo(hit.x, hit.top); c.lineTo(hit.x, hit.bottom); c.stroke();
        c.restore();
      }
      c.save();
      c.beginPath(); c.arc(hit.x, hit.y, 4.5, 0, 6.2832);
      c.fillStyle = hit.colour; c.fill();
      c.strokeStyle = T().panel; c.lineWidth = 2; c.stroke();
      c.restore();
    }
    function move(ev) {
      var m = at(ev), hit = find(m.x, m.y);
      if (!hit) { tip.classList.remove('on'); redraw(); return; }
      redraw(hit);
      tip.textContent = hit.text;
      tip.classList.add('on');
      var tw = tip.offsetWidth || 90;
      tip.style.left = Math.max(2, Math.min(box.clientWidth - tw - 2,
                                            hit.x - tw / 2)) + 'px';
      tip.style.top = Math.max(0, hit.y - 38) + 'px';
      if (ev.cancelable && ev.touches) ev.preventDefault();
    }
    function leave() { tip.classList.remove('on'); redraw(); }

    setTimeout(snapshot, 0);
    canvas.addEventListener('mousemove', move);
    canvas.addEventListener('mouseleave', leave);
    canvas.addEventListener('touchstart', move, { passive: false });
    canvas.addEventListener('touchmove', move, { passive: false });
    canvas.addEventListener('touchend', leave);
    canvas._unwire = function () {
      canvas.removeEventListener('mousemove', move);
      canvas.removeEventListener('mouseleave', leave);
      canvas.removeEventListener('touchstart', move);
      canvas.removeEventListener('touchmove', move);
      canvas.removeEventListener('touchend', leave);
    };
  }

  global.Chart = { line: line, bars: bars, tally: tally, spark: spark, token: tok };
}(window));
