"""
SPHEREx 3D website, black theme (Flask + Three.js).

Run:
    pip install flask
    python app.py
Then open http://127.0.0.1:5000 in your browser (needs internet for the
3D library and fonts).

Edit the data lists below to change any text.
"""

from flask import Flask, Response, render_template, render_template_string, request, send_from_directory
from dotenv import load_dotenv
import os
from pathlib import Path
from urllib.parse import urlsplit
import requests

load_dotenv()

app = Flask(__name__)


def _normalize_api_base_url(value: str) -> str:
    api_base = value.strip().rstrip("/")
    return api_base[:-4] if api_base.endswith("/api") else api_base


API_BASE_URL = _normalize_api_base_url(os.getenv("SPHEREX_API_URL", ""))
DATA_DIR = Path(os.getenv("SPHEREX_DATA_DIR", Path(__file__).resolve().parent / "data"))
GEOGRAPHY_DIR = DATA_DIR / "geography"
GEOGRAPHY_FILES = {
    "ne_50m_admin_0_countries.geojson",
    "ne_50m_geography_marine_polys.geojson",
}


# ---------------------------------------------------------------- data

# Six detector arrays (start, end) in micrometres, 17 bands each = 102 bands.
# Band edges are approximate and used for illustration.
ARRAYS = [(0.75, 1.11), (1.11, 1.64), (1.64, 2.42), (2.42, 3.82), (3.82, 4.42), (4.42, 5.00)]
BANDS_PER_ARRAY = 17
WL_MIN, WL_MAX = 0.75, 5.00

# Ice features: (short label, name, centre, half-width) in micrometres.
ICES = [
    ("H₂O", "Water ice", 3.00, 0.20),
    ("CO₂", "Carbon dioxide ice", 4.27, 0.05),
    ("CO", "Carbon monoxide ice", 4.67, 0.04),
]

TITLE = "SPHEREx"
FULL_NAME = "Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer"
LEAD = "NASA's infrared space telescope, mapping the entire sky in 102 colors."

MODES = [
    {
        "key": "orbit",
        "label": "Orbit",
        "text": (
            "SPHEREx flies from pole to pole along the line between day and night, "
            "circling Earth about 14.5 times a day. Its orbit plane always faces the "
            "Sun, so it stays cool and its solar panel stays in sunlight. Sizes and "
            "distances are not to scale. The yellow arrow points to the Sun."
        ),
    },
    {
        "key": "survey",
        "label": "Sky survey",
        "text": (
            "Each orbit, SPHEREx scans a strip of sky from pole to pole. As Earth "
            "moves around the Sun, the strip swings around too and covers the whole "
            "sky in about six months. Move the slider or press play. The two yellow "
            "dots, where every strip crosses, get the most data."
        ),
    },
    {
        "key": "craft",
        "label": "Spacecraft",
        "text": (
            "Tap one of the parts below to see what it does and where it sits. "
            "Drag to turn the model. It is a simplified version of the real spacecraft."
        ),
    },
]

PARTS = [
    {"key": "shields", "label": "Photon shields",
     "text": "Three nested cones, made of aluminum honeycomb between thin aluminum sheets, block light and heat from the Sun and Earth, and from the spacecraft's own electronics."},
    {"key": "vgroove", "label": "V-groove radiators",
     "text": "Stacked conical mirrors made of wedges that bounce infrared light out through the gaps between the shields. They carry heat away so the telescope stays below -210 °C."},
    {"key": "telescope", "label": "Telescope",
     "text": "A 20 cm telescope with six detectors behind linear variable filters. It is tipped slightly toward the Sun so it can see the whole sky while staying inside the shields."},
    {"key": "bus", "label": "Spacecraft bus",
     "text": "The part at room temperature. It holds the computer and electronics and moves the observatory quickly as it scans the sky."},
    {"key": "panel", "label": "Solar panel",
     "text": "Because the orbit follows the day-night line, the panel almost always faces the Sun, so power stays steady. A battery covers brief trips through Earth's shadow."},
]

GOALS = [
    ("How did the universe begin?",
     "Right after the Big Bang, space expanded extremely fast. SPHEREx maps the 3D positions "
     "of hundreds of millions of galaxies and looks for traces of that expansion, called "
     "inflation, in how they are spread out."),
    ("How do galaxies form and grow?",
     "Many galaxies are too faint to see one by one. SPHEREx measures their combined glow "
     "instead, to piece together how galaxies have formed and grown over cosmic history."),
    ("Where is the water in our galaxy?",
     "In cold clouds where stars are born, water, carbon dioxide and carbon monoxide freeze "
     "onto dust grains. SPHEREx looks for the light these ices absorb, tracking the raw "
     "ingredients for planets and life."),
]

NUMBERS = [
    ("102", "infrared colors"),
    ("4", "all-sky scans in two years"),
    ("450 million", "galaxies to map"),
    ("0.75–5 µm", "wavelength range"),
    ("14.5", "orbits around Earth per day"),
    ("−210 °C", "or colder, cooled by shields alone"),
]

NEIGHBORS = [
    ("PUNCH", "Four small satellites that work as one instrument to study the Sun's corona. They shared SPHEREx's rocket ride in March 2025."),
    ("James Webb Space Telescope", "SPHEREx finds targets worth a closer look, and Webb provides the detailed follow-up."),
    ("Roman Space Telescope", "Another NASA observatory that can follow up SPHEREx discoveries in more detail."),
    ("WISE", "An earlier infrared telescope that mapped the whole sky, but in far fewer colors."),
]

TIMELINE = [
    ("February 2019", "NASA selects SPHEREx as a Medium-Class Explorer mission."),
    ("March 11, 2025", "Launch on a SpaceX Falcon 9 from California."),
    ("May 2025", "The sky survey begins."),
    ("December 2025", "The first all-sky map is complete."),
    ("Every six months", "Another full scan, until four are done."),
]

LINKS = [
    ("SPHEREx at Caltech", "https://spherex.caltech.edu"),
    ("NASA mission page", "https://science.nasa.gov/mission/spherex/"),
    ("NASA/IPAC Infrared Science Archive", "https://irsa.ipac.caltech.edu/"),
]

DISCLAIMER = "Unofficial educational page. Not affiliated with or endorsed by NASA."

# ------------------------------------------------------- spectrum builder


def build_bands():
    bands = []
    for lo, hi in ARRAYS:
        step = (hi - lo) / BANDS_PER_ARRAY
        for i in range(BANDS_PER_ARRAY):
            b_lo, b_hi = lo + i * step, lo + (i + 1) * step
            mid = (b_lo + b_hi) / 2
            hue = 250 * (1 - (mid - WL_MIN) / (WL_MAX - WL_MIN))  # blue to red
            ices = [n for _l, n, c, h in ICES if b_lo <= c + h and b_hi >= c - h]
            bands.append({"lo": round(b_lo, 3), "hi": round(b_hi, 3),
                          "color": f"hsl({hue:.0f} 85% 58%)", "ices": ices})
    return bands


def band_index(bands, wl):
    return next((i for i, b in enumerate(bands) if b["lo"] <= wl <= b["hi"]), 0)


# ------------------------------------------------------------- template

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}: the whole sky in 102 colors</title>
  <meta name="description" content="{{ lead }}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@500;600;700&family=Michroma&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#000; --text:#F4F5F8; --muted:#A9ACB8; --rule:#26262B; --red:#FC3D21;
      --display:"Michroma","Eurostile",sans-serif; --cond:"Barlow Condensed","Arial Narrow",sans-serif;
      --sans:"Barlow","Helvetica Neue",Arial,sans-serif; }
    * { box-sizing:border-box; }
    [hidden] { display:none !important; }
    html { scroll-behavior:smooth; }
    body { margin:0; background:var(--bg); color:var(--text); font:1.0625rem/1.65 var(--sans); overflow-x:hidden; }
    a { color:inherit; text-underline-offset:5px; text-decoration-thickness:2px; }
    a:hover { text-decoration-color:var(--red); }
    a:focus-visible, input:focus-visible, button:focus-visible { outline:3px solid #fff; outline-offset:3px; }
    .wrap { max-width:1100px; margin:0 auto; padding:0 1.25rem; }
    p { margin:0; }
    section[id] { scroll-margin-top:64px; }

    .top { position:sticky; top:0; z-index:20; background:rgba(0,0,0,.9); backdrop-filter:blur(8px); border-bottom:1px solid var(--rule); }
    .bar { display:flex; justify-content:space-between; align-items:center; min-height:56px; gap:1rem; }
    .brand { font:400 .95rem var(--display); letter-spacing:.08em; text-decoration:none; }
    .navlinks { display:flex; gap:1.1rem; }
    .navlinks a { font:600 .95rem var(--cond); letter-spacing:.12em; text-transform:uppercase; text-decoration:none; color:var(--muted); padding:.5rem 0; }
    .navlinks a:hover { color:var(--text); }
    @media (max-width:700px) {
      .bar { align-items:flex-start; flex-direction:column; padding-top:.7rem; padding-bottom:.7rem; }
      .navlinks { flex-wrap:wrap; gap:.45rem 1rem; }
    }

    .kicker { font:600 1rem var(--cond); letter-spacing:.18em; text-transform:uppercase; color:var(--red); }
    h1 { margin:.5rem 0 0; font:400 clamp(2.4rem,12.5vw,7.5rem)/1 var(--display); letter-spacing:.01em; }
    h2 { margin:0 0 1.5rem; font:600 clamp(1.7rem,5vw,2.4rem)/1.1 var(--cond); letter-spacing:.08em; text-transform:uppercase; }
    h2::before { content:""; display:block; width:3rem; height:4px; background:var(--red); margin-bottom:1rem; }
    h3 { margin:0 0 .5rem; font:600 1.3rem/1.25 var(--cond); letter-spacing:.04em; text-transform:uppercase; }
    .hero { padding:3.5rem 0 2rem; }
    .lead { margin:1.5rem 0 .75rem; max-width:30ch; font:500 clamp(1.4rem,4.2vw,2.1rem)/1.25 var(--sans); }
    .full, .muted { color:var(--muted); }
    .full { max-width:60ch; font-size:.95rem; }
    section.block { padding:2.5rem 0 3rem; }

    .tabs { display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 1rem; }
    button { font:600 1rem var(--cond); letter-spacing:.1em; text-transform:uppercase; color:var(--text); background:transparent;
      border:1px solid #3a3a42; min-height:44px; padding:.5rem 1.1rem; cursor:pointer; }
    button:hover { border-color:#fff; }
    button[aria-pressed="true"] { background:var(--text); color:#000; border-color:var(--text); }
    .partctl { margin-top:1rem; }
    .scene { width:100vw; margin-left:calc(50% - 50vw); height:clamp(24rem,72vh,44rem); background:#000; overflow:hidden;
      border-top:1px solid var(--rule); border-bottom:1px solid var(--rule); }
    .scene canvas { display:block; width:100%; height:100%; cursor:grab; touch-action:pan-y; }
    .scene .nogl { padding:2rem 1.25rem; color:var(--muted); }
    .ctrl { display:flex; align-items:center; gap:1rem; flex-wrap:wrap; margin-top:1rem; }
    .ctrl input { flex:1 1 12rem; accent-color:#fff; }
    .info { margin-top:1rem; max-width:64ch; color:var(--muted); }
    .month { font-weight:600; color:var(--text); }

    .strip { position:relative; display:flex; height:clamp(6rem,20vw,10rem); cursor:crosshair; touch-action:pan-y; user-select:none; }
    .strip i { flex:1; display:block; }
    .marker { position:absolute; top:-.7rem; bottom:-.7rem; left:0; width:2px; margin-left:-1px; background:#fff; pointer-events:none; }
    .ticks { position:relative; height:1.7rem; margin-top:1.1rem; }
    .ticks span { position:absolute; top:.45rem; transform:translateX(-50%); font-size:.875rem; color:var(--muted); }
    .ticks span::before { content:""; position:absolute; left:50%; top:-.5rem; width:1px; height:.4rem; background:var(--muted); }
    .slider { width:100%; margin:.5rem 0 0; accent-color:#fff; }
    .readout { margin:1rem 0 .15rem; font-size:1.25rem; font-weight:600; }
    .note { max-width:62ch; color:var(--muted); min-height:3.2em; }

    .goals { display:grid; gap:2rem; }
    .goals > div, .nums > div { border-top:1px solid var(--rule); padding-top:1rem; }
    .goals p { color:var(--muted); max-width:40ch; }
    .nums { display:grid; grid-template-columns:repeat(2,1fr); gap:1.75rem 1.25rem; }
    .nums b { display:block; font:600 clamp(2.4rem,9vw,4rem)/1 var(--cond); letter-spacing:.01em; }
    .nums span { color:var(--muted); font-size:.95rem; }
    @media (min-width:820px) { .goals, .nums { grid-template-columns:repeat(3,1fr); gap:2.5rem; } }

    .rows { margin:0; }
    .rows > div { display:grid; gap:.2rem 2rem; padding:1rem 0; border-top:1px solid var(--rule); }
    .rows > div:last-child { border-bottom:1px solid var(--rule); }
    .rows dt { font-weight:600; }
    .rows dd { margin:0; color:var(--muted); max-width:62ch; }
    .two { display:grid; gap:2.5rem; }
    @media (min-width:900px) { .two { grid-template-columns:1fr 1fr; gap:3rem; } }
    .links { display:flex; flex-direction:column; gap:.75rem; }
    .links a { font:600 clamp(1.4rem,5vw,2rem)/1.2 var(--cond); letter-spacing:.06em; text-transform:uppercase; width:fit-content; }
    footer { border-top:1px solid var(--rule); padding:2rem 0 3rem; color:var(--muted); font-size:.9rem; }
    .foot { display:grid; gap:1rem; }
    .foot .brand { color:var(--text); }
    @media (min-width:700px) { .foot { grid-template-columns:1fr 1fr; gap:3rem; } }
  </style>
</head>
<body>
  <nav class="top" aria-label="Main">
    <div class="wrap bar">
      <a class="brand" href="#top">SPHEREx</a>
      <div class="navlinks"><a href="/explorer">Data Explorer</a><a href="/tracker">Live Tracker</a><a href="/fits">FITS Viewer</a><a href="#explore">3D</a><a href="#spectrum">Spectrum</a><a href="#science">Science</a><a href="#mission">Mission</a></div>
    </div>
  </nav>
  <main class="wrap">
    <header class="hero" id="top">
      <p class="kicker">Space telescope mission · Launched March 2025</p>
      <h1>{{ title }}</h1>
      <p class="lead">{{ lead }}</p>
      <p class="full">{{ full_name }}</p>
    </header>

    <section class="block" id="explore" aria-labelledby="d3-h">
      <h2 id="d3-h">See it in 3D</h2>
      <div class="tabs" role="group" aria-label="Choose a 3D view">
        {% for m in modes %}<button type="button" data-mode="{{ m.key }}" aria-pressed="{{ 'true' if loop.first else 'false' }}">{{ m.label }}</button>{% endfor %}
      </div>
      <div class="scene" id="scene" role="img" aria-label="Interactive 3D view of the SPHEREx telescope. Drag to rotate."></div>
      <div class="tabs partctl" id="partCtrl" role="group" aria-label="Spacecraft parts" hidden>
        {% for p in parts %}<button type="button" data-part="{{ p.key }}" aria-pressed="false">{{ p.label }}</button>{% endfor %}
      </div>
      <div class="ctrl" id="surveyCtrl" hidden>
        <button type="button" id="play">Play</button>
        <input type="range" id="month" min="0" max="600" value="0" aria-label="Months into the survey">
        <span class="month" id="monthOut" aria-live="polite"></span>
      </div>
      <p class="info" id="modeText"></p>
    </section>

    <section class="block" id="spectrum" aria-labelledby="sp-h">
      <h2 id="sp-h">102 colors of light you can't see</h2>
      <div class="strip" id="strip" aria-hidden="true">
        {% for b in bands %}<i style="background: {{ b.color }}"></i>{% endfor %}
        <div class="marker" id="marker"></div>
      </div>
      <div class="ticks" aria-hidden="true">
        {% for t in ticks %}<span style="left: {{ t.left }}%">{{ t.label }}</span>{% endfor %}
      </div>
      <input class="slider" id="slider" type="range" min="1" max="{{ bands|length }}" value="1" aria-label="Choose one of the {{ bands|length }} bands">
      <p class="readout" id="readout" aria-live="polite"></p>
      <p class="note" id="note"></p>
      <p class="muted" style="margin-top:1rem;max-width:62ch;font-size:.9rem">
        Drag across the bars or use the slider. False colors: blue is the shortest wavelength
        SPHEREx sees, red the longest. Labels mark where water, carbon dioxide and carbon
        monoxide ices absorb light. Band edges are approximate.
      </p>
    </section>

    <section class="block" id="science" aria-labelledby="g-h">
      <h2 id="g-h">What it is for</h2>
      <div class="goals">
        {% for t, x in goals %}<div><h3>{{ t }}</h3><p>{{ x }}</p></div>{% endfor %}
      </div>
    </section>

    <section class="block" id="mission" aria-labelledby="n-h">
      <h2 id="n-h">By the numbers</h2>
      <div class="nums">
        {% for n, l in numbers %}<div><b>{{ n }}</b><span>{{ l }}</span></div>{% endfor %}
      </div>
    </section>

    <section class="block two">
      <div>
        <h2>Its neighbors</h2>
        <dl class="rows">
          {% for n, x in neighbors %}<div><dt>{{ n }}</dt><dd>{{ x }}</dd></div>{% endfor %}
        </dl>
      </div>
      <div>
        <h2>Timeline</h2>
        <dl class="rows">
          {% for n, x in timeline %}<div><dt>{{ n }}</dt><dd>{{ x }}</dd></div>{% endfor %}
        </dl>
      </div>
    </section>

    <section class="block" aria-labelledby="l-h">
      <h2 id="l-h">Learn more</h2>
      <div class="links">
        {% for n, u in links %}<a href="{{ u }}" target="_blank" rel="noopener">{{ n }}</a>{% endfor %}
      </div>
    </section>
  </main>
  <footer>
    <div class="wrap foot">
      <div><a class="brand" href="#top">SPHEREx</a><p style="margin-top:.5rem">{{ disclaimer }}</p></div>
      <p>Facts come from public NASA, JPL and Caltech sources. The 3D scene is a simplified model and is not to scale.</p>
    </div>
  </footer>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script>
    /* ---------- spectrum ---------- */
    (function () {
      var BANDS = {{ bands|tojson }};
      var strip = document.getElementById('strip'), marker = document.getElementById('marker');
      var slider = document.getElementById('slider'), readout = document.getElementById('readout'), note = document.getElementById('note');
      var DEFAULT_NOTE = 'Infrared light is invisible to us, so SPHEREx sees colors our eyes cannot.';
      function show(i) {
        i = Math.max(0, Math.min(BANDS.length - 1, i));
        var b = BANDS[i];
        var text = 'Band ' + (i + 1) + ' of ' + BANDS.length + ': ' + b.lo.toFixed(2) + ' to ' + b.hi.toFixed(2) + ' micrometres';
        marker.style.left = ((i + 0.5) / BANDS.length * 100) + '%';
        slider.value = i + 1;
        slider.setAttribute('aria-valuetext', text);
        readout.textContent = text;
        note.textContent = b.ices.length ? b.ices.join(' and ') + ' absorbs light at these wavelengths. SPHEREx detects it by looking for the dip.' : DEFAULT_NOTE;
      }
      function fromPointer(e) {
        var r = strip.getBoundingClientRect();
        show(Math.floor((e.clientX - r.left) / r.width * BANDS.length));
      }
      strip.addEventListener('pointermove', fromPointer);
      strip.addEventListener('pointerdown', fromPointer);
      slider.addEventListener('input', function () { show(Number(slider.value) - 1); });
      show({{ default_index }});
    })();

    /* ---------- 3D scene ---------- */
    (function () {
      var MODES = {{ modes|tojson }};
      var host = document.getElementById('scene');
      var tabs = document.querySelectorAll('[data-mode]');
      var modeText = document.getElementById('modeText'), ctrl = document.getElementById('surveyCtrl');
      var partCtrl = document.getElementById('partCtrl'), partBtns = document.querySelectorAll('[data-part]'), PARTS = {{ parts|tojson }};
      var mSlider = document.getElementById('month'), mOut = document.getElementById('monthOut'), playBtn = document.getElementById('play');
      var renderer;
      if (!window.THREE) { host.innerHTML = '<p class="nogl">The 3D view needs an internet connection to load. Reload the page when you are online.</p>'; return; }
      try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
      catch (e) { host.innerHTML = '<p class="nogl">This browser does not support 3D (WebGL).</p>'; return; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setClearColor(0x000000, 1);
      renderer.outputEncoding = THREE.sRGBEncoding;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
      host.appendChild(renderer.domElement);
      var scene = new THREE.Scene();
      var cam = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
      var i;

      /* stars */
      function starLayer(n, size, hex) {
        var p = [];
        for (var s = 0; s < n; s++) {
          var u = Math.random() * 2 - 1, a2 = Math.random() * 6.2832, q = Math.sqrt(1 - u * u);
          p.push(60 * q * Math.cos(a2), 60 * u, 60 * q * Math.sin(a2));
        }
        var sg = new THREE.BufferGeometry();
        sg.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
        scene.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: hex, size: size, sizeAttenuation: false })));
      }
      starLayer(2400, 1.1, 0x8d96c9);
      starLayer(240, 2.2, 0xffffff);

      /* light: the Sun is on the +x side */
      scene.add(new THREE.AmbientLight(0x4a5588, 0.4));
      var sun = new THREE.DirectionalLight(0xffffff, 1.7);
      sun.position.set(10, 0, 0);
      scene.add(sun);

      /* reflections for the metal parts: a dark sky with a bright Sun */
      (function () {
        var c = document.createElement('canvas');
        c.width = 512; c.height = 256;
        var x = c.getContext('2d');
        var gr = x.createLinearGradient(0, 0, 0, 256);
        gr.addColorStop(0, '#202a55'); gr.addColorStop(0.5, '#070914'); gr.addColorStop(1, '#16307a');
        x.fillStyle = gr; x.fillRect(0, 0, 512, 256);
        var sp = x.createRadialGradient(256, 128, 0, 256, 128, 70);
        sp.addColorStop(0, '#ffffff'); sp.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = sp; x.fillRect(0, 0, 512, 256);
        scene.environment = new THREE.PMREMGenerator(renderer).fromEquirectangular(new THREE.CanvasTexture(c)).texture;
      })();

      /* real Earth textures, loaded once and shared (falls back to plain blue if offline) */
      var TEX_URL = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/textures/planets/';
      var loader = new THREE.TextureLoader();
      loader.setCrossOrigin('anonymous');
      var texCache = {};
      function getTex(name, srgb, cb) {
        var e = texCache[name];
        if (!e) {
          e = texCache[name] = { cbs: [], done: false, t: null };
          e.t = loader.load(TEX_URL + name, function (tx) {
            tx.anisotropy = renderer.capabilities.getMaxAnisotropy();
            if (srgb) tx.encoding = THREE.sRGBEncoding;
            e.done = true;
            e.cbs.forEach(function (f) { f(tx); });
          }, undefined, function () {});
        }
        if (e.done) cb(e.t); else e.cbs.push(cb);
      }

      function makeEarth(rad) {
        var g = new THREE.Group();
        var m = new THREE.MeshPhongMaterial({ color: 0x1f3f9c, specular: 0x444444, shininess: 16 });
        var earth = new THREE.Mesh(new THREE.SphereGeometry(rad, 96, 64), m);
        g.add(earth);
        getTex('earth_atmos_2048.jpg', true, function (tx) { m.map = tx; m.color.setHex(0xffffff); m.needsUpdate = true; });
        getTex('earth_specular_2048.jpg', false, function (tx) { m.specularMap = tx; m.needsUpdate = true; });
        getTex('earth_lights_2048.png', true, function (tx) { m.emissiveMap = tx; m.emissive.setHex(0x9a6a30); m.needsUpdate = true; });
        var cm = new THREE.MeshPhongMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 });
        var clouds = new THREE.Mesh(new THREE.SphereGeometry(rad * 1.012, 64, 48), cm);
        g.add(clouds);
        getTex('earth_clouds_1024.png', true, function (tx) { cm.map = tx; cm.opacity = 0.9; cm.needsUpdate = true; });
        g.add(new THREE.Mesh(new THREE.SphereGeometry(rad * 1.14, 64, 48), new THREE.ShaderMaterial({
          vertexShader: 'varying vec3 vN; void main() { vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
          fragmentShader: 'varying vec3 vN; void main() { float k = pow(max(0.0, 0.66 - dot(vN, vec3(0.0, 0.0, 1.0))), 3.0); gl_FragColor = vec4(0.32, 0.58, 1.0, 1.0) * k * 2.2; }',
          side: THREE.BackSide, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false
        })));
        g.userData.earth = earth;
        g.userData.clouds = clouds;
        return g;
      }

      function panelTex() {
        var c = document.createElement('canvas');
        c.width = 128; c.height = 256;
        var x = c.getContext('2d');
        x.fillStyle = '#12235e'; x.fillRect(0, 0, 128, 256);
        x.strokeStyle = '#4f6fd0'; x.lineWidth = 2;
        for (var i2 = 0; i2 <= 8; i2++) { x.beginPath(); x.moveTo(i2 * 16, 0); x.lineTo(i2 * 16, 256); x.stroke(); }
        for (i2 = 0; i2 <= 16; i2++) { x.beginPath(); x.moveTo(0, i2 * 16); x.lineTo(128, i2 * 16); x.stroke(); }
        var tx = new THREE.CanvasTexture(c);
        tx.encoding = THREE.sRGBEncoding;
        return tx;
      }

      /* SPHEREx model: bus, solar panel, V-groove radiators, three photon shields, tilted telescope. Cone axis is +y. */
      function makeSat() {
        var g = new THREE.Group(), P = {}, k;
        function M(c, mt, ro, extra) {
          var o = { color: c, metalness: mt, roughness: ro, side: THREE.DoubleSide, flatShading: true };
          for (var key in extra) o[key] = extra[key];
          return new THREE.MeshStandardMaterial(o);
        }
        function part(name) { P[name] = new THREE.Group(); g.add(P[name]); return P[name]; }
        function add(grp, geo, mat, x, y, z) {
          var me = new THREE.Mesh(geo, mat);
          me.position.set(x || 0, y || 0, z || 0);
          grp.add(me);
          return me;
        }
        var bus = part('bus');
        add(bus, new THREE.BoxGeometry(0.2, 0.1, 0.2), M(0xc9a24b, 0.9, 0.38));
        add(bus, new THREE.BoxGeometry(0.21, 0.012, 0.21), M(0x3a3d4a, 0.5, 0.6), 0, -0.03, 0);
        add(bus, new THREE.BoxGeometry(0.04, 0.03, 0.04), M(0x20222b, 0.4, 0.6), -0.07, 0.065, 0.06);
        add(bus, new THREE.CylinderGeometry(0.004, 0.004, 0.08, 8), M(0xd0d4e0, 0.8, 0.3), -0.12, 0, -0.06);
        add(bus, new THREE.SphereGeometry(0.025, 16, 12), M(0xe8eaf2, 0.6, 0.35, { flatShading: false }), -0.12, 0.05, -0.06);
        var panel = part('panel');
        add(panel, new THREE.BoxGeometry(0.06, 0.012, 0.012), M(0x9aa3b8, 0.8, 0.4), 0.13, 0, 0);
        add(panel, new THREE.BoxGeometry(0.012, 0.12, 0.42), M(0xffffff, 0.35, 0.45, { map: panelTex(), flatShading: false }), 0.17, 0, 0);
        var vg = part('vgroove');
        for (k = 0; k < 3; k++) add(vg, new THREE.CylinderGeometry(0.19, 0.08, 0.045, 24, 1, true), M(0xaab4c8, 0.95, 0.2), 0, 0.075 + k * 0.045, 0);
        var sh = part('shields'), tops = [0.24, 0.19, 0.14], cols = [0xe6e9f0, 0xc9cfdc, 0xaab2c6], hs = [0.28, 0.25, 0.22];
        for (k = 0; k < 3; k++) add(sh, new THREE.CylinderGeometry(tops[k], 0.1, hs[k], 24, 1, true), M(cols[k], 0.85, 0.4), 0, 0.2 + hs[k] / 2, 0);
        var tel = part('telescope');
        tel.position.set(0, 0.3, 0);
        tel.rotation.z = -0.18;
        add(tel, new THREE.CylinderGeometry(0.05, 0.05, 0.2, 24), M(0x2a2e3c, 0.7, 0.35, { flatShading: false }));
        add(tel, new THREE.CylinderGeometry(0.044, 0.044, 0.01, 24), M(0x000000, 0.2, 0.1, { flatShading: false }), 0, 0.1, 0);
        g.userData.parts = P;
        return g;
      }

      /* orbit view */
      var orbit = new THREE.Group();
      scene.add(orbit);
      var earth1 = makeEarth(1);
      orbit.add(earth1);
      var OR = 1.55, lp = [];
      for (i = 0; i < 128; i++) { var a = i / 128 * 6.2832; lp.push(new THREE.Vector3(0, OR * Math.cos(a), OR * Math.sin(a))); }
      orbit.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(lp), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 })));
      var sat = makeSat();
      sat.scale.setScalar(0.8);
      orbit.add(sat);
      orbit.add(new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(2.6, 0, 0), 1.5, 0xffd36e, 0.35, 0.18));

      /* survey view: strips are great circles through the sky's poles (y axis) */
      var survey = new THREE.Group();
      scene.add(survey);
      var earth2 = makeEarth(0.28);
      survey.add(earth2);
      survey.add(new THREE.Mesh(new THREE.SphereGeometry(2, 24, 16), new THREE.MeshBasicMaterial({ color: 0x7088ea, wireframe: true, transparent: true, opacity: 0.12 })));
      var N = 36, rings = [];
      for (i = 0; i < N; i++) {
        var col = new THREE.Color().setHSL(250 * (1 - i / N) / 360, 0.85, 0.58);
        var ring = new THREE.Mesh(new THREE.TorusGeometry(2, 0.022, 6, 96), new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.7 }));
        ring.rotation.y = i / N * Math.PI;
        survey.add(ring);
        rings.push(ring);
      }
      var cur = new THREE.Mesh(new THREE.TorusGeometry(2.02, 0.05, 8, 96), new THREE.MeshBasicMaterial({ color: 0xffffff }));
      survey.add(cur);
      [1, -1].forEach(function (s) {
        var p = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffd36e }));
        p.position.y = 2 * s;
        survey.add(p);
      });

      /* spacecraft view */
      var craft = new THREE.Group();
      scene.add(craft);
      var big = makeSat();
      big.scale.setScalar(2.6);
      big.position.y = -0.56;
      craft.add(big);

      /* state */
      var BASE = { orbit: 5.6, survey: 6.6, craft: 2.7 };
      var mode = 'orbit', zoom = 1, rad = 5.6, az = 1.0, el = 0.32, ang = 0;
      var month = 0, playing = false, drag = false, lx = 0, onscreen = true;
      var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      function setMonth(v) {
        month = v;
        var deg = month / 6 * 180;
        cur.rotation.y = deg * Math.PI / 180;
        rings.forEach(function (rg, j) { rg.visible = j * 5 <= deg; });
        mSlider.value = Math.round(month * 100);
        mOut.textContent = 'Month ' + month.toFixed(1) + ' of 6: about ' + Math.round(month / 6 * 100) + '% of the sky';
      }
      function setMode(k) {
        mode = k; zoom = 1;
        orbit.visible = k === 'orbit'; survey.visible = k === 'survey'; craft.visible = k === 'craft';
        ctrl.hidden = k !== 'survey';
        partCtrl.hidden = k !== 'craft';
        if (k === 'craft') pick(null);
        tabs.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-mode') === k ? 'true' : 'false'); });
        modeText.textContent = MODES.filter(function (m) { return m.key === k; })[0].text;
      }
      tabs.forEach(function (b) { b.addEventListener('click', function () { setMode(b.getAttribute('data-mode')); }); });
      mSlider.addEventListener('input', function () { setMonth(Number(mSlider.value) / 100); });
      playBtn.addEventListener('click', function () {
        playing = !playing;
        playBtn.textContent = playing ? 'Pause' : 'Play';
        if (playing && month >= 6) setMonth(0);
      });

      function pick(key) {
        var ps = big.userData.parts;
        Object.keys(ps).forEach(function (name) {
          ps[name].traverse(function (o) { if (o.material) o.material.emissive.setHex(name === key ? 0xa3260f : 0x000000); });
        });
        partBtns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-part') === key ? 'true' : 'false'); });
        modeText.textContent = key
          ? PARTS.filter(function (p) { return p.key === key; })[0].text
          : MODES.filter(function (m) { return m.key === 'craft'; })[0].text;
      }
      partBtns.forEach(function (b) {
        b.addEventListener('click', function () {
          pick(b.getAttribute('aria-pressed') === 'true' ? null : b.getAttribute('data-part'));
        });
      });

      /* input: drag to turn, wheel to zoom */
      var cv = renderer.domElement;
      cv.addEventListener('pointerdown', function (e) { drag = true; lx = e.clientX; cv.setPointerCapture(e.pointerId); });
      cv.addEventListener('pointermove', function (e) { if (drag) { az -= (e.clientX - lx) * 0.008; lx = e.clientX; } });
      ['pointerup', 'pointercancel'].forEach(function (n) { cv.addEventListener(n, function () { drag = false; }); });
      cv.addEventListener('wheel', function (e) {
        e.preventDefault();
        zoom = Math.max(0.6, Math.min(1.6, zoom * (1 + e.deltaY * 0.001)));
      }, { passive: false });

      function resize() {
        var w = host.clientWidth, h = host.clientHeight;
        renderer.setSize(w, h, false);
        cam.aspect = w / h;
        cam.updateProjectionMatrix();
      }
      if (window.ResizeObserver) new ResizeObserver(resize).observe(host); else window.addEventListener('resize', resize);
      if (window.IntersectionObserver) new IntersectionObserver(function (en) { onscreen = en[0].isIntersecting; }).observe(host);
      resize();

      var last = performance.now();
      function frame(now) {
        requestAnimationFrame(frame);
        var dt = Math.min((now - last) / 1000, 0.1);
        last = now;
        if (!onscreen) return;
        if (!drag && !calm) az += 0.12 * dt;
        earth1.userData.earth.rotation.y += 0.02 * dt;
        earth1.userData.clouds.rotation.y += 0.026 * dt;
        earth2.userData.earth.rotation.y += 0.02 * dt;
        earth2.userData.clouds.rotation.y += 0.026 * dt;
        if (mode === 'orbit') {
          ang += 0.7 * dt;
          sat.position.set(0, OR * Math.cos(ang), OR * Math.sin(ang));
          sat.rotation.x = ang;
        }
        if (mode === 'survey' && playing) setMonth(month + dt / 2 > 6 ? 0 : month + dt / 2);
        rad += (BASE[mode] * zoom - rad) * 0.08;
        cam.position.set(rad * Math.cos(el) * Math.sin(az), rad * Math.sin(el), rad * Math.cos(el) * Math.cos(az));
        cam.lookAt(0, 0, 0);
        renderer.render(scene, cam);
      }
      setMode('orbit');
      setMonth(0);
      requestAnimationFrame(frame);
    })();
  </script>
</body>
</html>
"""


@app.route("/")
def home():
    bands = build_bands()
    ticks = [
        {"label": label, "left": round((band_index(bands, c) + 0.5) / len(bands) * 100, 1)}
        for label, _n, c, _h in ICES
    ]
    return render_template_string(
        PAGE, title=TITLE, full_name=FULL_NAME, lead=LEAD, modes=MODES, bands=bands,
        ticks=ticks, default_index=band_index(bands, ICES[0][2]), goals=GOALS, parts=PARTS,
        numbers=NUMBERS, neighbors=NEIGHBORS, timeline=TIMELINE, links=LINKS,
        disclaimer=DISCLAIMER,
    )


@app.route("/explorer")
def explorer():
    return render_template("explorer.html")


@app.route("/tracker")
def tracker():
    return render_template("tracker.html")


@app.route("/geography/<path:filename>")
def geography_file(filename):
    safe_name = Path(filename).name
    if safe_name not in GEOGRAPHY_FILES:
        return {"error": "Geographic dataset not found"}, 404
    return send_from_directory(GEOGRAPHY_DIR, safe_name)


@app.route("/api/<path:api_path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
def proxy_api(api_path):
    api_base = API_BASE_URL
    if not api_base and request.environ.get("SERVER_PORT") in {"5000", "5001", "5050"}:
        hostname = urlsplit(request.host_url).hostname
        api_base = f"{request.scheme}://{hostname}:8000" if hostname else ""
    if not api_base:
        return {"error": "Analysis API is not configured"}, 503

    upstream_url = f"{api_base}/api/{api_path}"
    if request.query_string:
        upstream_url += f"?{request.query_string.decode('latin-1')}"
    headers = {
        key: value for key, value in request.headers
        if key.lower() in {"accept", "authorization", "content-type"}
    }
    try:
        upstream = requests.request(
            request.method,
            upstream_url,
            headers=headers,
            data=request.get_data(),
            timeout=60,
            allow_redirects=False,
        )
    except requests.RequestException:
        app.logger.exception("Analysis API proxy request failed")
        return {"error": "Could not reach the analysis API"}, 502

    response_headers = {
        key: upstream.headers[key]
        for key in ("Content-Type", "Cache-Control", "Content-Disposition", "ETag", "Last-Modified")
        if key in upstream.headers
    }
    return Response(upstream.content, status=upstream.status_code, headers=response_headers)


@app.route("/fits")
def fits_viewer():
    return render_template("fits_viewer.html")


if __name__ == "__main__":
    # host="0.0.0.0" lets other devices on your Wi-Fi open the site too.
    app.run(host="0.0.0.0", debug=False)
