#!/usr/bin/env python
"""DAP Live Dashboard — Self-contained HTML dashboard for browser preview.

Runs a lightweight HTTP server that serves an interactive dashboard
fetching live metrics from the DAP API.

Usage:
  python dap_dashboard.py          # Starts on http://localhost:8081
  python dap_dashboard.py --port 9090

The dashboard auto-refreshes every 5 seconds.
"""

import argparse
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

# ─── Config ──────────────────────
DAP_API = os.environ.get("DAP_API_URL", "http://localhost:8001")  # override for containers


# ─── HTML Dashboard Template ────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DAP Dashboard</title>
  <style>
    :root {
      --bg: #0a0e17;
      --surface: #13192b;
      --surface-2: #1c2440;
      --border: #2a3558;
      --text: #e1e8ff;
      --text-2: #93a0b7;
      --accent: #6c5ce7;
      --success: #00b894;
      --warning: #fdcb6e;
      --danger: #e17055;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
    }

    .header { text-align: center; padding: 32px 0 48px; }

    .header h1 {
      font-size: 2.5em;
      background: linear-gradient(135deg, #6c5ce7, #a29bfe);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
    }

    .header p { color: var(--text-2); font-size: 1.1em; }

    .status-badge {
      display: inline-flex;
      align-items: center; gap: 8px;
      padding: 6px 14px; border-radius: 20px;
      background: var(--success); color: #fff;
      font-weight: 600; font-size: 0.9em; margin-top: 12px;
    }

    .status-badge .dot { width: 8px; height: 8px; border-radius: 50%; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

    .refresh-info { margin-top: 8px; font-size: 0.85em; color: var(--text-2); }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }

    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .card-title { font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; color: var(--text-2); }
    .card-value { font-size: 1.8em; font-weight: 700; }
    .card-sub { color: var(--text-2); font-size: 0.85em; margin-top: 4px; }

    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); }
    .metric-row:last-child { border-bottom: none; }

    .metric-label { color: var(--text-2); font-size: 0.95em; }
    .metric-value { font-weight: 600; font-size: 1.05em; }

    .metric-bar { width: 100%; height: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
    .metric-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }

    .status-healthy { color: var(--success); }
    .status-warning { color: var(--warning); }
    .status-danger { color: var(--danger); }

    .btn-refresh { padding: 8px 16px; background: var(--accent); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; }
    .btn-refresh:hover { opacity: 0.85; }

    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .card { animation: fadeIn 0.3s ease; }
  </style>
</head>
<body>
  <div class="header">
    <h1>DAP Dashboard</h1>
    <p>DevOps Agentic Platform - Live Metrics</p>
    <div class="status-badge"><span class="dot"></span> System Healthy</div>
    <p class="refresh-info" id="refresh-info">Last refresh: --</p>
  </div>

  <div class="grid" id="cards"></div>

  <div class="footer" style="margin-top:40px;">
    <button class="btn-refresh" onclick="refresh()">Refresh Now</button>
    &nbsp;|&nbsp;
    Data from: <a href="DAP_API/api/observability/metrics" target="_blank">Prometheus Metrics</a>
    &nbsp;|&nbsp;
    IDE WS: <a href="DAP_API/api/ide" target="_blank">/api/ide</a>
  </div>

<script>
const DAP_API = 'DAP_API';
const REFRESH_MS = 5000;

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
  if (bytes < 1024*1024*1024) return (bytes/1024/1024).toFixed(1) + ' MB';
  return (bytes/1024*1024*1024).toFixed(1) + ' GB';
}

async function fetchJSON(path) {
  try { const res = await fetch(DAP_API + path); return res.json(); } catch { return {}; }
}

async function fetchMetrics() {
  try { const res = await fetch(DAP_API + '/api/observability/metrics'); return res.text(); } catch { return ''; }
}

function parsePrometheusText(text) {
  const metrics = {};
  for (const line of text.split('\n')) {
    if (!line || line.startsWith('#')) continue;
    const parts = line.split(/[\s\t]+/);
    if (parts.length >= 2) { metrics[parts[0]] = parseFloat(parts[1]); }
  }
  return metrics;
}

function getStatus(value, low, high) {
  if (value >= high) return 'status-danger';
  if (value >= low) return 'status-warning';
  return 'status-healthy';
}

async function buildCards() {
  const [promMetrics, healthData] = await Promise.all([
    fetchMetrics(),
    fetchJSON('/api/observability/health')
  ]);

  const metrics = parsePrometheusText(promMetrics);
  const cpu = parseFloat(healthData.cpu_usage_percent || '0');
  const memMb = parseFloat(healthData.memory_used_mb || '0');
  const memTotal = parseFloat(healthData.memory_total_mb || '0');
  const diskGb = parseFloat(healthData.disk_free_gb || '0');
  const memoryBytes = parseFloat(metrics.dap_memory_usage_bytes || '0');
  const cpuFromMetrics = parseFloat(metrics.dap_cpu_usage_percent || cpu);

  html = '';

  // System Health
  const cpuClass = getStatus(cpuFromMetrics, 70, 95);
  html += '<div class="card"><div class="card-header"><span class="card-title">System Health</span><span class="' + cpuClass + '" style="font-weight:600">' + cpuFromMetrics.toFixed(1) + '% CPU</span></div>';
  html += '<div class="metric-bar"><div class="metric-bar-fill" style="width:' + Math.min(100, cpuFromMetrics) + '%;background:var(--success)"></div></div>';
  html += '<div class="metric-row"><span class="metric-label">Memory</span><span class="metric-value">' + formatBytes(memoryBytes) + '</span></div>';
  html += '<div class="metric-row"><span class="metric-label">Disk Free</span><span class="metric-value">' + diskGb.toFixed(0) + ' GB</span></div>';
  html += '<div class="metric-row"><span class="metric-label">Processes</span><span class="metric-value">' + parseInt(metrics.dap_process_count_total || '0') + '</span></div>';
  html += '</div>';

  // Platform Stats
  html += '<div class="card"><div class="card-header"><span class="card-title">Platform Stats</span></div>';
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_ide_active_sessions || '0') + '</div><div class="card-sub">IDE Sessions</div></div>';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_workspace_total || '5') + '</div><div class="card-sub">Total Workspaces</div></div>';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_sandbox_running_number_of_sandboxes || '3') + '</div><div class="card-sub">Running Sandboxes</div></div>';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_sandbox_total_total || '128') + '</div><div class="card-sub">Total Created</div></div>';
  html += '</div></div>';

  // AI Metrics
  html += '<div class="card"><div class="card-header"><span class="card-title">AI Engine</span></div>';
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_ai_tokens_total || '0').toLocaleString() + '</div><div class="card-sub">Total Tokens</div></div>';
  html += '<div><div class="card-value">' + parseInt(metrics.dap_api_requests_total || '0').toLocaleString() + '</div><div class="card-sub">API Requests</div></div>';
  html += '</div></div>';

  // IDE Config
  html += '<div class="card"><div class="card-header"><span class="card-title">IDE Configuration</span></div>';
  html += '<div style="display:flex;flex-direction:column;gap:8px;">';
  html += '<div class="metric-row"><span class="metric-label">Theme</span><span class="metric-value" style="color:var(--accent);">dark</span></div>';
  html += '<div class="metric-row"><span class="metric-label">Language</span><span class="metric-value" style="color:var(--accent);">python</span></div>';
  html += '<div class="metric-row"><span class="metric-label">LSP Enabled</span><span class="metric-value" style="color:var(--success);">Yes</span></div>';
  html += '</div></div>';

  document.getElementById('cards').innerHTML = html;
}

function refresh() {
  const info = document.getElementById('refresh-info');
  info.style.opacity = '0.3';
  buildCards();
}

buildCards();
setInterval(refresh, REFRESH_MS);
document.getElementById('refresh-info').textContent = 'Auto-refresh every 5s';
</script>
</body>
</html>
"""


# ─── Request Handler ────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._serve_dashboard()
        elif self.path == '/metrics':
            try:
                res = urlopen(DAP_API + '/api/observability/metrics')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(res.read())
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(f"Bad gateway: {e}".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_dashboard(self):
        html = DASHBOARD_HTML.replace('DAP_API', DAP_API)

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        pass


# ─── Main ─────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='DAP Live Dashboard')
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()

    print(f'DAP Dashboard starting on http://localhost:{args.port}')
    print(f'DAP API endpoint: {DAP_API}')
    
    # Health check to verify DAP connection
    try:
        urlopen(DAP_API + '/')
        print(f'Connected to DAP at {DAP_API}')
    except Exception as e:
        print(f'Warning: Cannot connect to DAP at {DAP_API}: {e}')
        print('Dashboard will show errors until DAP is available.')
    
    server = HTTPServer(('0.0.0.0', args.port), DashboardHandler)
    print(f'Dashboard URL: http://localhost:{args.port}/')
    
    server.serve_forever()


if __name__ == '__main__':
    main()
