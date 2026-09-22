#!/usr/bin/env python3
"""Serve only the generated guide and its PDF renderer on this computer."""
import argparse, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

class ReaderHandler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm'}
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403);return
        path=unquote(urlsplit(self.path).path)
        if '..' in path.split('/') or '\\' in path:
            self.send_error(403);return
        if path in ('/','/index.html'): pass
        elif not path.startswith('/reader/pdfjs/'):
            self.send_error(404);return
        root=Path(self.directory).resolve(); target=Path(self.translate_path(self.path)).resolve()
        if root not in target.parents and target!=root:
            self.send_error(403);return
        if path.startswith('/reader/pdfjs/') and root/'reader/pdfjs' not in target.parents:
            self.send_error(403);return
        if target.is_dir() and target!=root:
            self.send_error(404);return
        super().do_GET()
    def do_HEAD(self):
        self.send_error(405)
    def list_directory(self,path):
        self.send_error(404)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',default=str(Path(__file__).resolve().parent));p.add_argument('--port',type=int,default=8880);a=p.parse_args()
    root=Path(a.directory).resolve()
    if not (root/'index.html').is_file():p.error('目录内没有 index.html，请在生成的网页目录运行。')
    try:
        server=ThreadingHTTPServer(('127.0.0.1',a.port),partial(ReaderHandler,directory=str(root)))
    except OSError:p.error('端口不可用：请关闭原来的启动窗口，或使用 --port 指定端口。换端口后浏览器记录不共享。')
    print(f'打开 http://127.0.0.1:{server.server_port}/ ，保留此窗口，按 Ctrl+C 停止。',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
