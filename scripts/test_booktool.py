"""Synthetic fixtures only; never reads a user's books or browser state."""
import copy, json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import booktool as b

SOURCE={'id':'demo-quiet','title':'慢慢读，也是一种抵达','format':'txt','warnings':[], 'units':[{'id':1,'label':'第一章 · 从一页开始','text':'小林把一本厚书放在桌上，每次只读一页。读完一页，也是一段自己的时间。'}, {'id':2,'label':'第二章 · 留一个问题','text':'她在书签上写下一个问题，第二天回来寻找答案。书签不是终点，是下次出发的地方。'}]}
def fixture():
    a={'title':'先留一点时间','text':'小林不再按页数衡量自己，而是给阅读留出一小段时间。','units':[1]}
    c={'title':'带着问题回来','text':'她把未解的问题写在书签上，给下一次阅读留一个入口。','units':[2]}
    return {'title':SOURCE['title'],'author':'一页读书 · 原创验收短文','intro':'从一页开始，留一个问题，再慢慢回来。这是一份用来检查生成流程的原创短文导览，不是真实出版物。','coverage':'完整覆盖两章原创测试短文；用于功能验收。','spoilers':False,'synopsis':[a,c],'map':[a,c],'diagrams':[{'title':'让阅读自然接下去','type':'sequence','nodes':[a,c]}],'quotes':[{'text':'读完一页，也是一段自己的时间。','context':'第一章里，小林重新理解自己的阅读时间。','unit':1}],'routes':[a,c]}

def make_epub(path):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        z.writestr('OEBPS/content.opf','<package><metadata><title>测试书</title></metadata><manifest><item id="a" href="a.xhtml"/><item id="b" href="b.xhtml"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>')
        z.writestr('OEBPS/a.xhtml','<html><body><p>甲章正文</p><script>不要执行</script></body></html>')
        z.writestr('OEBPS/b.xhtml','<html><body><p>乙章正文</p></body></html>')

class Tests(unittest.TestCase):
    def test_epub_spine(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'书.epub';make_epub(p);out=b.extract_one(p,d);s=b.read_json(out/'source.json')
            self.assertEqual(s['units'][0]['text'],'乙章正文');self.assertEqual(s['units'][1]['text'],'甲章正文')
    def test_text_encoding_and_md(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'中文.txt';p.write_bytes('这是中文正文。'.encode('gb18030'));out=b.extract_one(p,d)
            self.assertIn('这是中文正文',(out/'book.md').read_text(encoding='utf8'))
    def test_missing_mobi(self):
        with tempfile.TemporaryDirectory() as d,patch('booktool.shutil.which',return_value=None):
            p=Path(d)/'test.mobi';p.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError,'Calibre'):b.extract_one(p,d)
    def test_missing_pdf_parser(self):
        with tempfile.TemporaryDirectory() as d,patch('booktool.shutil.which',return_value=None),patch('booktool.importlib.util.find_spec',return_value=None):
            p=Path(d)/'test.pdf';p.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError,'PDF 解析器'):b.extract_one(p,d)
    def test_blank_text(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'empty.txt';p.write_text('  ')
            with self.assertRaisesRegex(ValueError,'OCR'):b.extract_one(p,d)
    def test_valid_guide(self):self.assertTrue(b.validate(fixture(),SOURCE))
    def test_fake_quote_rejected(self):
        g=fixture();g['quotes'][0]['text']='这句话并没有出现。'
        with self.assertRaisesRegex(ValueError,'引文'):b.validate(g,SOURCE)
    def test_bad_reference_rejected(self):
        g=fixture();g['map'][0]['units']=[999]
        with self.assertRaisesRegex(ValueError,'来源'):b.validate(g,SOURCE)
    def test_blank_source_rejected(self):
        s=copy.deepcopy(SOURCE);s['units'][0]['text']=''
        with self.assertRaisesRegex(ValueError,'来源'):b.validate(fixture(),s)
    def test_safe_html_and_no_network(self):
        g=fixture();g['title']='</script><img src=x onerror=alert(1)>'
        with tempfile.TemporaryDirectory() as d:
            b.publish([b.bundle(g,SOURCE)],d);h=(Path(d)/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('</script><img',h);self.assertNotIn('fetch(',h);self.assertNotIn('/*BOOKS*/',h)
    def test_source_excerpt_bound(self):
        s=copy.deepcopy(SOURCE);s['units'][1]['text']+='字'*10000
        self.assertLessEqual(len(b.bundle(fixture(),s)['sources'][1]['text']),260)

if __name__=='__main__':unittest.main()
