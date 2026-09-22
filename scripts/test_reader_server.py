import tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from start_reader import ReaderHandler
class ServerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);(root/'index.html').write_text('demo');(root/'books.json').write_text('private');(root/'reader/pdfjs').mkdir(parents=True);(root/'reader/pdfjs/test.mjs').write_text('export const x=1;')
  self.server=ThreadingHTTPServer(('127.0.0.1',0),partial(ReaderHandler,directory=str(root)));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def get(self,path,host=None):
  r=urllib.request.Request(self.url+path,headers={'Host':host} if host else {})
  try:
   with urllib.request.urlopen(r) as f:return f.status,f.headers,f.read()
  except urllib.error.HTTPError as e:return e.code,e.headers,e.read()
 def test_main(self):self.assertEqual(self.get('/')[0],200)
 def test_module_mime(self):self.assertEqual(self.get('/reader/pdfjs/test.mjs')[1]['Content-Type'],'text/javascript')
 def test_materials_not_served(self):self.assertEqual(self.get('/books.json')[0],404)
 def test_directory_listing_blocked(self):self.assertIn(self.get('/reader/pdfjs/')[0],(403,404))
 def test_path_escape(self):self.assertNotEqual(self.get('/reader/pdfjs/../../books.json')[0],200)
 def test_host_boundary(self):self.assertEqual(self.get('/', 'example.com')[0],403)
if __name__=='__main__':unittest.main()
