const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..', '..');
const staticDir = path.join(projectRoot, 'static');
const templatePath = path.join(projectRoot, 'templates', 'index.html');

// JS MUST EXIST
const jsDir = path.join(staticDir, 'js');
if (!fs.existsSync(jsDir)) {
  console.error('static/js/ NOT FOUND!');
  process.exit(1);
}

const jsFiles = fs.readdirSync(jsDir).filter(f => f.startsWith('main.') && f.endsWith('.js'));
if (jsFiles.length === 0) {
  console.error('MAIN JS NOT FOUND!');
  process.exit(1);
}

const jsFile = jsFiles[0];

// CSS IS OPTIONAL
let cssFile = '';
const cssDir = path.join(staticDir, 'css');
if (fs.existsSync(cssDir)) {
  cssFile = fs.readdirSync(cssDir).find(f => f.startsWith('main.') && f.endsWith('.css')) || '';
}

// Write index.html
const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>QUANTUMTRADER PRO v7.1</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}" />
  ${cssFile ? `<link rel="stylesheet" href="{{ url_for('static', filename='css/${cssFile}') }}" />` : ''}
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:#0a0a0a; font-family:'Courier New',monospace; color:#fff; overflow:hidden; }
    #loading { position:fixed; inset:0; background:#0a0a0a; display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:9999; transition:opacity 1s ease-out; }
    .glow { text-shadow:0 0 30px #00d4ff, 0 0 60px #7c3aed; }
    .pulse { animation:pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.7; transform:scale(1.05); } }
    .gradient-text { background: linear-gradient(90deg, #00d4ff, #7c3aed); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold; }
  </style>
</head>
<body>
  <div id="loading">
    <div class="glow pulse gradient-text" style="font-size:3.8rem; letter-spacing:2px;">QUANTUMTRADER PRO</div>
    <div style="color:#00d4ff; margin:20px; font-size:1.3rem;">Neural Engine v7.1</div>
    <div style="color:#0f0; font-size:1rem; margin:8px;">WEBSOCKET SECURE</div>
    <div style="color:#0f0; font-size:1rem; margin:8px;">REAL MODE ARMED</div>
    <div style="color:#0f0; font-size:1rem; margin:8px;">AI PREDICTOR LOADED</div>
    <div style="color:#ff9100; font-size:0.9rem; margin-top:30px; opacity:0.8;">Initializing in 2.8s...</div>
  </div>
  <div id="root"></div>
  <script src="{{ url_for('static', filename='js/${jsFile}') }}"></script>
  <script>
    window.addEventListener('load', () => {
      setTimeout(() => {
        const l = document.getElementById('loading');
        if (l) { l.style.opacity = '0'; setTimeout(() => l.remove(), 1000); }
      }, 2800);
    });
    setTimeout(() => { const l = document.getElementById('loading'); if (l) l.remove(); }, 10000);
  </script>
</body>
</html>`;

fs.writeFileSync(templatePath, html);
console.log(`INJECTED: js/${jsFile}${cssFile ? ` + css/${cssFile}` : ' (NO CSS)'}`);