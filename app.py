#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cosmic Vibe - daily news distilled into one snarky sentence."""


import json
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
from flask import Flask, jsonify

import ollama

MODEL = "llama3.2:latest"   # swap to "gemma4:latest" for more creative output (slower)

OLLAMA_HOST = "http://localhost:11434"

app = Flask(__name__)

# ── HTML / CSS / JS ───────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cosmic Vibe</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500&family=Space+Mono&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      height: 100%;
      overflow: hidden;
    }

    body {
      background: #000;
      color: #fff;
      font-family: 'Space Grotesk', system-ui, sans-serif;
    }

    canvas#stars {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
    }

    #app {
      position: relative;
      z-index: 1;
      height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      gap: 1.5rem;
    }

    /* ── Orb ──────────────────────────────────────────────────────────────── */
    #orb-wrap {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.95s cubic-bezier(0.34, 1.35, 0.64, 1);
      flex-shrink: 0;
    }
    #orb-wrap.lifted { transform: translateY(-30px); }

    #spinner {
      position: absolute;
      width: 314px;
      height: 314px;
      border-radius: 50%;
      border: 2px solid transparent;
      border-top-color: rgba(160, 195, 255, 0.9);
      border-right-color: rgba(160, 195, 255, 0.3);
      opacity: 0;
      transition: opacity 0.4s ease;
      pointer-events: none;
      will-change: transform;
    }
    #spinner.active {
      opacity: 1;
      animation: spin 1.35s linear infinite;
    }

    #orb {
      width: 286px;
      height: 286px;
      border-radius: 50%;
      background: radial-gradient(circle at 38% 36%,
        rgba(140, 175, 255, 0.13) 0%,
        rgba(90, 130, 230, 0.08) 45%,
        rgba(50, 80, 200, 0.04) 75%,
        transparent 100%);
      border: 1.5px solid rgba(140, 175, 255, 0.3);
      box-shadow:
        0 0 50px rgba(100, 145, 255, 0.2),
        0 0 100px rgba(80, 120, 240, 0.09),
        inset 0 0 55px rgba(110, 150, 255, 0.05);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.25rem;
      animation: orb-pulse 4.5s ease-in-out infinite;
      transition: box-shadow 0.35s ease, border-color 0.35s ease;
      user-select: none;
      -webkit-tap-highlight-color: transparent;
      outline: none;
    }

    #orb:hover {
      box-shadow:
        0 0 70px rgba(100, 145, 255, 0.36),
        0 0 140px rgba(80, 120, 240, 0.15),
        inset 0 0 65px rgba(110, 150, 255, 0.09);
      border-color: rgba(165, 200, 255, 0.55);
    }

    #orb.loading {
      animation: none;
      cursor: wait;
    }

    @keyframes orb-pulse {
      0%, 100% {
        box-shadow:
          0 0 50px rgba(100, 145, 255, 0.20),
          0 0 100px rgba(80, 120, 240, 0.09),
          inset 0 0 55px rgba(110, 150, 255, 0.05);
        transform: scale(1);
      }
      50% {
        box-shadow:
          0 0 75px rgba(100, 145, 255, 0.36),
          0 0 150px rgba(80, 120, 240, 0.15),
          inset 0 0 75px rgba(110, 150, 255, 0.09);
        transform: scale(1.022);
      }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    #orb-date {
      font-size: 0.7rem;
      font-weight: 300;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: rgba(185, 210, 255, 0.55);
    }

    #orb-time {
      font-family: 'Space Mono', monospace;
      font-size: 2.1rem;
      color: rgba(220, 238, 255, 0.92);
      letter-spacing: 0.04em;
    }

    #orb-hint {
      font-size: 0.6rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: rgba(135, 170, 255, 0.42);
      margin-top: 0.35rem;
      transition: opacity 0.4s ease;
    }

    #orb-status {
      font-size: 0.62rem;
      letter-spacing: 0.13em;
      text-transform: uppercase;
      color: rgba(155, 190, 255, 0.65);
      margin-top: 0.35rem;
      opacity: 0;
      transition: opacity 0.4s ease;
      min-height: 1em;
    }

    #orb.loading #orb-hint   { opacity: 0; }
    #orb.loading #orb-status { opacity: 1; }

    /* ── Result ───────────────────────────────────────────────────────────── */
    #result {
      max-width: 680px;
      width: 100%;
      max-height: 0;
      opacity: 0;
      overflow: hidden;
      transition:
        max-height 0.95s cubic-bezier(0.34, 1.05, 0.64, 1),
        opacity   0.7s ease 0.35s;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    #result.visible {
      max-height: 42vh;
      opacity: 1;
      pointer-events: auto;
    }

    #result-scroll {
      width: 100%;
      max-height: 36vh;
      overflow-y: auto;
      text-align: center;
      padding: 0.5rem 1.2rem 0.5rem 0.8rem;
      scrollbar-width: thin;
      scrollbar-color: rgba(150, 185, 255, 0.3) transparent;
    }
    #result-scroll::-webkit-scrollbar { width: 6px; }
    #result-scroll::-webkit-scrollbar-track { background: transparent; }
    #result-scroll::-webkit-scrollbar-thumb {
      background: rgba(150, 185, 255, 0.22);
      border-radius: 3px;
    }
    #result-scroll::-webkit-scrollbar-thumb:hover {
      background: rgba(150, 185, 255, 0.5);
    }

    #sentence {
      font-size: clamp(1rem, 2.4vw, 1.35rem);
      font-weight: 400;
      font-style: italic;
      line-height: 1.6;
      color: rgba(225, 238, 255, 0.95);
      text-shadow: 0 0 45px rgba(100, 145, 255, 0.22);
      margin-bottom: 1.8rem;
      padding: 0 0.5rem;
    }

    #refs-label {
      font-size: 0.56rem;
      letter-spacing: 0.24em;
      text-transform: uppercase;
      color: rgba(125, 160, 255, 0.32);
      margin-bottom: 1rem;
    }

    #refs-list {
      display: flex;
      flex-direction: column;
      gap: 0.7rem;
      text-align: left;
    }

    .ref {
      padding: 0.55rem 1rem;
      border-left: 1px solid rgba(100, 145, 255, 0.22);
      transition: border-color 0.2s ease;
    }
    .ref:hover { border-color: rgba(155, 190, 255, 0.5); }

    .ref-title {
      font-size: 0.77rem;
      color: rgba(195, 215, 255, 0.7);
      margin-bottom: 0.22rem;
      line-height: 1.4;
    }

    .ref-url {
      font-size: 0.63rem;
      color: rgba(105, 150, 255, 0.42);
      text-decoration: none;
      word-break: break-all;
    }
    .ref-url:hover { color: rgba(150, 185, 255, 0.72); }

    #again-btn {
      display: none;
      margin-top: 1rem;
      padding: 0.45rem 1.5rem;
      background: rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(4px);
      border: 1px solid rgba(130, 165, 255, 0.22);
      color: rgba(135, 170, 255, 0.6);
      border-radius: 99px;
      cursor: pointer;
      font-family: inherit;
      font-size: 0.62rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      transition: border-color 0.2s ease, color 0.2s ease;
      flex-shrink: 0;
    }
    #again-btn:hover {
      border-color: rgba(155, 190, 255, 0.5);
      color: rgba(175, 205, 255, 0.85);
    }
  </style>
</head>
<body>

<canvas id="stars"></canvas>

<div id="app">
  <div id="orb-wrap">
    <div id="spinner"></div>
    <div id="orb" role="button" tabindex="0" aria-label="Reveal today's vibe">
      <div id="orb-date"></div>
      <div id="orb-time"></div>
      <div id="orb-hint">tap to reveal today's vibe</div>
      <div id="orb-status">scanning the cosmos</div>
    </div>
  </div>

  <div id="result">
    <div id="result-scroll">
      <p id="sentence"></p>
      <div id="refs-label"></div>
      <div id="refs-list"></div>
    </div>
    <button id="again-btn" onclick="resetApp()">&larr; scan again</button>
  </div>
</div>

<script>
"use strict";

// ── Stars ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById('stars');
const ctx    = canvas.getContext('2d');
let stars    = [];

function resize() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  spawnStars();
}

function spawnStars() {
  const n = Math.round((canvas.width * canvas.height) / 6800);
  stars = Array.from({ length: n }, () => ({
    x:     Math.random() * canvas.width,
    y:     Math.random() * canvas.height,
    r:     Math.random() * 1.1 + 0.15,
    o:     Math.random() * 0.7 + 0.08,
    speed: (Math.random() * 0.016 + 0.003) * (Math.random() < 0.5 ? 1 : -1),
    blue:  Math.random() > 0.72,
  }));
}

function drawStars() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (const s of stars) {
    s.o += s.speed;
    if (s.o > 0.88 || s.o < 0.04) s.speed *= -1;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, 6.2832);
    ctx.fillStyle = s.blue
      ? `rgba(185,210,255,${s.o})`
      : `rgba(255,255,255,${s.o})`;
    ctx.fill();
  }
  requestAnimationFrame(drawStars);
}

resize();
drawStars();
window.addEventListener('resize', resize);

// ── Clock ──────────────────────────────────────────────────────────────────
const dateEl = document.getElementById('orb-date');
const timeEl = document.getElementById('orb-time');

function tick() {
  const now = new Date();
  dateEl.textContent = now.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  });
  timeEl.textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  });
}
tick();
setInterval(tick, 1000);

// ── State machine ──────────────────────────────────────────────────────────
let busy = false;

const orb       = document.getElementById('orb');
const spinner   = document.getElementById('spinner');
const orbWrap   = document.getElementById('orb-wrap');
const result    = document.getElementById('result');
const statusEl  = document.getElementById('orb-status');
const againBtn  = document.getElementById('again-btn');

orb.addEventListener('click',   generate);
orb.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') generate(); });

const STATUS_PHRASES = [
  'scanning the cosmos',
  'reading between the headlines',
  'sifting through the noise',
  'consulting the oracle',
  'distilling the chaos',
  'summarising humanity’s choices',
];

let phraseInterval = null;

function cycleStatus() {
  let i = 0;
  phraseInterval = setInterval(() => {
    i = (i + 1) % STATUS_PHRASES.length;
    statusEl.textContent = STATUS_PHRASES[i];
  }, 2600);
}

async function generate() {
  if (busy) return;
  busy = true;

  orb.classList.add('loading');
  spinner.classList.add('active');
  statusEl.textContent = STATUS_PHRASES[0];
  cycleStatus();

  try {
    const res = await fetch('/generate', { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showResult(data);
  } catch (err) {
    showResult({
      sentence: 'The cosmos refused to speak. Try again.',
      references: []
    });
  }
}

function showResult(data) {
  clearInterval(phraseInterval);
  orb.classList.remove('loading');
  spinner.classList.remove('active');

  // Populate sentence
  document.getElementById('sentence').textContent =
    '“' + (data.sentence || 'No vibe detected.') + '”';

  // Populate references
  const refsList = document.getElementById('refs-list');
  const refsLabel = document.getElementById('refs-label');
  refsList.innerHTML = '';

  const refs = (data.references || [])
    .filter(r => r.title || r.url)
    .slice(0, 8);

  if (refs.length) {
    refsLabel.textContent = 'sources from the void';
    refs.forEach(ref => {
      const div = document.createElement('div');
      div.className = 'ref';

      const titleDiv = document.createElement('div');
      titleDiv.className = 'ref-title';
      titleDiv.textContent = ref.title || 'Untitled';
      div.appendChild(titleDiv);

      if (ref.url) {
        const a = document.createElement('a');
        a.className = 'ref-url';
        a.href      = ref.url;
        try {
          const u = new URL(ref.url);
          a.textContent = u.hostname.replace(/^www\./, '') + ' ↗';
        } catch (_) {
          a.textContent = ref.url;
        }
        a.target = '_blank';
        a.rel    = 'noopener noreferrer';
        div.appendChild(a);
      }

      refsList.appendChild(div);
    });
  }

  againBtn.style.display = 'inline-block';

  // Animate: lift orb, then fade in result
  orbWrap.classList.add('lifted');
  setTimeout(() => result.classList.add('visible'), 380);
}

function resetApp() {
  busy = false;
  result.classList.remove('visible');
  orbWrap.classList.remove('lifted');
  againBtn.style.display = 'none';

  setTimeout(() => {
    document.getElementById('sentence').textContent  = '';
    document.getElementById('refs-list').innerHTML   = '';
    document.getElementById('refs-label').textContent = '';
  }, 950);
}
</script>
</body>
</html>
"""

# ── Web search tool ───────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 8) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
            if not results:
                results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        return [{"title": f"Search unavailable: {e}", "href": "", "body": ""}]


# ── Agent ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a delightfully snarky AI journalist who distills the day's news into ONE perfectly crafted sentence. "
    "You have a sharp wit, a dark sense of humour, and zero patience for the absurdity of the modern world - "
    "but you show up anyway, coffee in hand, and deliver. "
    "You will be given today's actual news headlines. Read them, then synthesise the collective mood "
    "into a single punchy, eye-catching sentence that captures today's vibe. "
    "Reference real events from the headlines - do not invent news. "
    "Be clever. Be irreverent. Be unforgettable. "
    "Respond with ONLY the snarky sentence - no preamble, no explanation, no quotation marks."
)

# Topics we always search to guarantee a broad reference base
SEED_TOPICS = [
    "top news today",
    "world news today",
    "technology news today",
    "politics news today",
]


def gather_headlines() -> tuple[list[dict], list[dict]]:
    """Run the seed searches. Returns (references, headline_summaries)."""
    references: list[dict] = []
    seen_urls: set[str] = set()
    headlines: list[dict] = []

    for topic in SEED_TOPICS:
        for r in web_search(topic, max_results=5):
            url = r.get("url") or r.get("href") or ""
            title = r.get("title", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            references.append({"title": title, "url": url})
            headlines.append({
                "title": title,
                "snippet": (r.get("body") or r.get("snippet") or "")[:240],
                "source": r.get("source", ""),
            })

    return references, headlines


def run_agent() -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")

    # 1. Always gather real headlines first - guarantees references exist
    references, headlines = gather_headlines()

    if not headlines:
        return {
            "sentence": "The internet went silent today. Suspicious.",
            "references": references,
        }

    headlines_text = "\n".join(
        f"- {h['title']}" + (f" ({h['snippet'][:140]}...)" if h['snippet'] else "")
        for h in headlines[:20]
    )

    # 2. Hand real headlines to the model and let it craft the sentence
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Today is {today}. Here are the actual news headlines from across the web right now:\n\n"
                f"{headlines_text}\n\n"
                "Now give me your single snarky sentence that captures the collective vibe of these headlines. "
                "Reference real things from above. One sentence only. No quotation marks."
            )
        }
    ]

    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(model=MODEL, messages=messages)
    sentence = (response.message.content or "").strip().strip('"').strip("'").strip()

    # Tidy up: take only the first sentence if the model rambled
    if sentence:
        for terminator in ['\n', '. ']:
            if terminator in sentence:
                first, rest = sentence.split(terminator, 1)
                if len(first) > 40:  # avoid splitting on abbreviations
                    sentence = first + ('.' if terminator == '. ' else '')
                    break

    return {
        "sentence": sentence or "The universe shrugged. Check back tomorrow.",
        "references": references[:12],
    }


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML


@app.route("/generate", methods=["POST"])
def generate():
    try:
        return jsonify(run_agent())
    except Exception as e:
        return jsonify({
            "sentence": f"The oracle malfunctioned ({type(e).__name__}). Try again.",
            "references": [],
        }), 500


if __name__ == "__main__":
    print(f"\n  Cosmic Vibe  ->  http://localhost:5000   (model: {MODEL})\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
