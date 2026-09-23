import io, struct, zipfile, unittest
from unittest.mock import patch
from ebook_import import parse_book

def sample_mobi(text=b'<html><body><p>Readable paragraph.</p></body></html>'):
    # A minimal uncompressed PalmDOC/MOBI fixture with two Palm database records.
    record=bytearray(200)
    struct.pack_into('>H',record,0,1)
    struct.pack_into('>I',record,4,len(text))
    struct.pack_into('>H',record,8,1)
    struct.pack_into('>H',record,10,4096)
    record[16:20]=b'MOBI'
    struct.pack_into('>I',record,28,65001)
    title=b'Fixture'
    struct.pack_into('>I',record,0x54,160)
    struct.pack_into('>I',record,0x58,len(title))
    record[160:160+len(title)]=title
    header=bytearray(78+16)
    struct.pack_into('>H',header,76,2)
    struct.pack_into('>I',header,78,len(header))
    struct.pack_into('>I',header,86,len(header)+len(record))
    return bytes(header+record+text)

def sample_epub(href='chapter.xhtml', text='<h1>第一章</h1><p>保留的正文</p><script>不执行的脚本</script>'):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
        z.writestr('OPS/book.opf','<package><metadata><title>原创导入检查</title></metadata><manifest><item id="c" href="'+href+'"/></manifest><spine><itemref idref="c"/></spine></package>')
        z.writestr('OPS/chapter.xhtml',text)
    return b.getvalue()

class ImportTests(unittest.TestCase):
    def test_epub_order_and_no_script(self):
        d=parse_book(sample_epub(),'epub');self.assertEqual(d['title'],'原创导入检查');self.assertEqual(d['units'][0]['title'],'第一章');self.assertEqual(d['units'][0]['text'],'第一章\n\n保留的正文')
    def test_bad_archive(self):
        with self.assertRaisesRegex(ValueError,'损坏'):parse_book(b'not a zip','epub')
    def test_path_escape_and_remote(self):
        for href in ('../../outside','https://example.com/a','/etc/passwd'):
            with self.assertRaises(ValueError):parse_book(sample_epub(href),'epub')
    def test_text_chunks_are_lossless(self):
        text='中文 hello\n'*2000;d=parse_book(text.encode(),'txt');self.assertEqual(''.join(u['text'] for u in d['units']),text)
    def test_gb18030(self):self.assertIn('文字',parse_book('文字内容'.encode('gb18030'),'txt')['units'][0]['text'])
    def test_markdown_is_data(self):self.assertEqual(parse_book(b'# hi\n<script>x</script>','md')['units'][0]['text'],'# hi\n<script>x</script>')
    def test_no_converter(self):
        with patch('ebook_import.converter',return_value=None):
            with self.assertRaisesRegex(ValueError,'Calibre'):parse_book(b'test','mobi')
    def test_mobi_direct_read_and_no_html_execution(self):
        d=parse_book(sample_mobi(),'mobi')
        self.assertEqual(d['title'],'Fixture')
        self.assertEqual(d['units'][0]['text'],'Readable paragraph.')
    def test_mobi_rejects_encryption(self):
        raw=bytearray(sample_mobi())
        struct.pack_into('>H',raw,94+12,1)
        with self.assertRaisesRegex(ValueError,'加密'):parse_book(bytes(raw),'mobi')
    def test_empty_book(self):
        with self.assertRaisesRegex(ValueError,'没有提取'):parse_book(sample_epub(text='<img src="x"/>'),'epub')
    def test_encrypted_archive(self):
        b=io.BytesIO(sample_epub())
        with zipfile.ZipFile(b,'a') as z:z.writestr('META-INF/encryption.xml','<encryption/>')
        with self.assertRaisesRegex(ValueError,'加密'):parse_book(b.getvalue(),'epub')

if __name__=='__main__':unittest.main()
