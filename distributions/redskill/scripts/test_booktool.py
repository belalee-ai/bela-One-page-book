"""Original fixtures only; no user books, accounts or browser records."""
import copy, json, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import booktool as b
ROOT=Path(__file__).resolve().parent.parent
SOURCE=b.read_json(ROOT/'examples/source.json')
def fixture():return b.read_json(ROOT/'examples/guide.json')
def reviewed(g,s):
    ledger=b.new_reading(s)
    for row in ledger['units']:row.update(status='read',note='Synthetic test: unit reviewed.')
    r=b.new_review(g,s,ledger)
    for key in ('semantic','spoiler_check'):r[key]={'status':'reviewed','notes':'Synthetic test review, not a real book assessment.'}
    return r

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
            self.assertEqual([u['text'] for u in s['units']],['乙章正文','甲章正文'])
    def test_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'中文.txt';p.write_bytes('这是中文正文。'.encode('gb18030'));out=b.extract_one(p,d)
            self.assertIn('这是中文正文',(out/'book.md').read_text(encoding='utf-8'))
    def test_extract_is_not_reading(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'书.txt';p.write_text('第一章的正文', encoding='utf-8');out=b.extract_one(p,d)
            self.assertEqual(b.read_json(out/'reading.json')['units'][0]['status'],'unread')
    def test_resume_preserves_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'书.txt';p.write_text('第一章的正文', encoding='utf-8');out=b.extract_one(p,d);ledger=b.read_json(out/'reading.json')
            ledger['units'][0].update(status='read',note='已经核对正文');b.write_json(out/'reading.json',ledger)
            b.extract_one(p,d);self.assertEqual(ledger,b.read_json(out/'reading.json'))
    def test_stale_ledger_rejected(self):
        ledger=b.new_reading(SOURCE);s=copy.deepcopy(SOURCE);s['units'][0]['text']+='变更'
        with self.assertRaisesRegex(ValueError,'正文已改变'):b.check_reading(ledger,s)
    def test_batch_failure_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'甲.txt';a.write_text('甲正文', encoding='utf-8');bad=Path(d)/'坏.epub';bad.write_text('坏文件', encoding='utf-8');c=Path(d)/'乙.txt';c.write_text('乙正文', encoding='utf-8')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/booktool.py'),'extract',str(a),str(bad),str(c),'--out',str(Path(d)/'output')],capture_output=True,text=True, encoding='utf-8')
            rows=[json.loads(line) for line in r.stdout.splitlines()]
            self.assertEqual(r.returncode,2);self.assertEqual(len(rows),3);self.assertIn('error',rows[1])
            for i in (0,2):self.assertTrue((Path(rows[i]['output'])/'reading.json').is_file())
    def test_missing_mobi(self):
        with tempfile.TemporaryDirectory() as d,patch('booktool.shutil.which',return_value=None):
            p=Path(d)/'x.mobi';p.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError,'Calibre'):b.extract_one(p,d)
    def test_missing_pdf(self):
        with tempfile.TemporaryDirectory() as d,patch('booktool.shutil.which',return_value=None),patch('booktool.importlib.util.find_spec',return_value=None):
            p=Path(d)/'x.pdf';p.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError,'PDF 解析器'):b.extract_one(p,d)
    def test_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.txt';p.write_text(' ', encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'OCR'):b.extract_one(p,d)
    def test_valid(self):
        g=fixture();self.assertTrue(b.validate(g,SOURCE,reviewed(g,SOURCE)))
    def test_no_review(self):
        with self.assertRaisesRegex(ValueError,'缺少核对记录'):b.validate(fixture(),SOURCE)
    def test_pending_review(self):
        g=fixture();r=reviewed(g,SOURCE);r['semantic']['status']='pending'
        with self.assertRaisesRegex(ValueError,'semantic'):b.validate(g,SOURCE,r)
    def test_changed_claim_invalidates_review(self):
        g=fixture();r=reviewed(g,SOURCE);g['synopsis'][0]['text']='本书建议放弃阅读。'
        with self.assertRaisesRegex(ValueError,'已改变'):b.validate(g,SOURCE,r)
    def test_changed_source_invalidates_review(self):
        g=fixture();r=reviewed(g,SOURCE);s=copy.deepcopy(SOURCE);s['units'].append({'id':3,'label':'第三章','text':'遗漏正文'})
        with self.assertRaisesRegex(ValueError,'已改变'):b.validate(g,s,r)
    def test_full_requires_coverage(self):
        g=fixture();s=copy.deepcopy(SOURCE);s['units'].append({'id':3,'label':'第三章','text':'遗漏正文'});r=reviewed(g,s);r['reading']['units'][-1].update(status='unread',note='')
        with self.assertRaisesRegex(ValueError,'部分导览'):b.validate(g,s,r)
    def test_partial_allowed_and_labelled(self):
        g=fixture();g['scope']='partial';s=copy.deepcopy(SOURCE);s['units'].append({'id':3,'label':'第三章','text':'遗漏正文'});r=reviewed(g,s);r['reading']['units'][-1].update(status='unread',note='')
        packed=b.bundle(g,s,r);self.assertIn('2/3',packed['guide']['coverage_status']);self.assertIn('U3',packed['guide']['coverage_notes'][0])
    def test_empty_unit_cannot_be_read(self):
        s=copy.deepcopy(SOURCE);s['units'].append({'id':3,'label':'扫描页','text':''});g=fixture()
        with self.assertRaisesRegex(ValueError,'无文字单元'):b.validate(g,s,reviewed(g,s))
    def test_missing_unit_record(self):
        g=fixture();r=reviewed(g,SOURCE);r['reading']['units'].pop()
        with self.assertRaisesRegex(ValueError,'缺少单元'):b.validate(g,SOURCE,r)
    def test_exclusion_reason_required(self):
        g=fixture();r=reviewed(g,SOURCE);r['reading']['units'][0].update(status='excluded',note='')
        with self.assertRaisesRegex(ValueError,'排除理由'):b.validate(g,SOURCE,r)
    def test_evidence_required(self):
        g=fixture();del g['synopsis'][0]['evidence']
        with self.assertRaisesRegex(ValueError,'原文依据'):b.validate(g,SOURCE,reviewed(g,SOURCE))
    def test_fake_evidence(self):
        g=fixture();g['map'][0]['evidence'][0]['text']='不存在的原文'
        with self.assertRaisesRegex(ValueError,'依据不在原文'):b.validate(g,SOURCE,reviewed(g,SOURCE))
    def test_fake_quote(self):
        g=fixture();g['quotes'][0]['text']='不存在的原文'
        with self.assertRaisesRegex(ValueError,'引文'):b.validate(g,SOURCE,reviewed(g,SOURCE))
    def test_far_quotes_each_have_context(self):
        g=fixture();s=copy.deepcopy(SOURCE);s['units'][0]['text']+='填充。'*200+'第二条远处引文。'
        g['quotes'].append({'text':'第二条远处引文。','unit':1,'context':'远处原文'})
        packed=b.bundle(g,s,reviewed(g,s));byid={e['id']:e for e in packed['sources']}
        self.assertNotEqual(packed['guide']['quotes'][0]['sourceRefs'],packed['guide']['quotes'][1]['sourceRefs'])
        for q in packed['guide']['quotes']:self.assertIn(q['text'],byid[q['sourceRefs'][0]]['text'])
    def test_claim_evidence_not_page_start(self):
        g=fixture();s=copy.deepcopy(SOURCE);s['units'][0]['text']+='填充。'*200+'远处观点依据。';g['synopsis'][0]['evidence']=[{'unit':1,'text':'远处观点依据。'}]
        packed=b.bundle(g,s,reviewed(g,s));ref=packed['guide']['synopsis'][0]['sourceRefs'][0]
        self.assertIn('远处观点依据。',next(e['text'] for e in packed['sources'] if e['id']==ref))
    def test_safe_html(self):
        g=fixture();g['title']='</script><img src=x onerror=alert(1)>'
        with tempfile.TemporaryDirectory() as d:
            b.publish([b.bundle(g,SOURCE,reviewed(g,SOURCE))],d);h=(Path(d)/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('</script><img',h);self.assertNotIn('fetch(',h);self.assertNotIn('/*BOOKS*/',h)
    def test_excerpt_bound(self):
        g=fixture();s=copy.deepcopy(SOURCE);s['units'][0]['text']+='字'*10000
        self.assertTrue(all(len(e['text'])<=280 for e in b.bundle(g,s,reviewed(g,s))['sources']))
    def test_prepare_review_is_pending(self):
        r=b.new_review(fixture(),SOURCE,b.new_reading(SOURCE));self.assertEqual(r['semantic']['status'],'pending')
    def test_cli_missing_review_fails(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/booktool.py'),'validate',str(ROOT/'examples/guide.json'),'--source',str(ROOT/'examples/source.json')],capture_output=True)
        self.assertNotEqual(r.returncode,0)
    def test_bundle_version_required(self):
        g=fixture();pack=b.bundle(g,SOURCE,reviewed(g,SOURCE));pack.pop('format_version')
        with self.assertRaisesRegex(ValueError,'重新生成'):b.check_bundle(pack)
    def test_missing_display_reference_rejected(self):
        g=fixture();pack=b.bundle(g,SOURCE,reviewed(g,SOURCE));del pack['guide']['map'][0]['sourceRefs']
        with self.assertRaisesRegex(ValueError,'不完整'):b.check_bundle(pack)
    def test_old_shelf_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);old=base/'old';old.mkdir();g=fixture();pack=b.bundle(g,SOURCE,reviewed(g,SOURCE));pack.pop('format_version');b.write_json(old/'books.json',[pack])
            result=subprocess.run([sys.executable,str(ROOT/'scripts/booktool.py'),'shelf',str(old),'--out',str(base/'out')],capture_output=True,text=True, encoding='utf-8')
            self.assertEqual(result.returncode,2);self.assertIn('重新生成',result.stderr);self.assertFalse((base/'out/index.html').exists())
    def test_render_spoiler_md_gate(self):
        with tempfile.TemporaryDirectory() as d:
            g=fixture();g['spoilers']=True;g['intro']='结局标记';g['coverage']='覆盖秘密';b.write_json(Path(d)/'g.json',g);b.write_json(Path(d)/'r.json',reviewed(g,SOURCE))
            r=subprocess.run([sys.executable,str(ROOT/'scripts/booktool.py'),'render',str(Path(d)/'g.json'),'--source',str(ROOT/'examples/source.json'),'--review',str(Path(d)/'r.json'),'--out',d],capture_output=True,text=True, encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stderr);text=(Path(d)/'guide.md').read_text(encoding='utf-8');before=text.split('<details>')[0]
            self.assertNotIn('结局标记',before);self.assertNotIn('覆盖秘密',before);self.assertIn('结局标记',text)

if __name__=='__main__':unittest.main()
