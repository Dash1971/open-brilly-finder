#!/usr/bin/env python3
"""Local receiver: the Chess.com tab posts each captured review here; saved as ccreview/<game_id>.json"""
import json, os, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ccreview')

RELAY = b"""<!doctype html><meta charset=utf-8><title>brilly relay</title><body style="font:14px sans-serif">
<p>Brilly relay: keep this tab open while reviews are collected.</p><p id=s>waiting</p>
<script>
let n=0;
addEventListener('message',async e=>{
  if(e.origin!=='https://www.chess.com'||!e.data||!e.data.id)return;
  let ok=false;
  try{const r=await fetch('/save/'+e.data.id,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(e.data.data)});ok=r.status===200}catch(err){}
  if(ok)n++;document.getElementById('s').textContent='saved '+n;
  e.source.postMessage({ack:e.data.id,ok},e.origin);
});
if(window.opener)window.opener.postMessage({relayReady:true},'https://www.chess.com');
</script>"""

class H(BaseHTTPRequestHandler):
    timeout = 20
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', 'https://www.chess.com')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'content-type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path.startswith('/relay'):
            self.send_response(200); self.send_header('content-type', 'text/html'); self.end_headers(); self.wfile.write(RELAY); return
        n = len([f for f in os.listdir(OUT) if f.endswith('.json')])
        self.send_response(200); self._cors(); self.send_header('content-type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps({'saved': n}).encode())
    def do_POST(self):
        n = int(self.headers.get('content-length', 0))
        body = self.rfile.read(n) if 0 < n < 400_000_000 else b''
        if self.path.startswith('/bulk'):
            saved = 0
            try:
                txt = body.decode('utf-8', 'replace')
                if txt.startswith('d='): txt = txt[2:]
                for gid, val in json.loads(txt.strip()).items():
                    if re.fullmatch(r'\d{6,20}', gid):
                        with open(os.path.join(OUT, gid + '.json'), 'w') as f: json.dump(val, f)
                        saved += 1
            except Exception as e:
                saved = -1
            self.send_response(200); self.send_header('content-type', 'text/html'); self.end_headers()
            self.wfile.write(('<title>saved %d</title><p id=s>saved %d</p>' % (saved, saved)).encode()); return
        m = re.fullmatch(r'/save/(\d{6,20})', self.path)
        ok = False
        if m and body:
            try:
                json.loads(body)
                with open(os.path.join(OUT, m.group(1) + '.json'), 'wb') as f: f.write(body)
                ok = True
            except Exception: pass
        self.send_response(200 if ok else 400); self._cors(); self.end_headers(); self.wfile.write(b'ok' if ok else b'bad')
    def log_message(self, *a): pass
ThreadingHTTPServer(('127.0.0.1', 8765), H).serve_forever()
