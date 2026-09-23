#!/usr/bin/env python3
"""Serve only the generated guide and its PDF renderer on this computer."""
import argparse, json, secrets, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from ebook_import import parse_book, MAX_UPLOAD

class ReaderHandler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm'}
    def local_request(self):
        host=self.headers.get('Host')
        if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403);return False
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{host}':
            self.send_error(403);return False
        return True
    def json_reply(self,status,data):
        raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if not self.local_request():return
        path=unquote(urlsplit(self.path).path)
        if path=='/api/status':
            self.json_reply(200,{'available':True,'token':self.server.token});return
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
    def do_POST(self):
        if not self.local_request():return
        parts=urlsplit(self.path)
        if parts.path!='/api/import-book' or self.headers.get('X-Book-Token')!=self.server.token:
            self.send_error(403);return
        if self.headers.get('Content-Type')!='application/octet-stream':
            self.send_error(415);return
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:n=0
        if n<1 or n>MAX_UPLOAD:
            self.json_reply(413,{'error':'文件为空或超过 60 MB，请分卷后添加。'});return
        ext=parse_qs(parts.query).get('format',[''])[0]
        try:self.json_reply(200,parse_book(self.rfile.read(n),ext))
        except ValueError as error:self.json_reply(422,{'error':str(error)})
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
    server.token=secrets.token_urlsafe(32)
    print(f'打开 http://127.0.0.1:{server.server_port}/ ，保留此窗口，按 Ctrl+C 停止。',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
