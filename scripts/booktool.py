#!/usr/bin/env python3
"""Portable book extraction and guide publishing. Python 3.9+, optional PDF/Calibre."""
import argparse, hashlib, html, importlib.util, json, platform, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent.parent
MAX_FILE = 256 * 1024 * 1024

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip += 1
        if tag in ('p','div','h1','h2','h3','br','li'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style') and self.skip: self.skip -= 1
        if tag in ('p','div','h1','h2','h3','li'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
    def result(self):
        return re.sub(r'\n[ \t]*\n+', '\n\n', ''.join(self.parts)).strip()

def epub_text(path):
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > 20000 or sum(i.file_size for i in z.infolist()) > MAX_FILE:
            raise ValueError('EPUB 解压内容超出 256 MB/20000 文件限制，请分卷处理。')
        if 'META-INF/encryption.xml' in z.namelist():
            raise ValueError('EPUB 声明了加密资源，本版不能确认是否可读；请提供不加密的文字版。')
        container=ET.fromstring(z.read('META-INF/container.xml'))
        root=next((x.attrib.get('full-path') for x in container.iter() if x.tag.endswith('rootfile')), None)
        if not root: raise ValueError('EPUB 缺少正文入口。')
        opf=ET.fromstring(z.read(root))
        manifest={x.attrib['id']:x.attrib for x in opf.iter() if x.tag.endswith('}item') or x.tag=='item'}
        title=next((x.text for x in opf.iter() if x.tag.endswith('}title') and x.text), path.stem)
        units=[]
        for x in opf.iter():
            if not (x.tag.endswith('}itemref') or x.tag=='itemref'): continue
            item=manifest.get(x.attrib.get('idref'),{})
            href=unquote(item.get('href','').split('#')[0])
            # Never extract paths; reject traversal and remote references.
            if not href or ':' in href or '..' in PurePosixPath(href).parts or href.startswith('/'):
                raise ValueError('EPUB 正文路径不受支持，请重新导出标准 EPUB。')
            name=str(PurePosixPath(root).parent / href)
            raw=z.read(name).decode('utf-8-sig')
            p=TextParser(); p.feed(raw)
            units.append((f'EPUB 文档 {len(units)+1} · {PurePosixPath(href).name}',p.result()))
        return title, units

def extract_one(path, out):
    path=Path(path)
    if path.stat().st_size > MAX_FILE: raise ValueError('文件超过 256 MB，请分卷处理。')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()[:24]
    ext=path.suffix.lower(); warnings=[]; title=path.stem
    if ext in ('.txt','.md','.markdown'):
        try: raw=path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError: raw=path.read_text(encoding='gb18030')
        units=[(f'文本片段 {i//6000+1}',raw[i:i+6000]) for i in range(0,len(raw),6000)]
    elif ext=='.epub': title,units=epub_text(path)
    elif ext=='.mobi':
        tool=shutil.which('ebook-convert')
        if not tool: raise ValueError('缺少 MOBI 转换工具。请安装 Calibre 并使 ebook-convert 可用，或提供 EPUB。')
        with tempfile.TemporaryDirectory() as temp:
            converted=Path(temp)/'converted.epub'
            result=subprocess.run([tool,str(path.resolve()),str(converted)],capture_output=True,timeout=180)
            if result.returncode: raise ValueError('MOBI 转换失败，请检查文件是否加密或损坏，或提供 EPUB。')
            title,units=epub_text(converted)
        warnings.append('来源为 MOBI 转换后的 EPUB 文档位置。')
    elif ext=='.pdf':
        if importlib.util.find_spec('pymupdf'):
            import pymupdf
            with pymupdf.open(path) as doc:
                if doc.needs_pass: raise ValueError('PDF 已加密，请提供可读版本。')
                units=[(f'PDF 文件第 {i+1} 页',p.get_text()) for i,p in enumerate(doc)]
        elif importlib.util.find_spec('pypdf'):
            from pypdf import PdfReader
            doc=PdfReader(str(path))
            if doc.is_encrypted: raise ValueError('PDF 已加密，请提供可读版本。')
            units=[(f'PDF 文件第 {i+1} 页',p.extract_text() or '') for i,p in enumerate(doc.pages)]
        elif shutil.which('pdftotext'):
            r=subprocess.run(['pdftotext','-enc','UTF-8',str(path.resolve()),'-'],capture_output=True,timeout=120)
            if r.returncode: raise ValueError('PDF 提取失败，请提供可读文字版。')
            pages=r.stdout.decode('utf-8').split('\f')
            if pages and not pages[-1].strip(): pages.pop()
            units=[(f'PDF 文件第 {i+1} 页',p) for i,p in enumerate(pages)]
        else: raise ValueError('缺少 PDF 解析器。使用宿主 PDF 能力，或在隔离环境安装 pypdf，或提供 TXT/MD。')
    else: raise ValueError('不支持此格式。请提供 PDF、EPUB、MOBI、TXT 或 MD。')
    if not units or not any(t.strip() for _,t in units): raise ValueError('未提取到正文。可能为扫描或图片书，需要 OCR 或文字版。')
    empty=[i+1 for i,(_,t) in enumerate(units) if not t.strip()]
    if empty: warnings.append('无文字的单元（需核对空白/图片/扫描）：'+','.join(map(str,empty)))
    warnings.append('提取未包含图片中的文字；提取完成不代表已经阅读或核验全书。')
    source={'id':digest,'title':title,'format':ext[1:],'warnings':warnings,'units':[{'id':i+1,'label':label,'text':t.strip()} for i,(label,t) in enumerate(units)]}
    target=Path(out)/digest; target.mkdir(parents=True,exist_ok=True)
    write_json(target/'source.json',source)
    (target/'book.md').write_text('# '+title+'\n\n'+'\n\n'.join(f"## U{u['id']} · {u['label']}\n\n{u['text']}" for u in source['units']),encoding='utf-8')
    return target

def validate(g,s):
    def require(ok,msg):
        if not ok: raise ValueError(msg)
    require(isinstance(g,dict) and isinstance(s,dict),'输入应是 JSON 对象。')
    for k in ('title','author','intro','coverage'): require(isinstance(g.get(k),str) and bool(g[k].strip()),'缺少文字字段：'+k)
    require(type(g.get('spoilers')) is bool,'spoilers 应为 true/false。')
    require(isinstance(s.get('id'),str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',s['id']), 'source.id 不合法。')
    units={u['id']:u for u in s['units']}
    require(len(units)==len(s['units']) and all(type(i) is int for i in units),'来源编号应为不重复整数。')
    def node(n):
        require(isinstance(n,dict) and all(isinstance(n.get(k),str) and n[k].strip() for k in ('title','text')),'节点需要 title/text。')
        require(isinstance(n.get('units'),list) and n['units'] and all(type(i) is int and i in units and units[i]['text'].strip() for i in n['units']),'节点引用了不存在或空白来源。')
    for key in ('synopsis','map','routes'):
        require(isinstance(g.get(key),list) and 1<=len(g[key])<=12,key+' 应有 1–12 项。')
        for n in g[key]: node(n)
    require(isinstance(g.get('diagrams'),list) and 1<=len(g['diagrams'])<=2,'需 1–2 幅结构图。')
    for d in g['diagrams']:
        require(isinstance(d.get('title'),str) and d['title'].strip() and d.get('type') in ('topics','sequence','contrast'),'结构图标题或类型错误。')
        require(isinstance(d.get('nodes'),list) and 2<=len(d['nodes'])<=4,'结构图需 2–4 节点。')
        for n in d['nodes']: node(n)
    require(isinstance(g.get('quotes'),list) and len(g['quotes'])<=8,'quotes 需为最多 8 条列表。')
    for q in g['quotes']:
        require(type(q.get('unit')) is int and q['unit'] in units,'引文来源无效。')
        require(isinstance(q.get('context'),str) and q['context'].strip(),'引文缺少上下文。')
        require(isinstance(q.get('text'),str) and 0<len(q['text'])<=100 and q['text'] in units[q['unit']]['text'],'引文不在来源中或长度超限。')
    return True

def bundle(g,s):
    validate(g,s)
    # Only short located excerpts enter shared page, not full book text.
    ids=set()
    for key in ('synopsis','map','routes'):
        for n in g[key]: ids.update(n['units'])
    for d in g['diagrams']:
        for n in d['nodes']: ids.update(n['units'])
    ids.update(q['unit'] for q in g['quotes'])
    excerpts=[]
    for u in s['units']:
        if u['id'] not in ids: continue
        q=next((q for q in g['quotes'] if q['unit']==u['id']),None)
        start=max(0,u['text'].find(q['text'])-50) if q else 0
        excerpts.append({'id':u['id'],'label':u['label'],'text':u['text'][start:start+260]})
    return {'id':s['id'],'guide':g,'sources':excerpts,'warnings':s.get('warnings',[])}

def publish(books,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    data=json.dumps(books,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    page=(BASE/'assets/template.html').read_text(encoding='utf-8')
    page=page.replace('/*THEMES*/',(BASE/'assets/themes.css').read_text(encoding='utf-8'))
    page=page.replace('/*APP*/',(BASE/'assets/app.js').read_text(encoding='utf-8')).replace('/*BOOKS*/',data)
    (out/'index.html').write_text(page,encoding='utf-8')
    write_json(out/'books.json',books)

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('preflight')
    ex=sub.add_parser('extract'); ex.add_argument('files',nargs='+'); ex.add_argument('--out',required=True)
    for cmd in ('validate','render'):
        x=sub.add_parser(cmd); x.add_argument('guide'); x.add_argument('--source',required=True)
        if cmd=='render': x.add_argument('--out',required=True)
    sh=sub.add_parser('shelf'); sh.add_argument('directories',nargs='+'); sh.add_argument('--out',required=True)
    args=p.parse_args()
    try:
        if args.cmd=='preflight':
            print(json.dumps({'os':platform.system(),'python':platform.python_version(),'python_ok':sys.version_info>=(3,9),'text_epub':True,'pdf':bool(importlib.util.find_spec('pymupdf') or importlib.util.find_spec('pypdf') or shutil.which('pdftotext')),'mobi':bool(shutil.which('ebook-convert')),'ocr':'not bundled','model_browser':'check host tools separately'},ensure_ascii=False,indent=2))
        elif args.cmd=='extract':
            failed=False
            for f in args.files:
                try: print(json.dumps({'file':Path(f).name,'output':str(extract_one(f,args.out))},ensure_ascii=False))
                except Exception as e: failed=True; print(json.dumps({'file':Path(f).name,'error':str(e)},ensure_ascii=False))
            return 2 if failed else 0
        elif args.cmd in ('validate','render'):
            g=read_json(args.guide); s=read_json(args.source); validate(g,s)
            if args.cmd=='render':
                publish([bundle(g,s)],args.out)
                lines=['# '+g['title'],g['intro'],'覆盖范围：'+g['coverage']]
                for key,label in [('synopsis','梗概'),('map','全书脑图'),('routes','怎么读')]:
                    lines.append('## '+label)
                    for n in g[key]: lines.extend(['### '+n['title'],n['text'],'来源：'+', '.join('U'+str(i) for i in n['units'])])
                lines.append('## 短摘录')
                for q in g['quotes']: lines.extend(['> '+q['text'],q['context']+f"（U{q['unit']}）"])
                for d in g['diagrams']:
                    lines.append('## '+d['title'])
                    for n in d['nodes']: lines.append(n['title']+'：'+n['text']+'（'+','.join('U'+str(i) for i in n['units'])+'）')
                lines.append('## 来源位置')
                lines.extend(f"U{u['id']}：{u['label']}" for u in s['units'])
                (Path(args.out)/'guide.md').write_text('\n\n'.join(lines),encoding='utf-8')
            print('校验通过。'+(' 网页与 Markdown 已生成。' if args.cmd=='render' else ''))
        elif args.cmd=='shelf':
            books={}
            for d in args.directories:
                for b in read_json(Path(d)/'books.json'): books[b['id']]=b
            if not books: raise ValueError('书架中没有已生成的书。')
            publish(list(books.values()),args.out); print('选书网页已生成。')
        return 0
    except Exception as e: print('未完成：'+str(e),file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
