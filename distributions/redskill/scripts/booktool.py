#!/usr/bin/env python3
"""Portable book extraction and guide publishing. Python 3.9+, optional PDF/Calibre."""
import copy, argparse, hashlib, html, importlib.util, json, platform, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent.parent
MAX_FILE = 256 * 1024 * 1024
VERSION = "0.2"

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
    file_hash=hashlib.sha256(path.read_bytes()).hexdigest(); digest=file_hash[:24]
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
    source={'sha256':file_hash,'id':digest,'title':title,'format':ext[1:],'warnings':warnings,'units':[{'id':i+1,'label':label,'text':t.strip()} for i,(label,t) in enumerate(units)]}
    target=Path(out)/digest; target.mkdir(parents=True,exist_ok=True)
    # Preserve a matching reading ledger on restart; never mark extraction as reading.
    ledger_path=target/'reading.json'
    if ledger_path.exists():
        check_reading(read_json(ledger_path), source)
    else:
        write_json(ledger_path, new_reading(source))
    write_json(target/'source.json',source)
    (target/'book.md').write_text('# '+title+'\n\n'+'\n\n'.join(f"## U{u['id']} · {u['label']}\n\n{u['text']}" for u in source['units']),encoding='utf-8')
    return target

def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def require(ok, message):
    if not ok: raise ValueError(message)

def new_reading(s):
    return {'version':VERSION, 'source_digest':digest(s), 'units':[
        {'id':u['id'], 'status':'unread', 'note':''} for u in s['units']]}

def check_reading(ledger, s):
    require(isinstance(ledger,dict) and ledger.get('version')==VERSION, '阅读记录版本不匹配。')
    require(ledger.get('source_digest')==digest(s), '正文已改变，旧阅读记录不能复用，请重新核对。')
    rows=ledger.get('units')
    require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows), '缺少逐单元阅读记录。')
    ids=[r.get('id') for r in rows]
    require(all(type(i) is int for i in ids) and len(set(ids))==len(ids) and set(ids)=={u['id'] for u in s['units']}, '阅读记录缺少单元或包含重复单元。')
    for r in rows:
        require(r.get('status') in ('unread','read','partial','unreadable','excluded'), '阅读状态无效。')
        require(isinstance(r.get('note'),str), '阅读记录缺少说明。')
        require(r['status']=='unread' or bool(r['note'].strip()), '已处理或排除单元必须记录摘要、缺口或排除理由。')
        text=next(u['text'] for u in s['units'] if u['id']==r['id'])
        require(r['status']!='read' or bool(text.strip()), '无文字单元不能标为已读，请核对扫描页或说明排除理由。')
    return {r['id']:r for r in rows}

def new_review(g,s,ledger):
    check_reading(ledger,s)
    return {'version':VERSION, 'source_digest':digest(s), 'guide_digest':digest(g),
            'reading':copy.deepcopy(ledger), 'semantic':{'status':'pending','notes':''},
            'spoiler_check':{'status':'pending','notes':''}}

def validate(g,s,review=None):
    require(isinstance(g,dict) and isinstance(s,dict),'输入应是 JSON 对象。')
    for k in ('title','author','intro','coverage'): require(isinstance(g.get(k),str) and bool(g[k].strip()),'缺少文字字段：'+k)
    require(type(g.get('spoilers')) is bool,'spoilers 应为 true/false。')
    require(g.get('scope') in ('full','partial'),'scope 必须明确为 full 或 partial。')
    require(isinstance(s.get('id'),str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',s['id']), 'source.id 不合法。')
    require(isinstance(s.get('units'),list) and s['units'] and all(isinstance(u,dict) and type(u.get('id')) is int and isinstance(u.get('text'),str) and isinstance(u.get('label'),str) for u in s['units']), '来源单元结构无效。')
    units={u['id']:u for u in s['units']}
    require(len(units)==len(s['units']), '来源编号应为不重复整数。')
    cited=set()
    def node(n):
        require(isinstance(n,dict) and all(isinstance(n.get(k),str) and n[k].strip() for k in ('title','text')),'节点需要 title/text。')
        require(isinstance(n.get('units'),list) and n['units'] and all(type(i) is int and i in units and units[i]['text'].strip() for i in n['units']),'节点引用了不存在或空白来源。')
        evidence=n.get('evidence')
        require(isinstance(evidence,list) and 1<=len(evidence)<=24, '每条观点必须提供原文依据 evidence。')
        seen=set()
        for e in evidence:
            require(isinstance(e,dict) and type(e.get('unit')) is int and e['unit'] in n['units'], '依据的来源不匹配。')
            require(isinstance(e.get('text'),str) and 0<len(e['text'])<=200 and e['text'] in units[e['unit']]['text'], '观点依据不在原文中或超过200字。')
            seen.add(e['unit'])
        require(seen==set(n['units']), '每个引用单元都需要具体原文依据。')
        cited.update(n['units'])
    for key in ('synopsis','map','routes'):
        require(isinstance(g.get(key),list) and 1<=len(g[key])<=12,key+' 应有 1–12 项。')
        for n in g[key]: node(n)
    require(isinstance(g.get('diagrams'),list) and 1<=len(g['diagrams'])<=2,'需 1–2 幅结构图。')
    for d in g['diagrams']:
        require(isinstance(d,dict) and isinstance(d.get('title'),str) and d['title'].strip() and d.get('type') in ('topics','sequence','contrast'),'结构图标题或类型错误。')
        require(isinstance(d.get('nodes'),list) and 2<=len(d['nodes'])<=4,'结构图需 2–4 节点。')
        for n in d['nodes']: node(n)
    require(isinstance(g.get('quotes'),list) and len(g['quotes'])<=8,'quotes 需为最多 8 条列表。')
    for q in g['quotes']:
        require(isinstance(q,dict) and type(q.get('unit')) is int and q['unit'] in units,'引文来源无效。')
        require(isinstance(q.get('context'),str) and q['context'].strip(),'引文缺少上下文。')
        require(isinstance(q.get('text'),str) and 0<len(q['text'])<=100 and q['text'] in units[q['unit']]['text'],'引文不在来源中或长度超限。')
        cited.add(q['unit'])
    require(isinstance(review,dict), '缺少核对记录 review.json，不能仅凭结构校验发布。')
    require(review.get('version')==VERSION and review.get('source_digest')==digest(s) and review.get('guide_digest')==digest(g), '正文或导览已改变，请重新核对并生成对应记录。')
    rows=check_reading(review.get('reading'),s)
    require(all(rows[i]['status']=='read' for i in cited), '引用单元尚未完整阅读，请补读或缩小来源单元再生成。')
    if g['scope']=='full':
        require(all(r['status'] in ('read','excluded') for r in rows.values()), '有未完成的阅读单元，只能交付部分导览。')
    for key in ('semantic','spoiler_check'):
        check=review.get(key,{})
        require(isinstance(check,dict) and check.get('status')=='reviewed' and isinstance(check.get('notes'),str) and check['notes'].strip(), '尚未完成核对：'+key)
    return True

def bundle(g,s,review=None):
    validate(g,s,review)
    guide=copy.deepcopy(g); sources=[]; by_id={u['id']:u for u in s['units']}
    def ref(unit,text):
        u=by_id[unit]; at=u['text'].index(text); start=max(0,at-40); end=min(len(u['text']),at+len(text)+40)
        key='ref-'+str(len(sources)+1)
        sources.append({'id':key,'unit':unit,'label':u['label'],'text':u['text'][start:end], 'exact':text})
        return key
    for key in ('synopsis','map','routes'):
        for n in guide[key]: n['sourceRefs']=[ref(e['unit'],e['text']) for e in n['evidence']]
    for d in guide['diagrams']:
        for n in d['nodes']: n['sourceRefs']=[ref(e['unit'],e['text']) for e in n['evidence']]
    for q in guide['quotes']: q['sourceRefs']=[ref(q['unit'],q['text'])]
    rows=review['reading']['units']; read=sum(r['status']=='read' for r in rows); excluded=sum(r['status']=='excluded' for r in rows)
    guide['coverage_status']=f"{'全书导览' if g['scope']=='full' else '部分材料导览'} · 已读 {read}/{len(rows)} 个来源单元 · 排除 {excluded} 个"
    guide['coverage_notes']=[f"U{r['id']} · {r['status']}：{r['note'] or '尚未阅读'}" for r in rows if r['status']!='read']
    return {'format_version':1,'generator_version':VERSION,'source_format':s.get('format'),'source_sha256':s.get('sha256'),'id':s['id'],'title':s['title'],'guide':guide,'sources':sources,'warnings':s.get('warnings',[]),
            'verification':'格式、逐字依据与记录一致性已通过；语义和防剧透由整理者复核，不是自动事实认证。'}

def check_bundle(book):
    # A shelf can only accept complete output from this generator, not a raw or old guide.
    msg='导览数据格式不完整或版本不兼容，请用当前版本重新生成该书，再合并选书页。'
    require(isinstance(book,dict) and book.get('format_version')==1 and book.get('generator_version')==VERSION,msg)
    require(isinstance(book.get('id'),str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',book['id']) and book['id'] not in ('__proto__','constructor','prototype'),msg)
    require(all(isinstance(book.get(k),str) for k in ('title','verification')),msg)
    require(isinstance(book.get('warnings'),list) and all(isinstance(x,str) for x in book['warnings']),msg)
    sha=book.get('source_sha256')
    require(sha is None or (isinstance(sha,str) and re.fullmatch(r'[a-f0-9]{64}',sha) and sha[:24]==book['id']),msg)
    require(book.get('source_format') in (None,'pdf','epub','mobi','txt','md','markdown'),msg)
    sources=book.get('sources');require(isinstance(sources,list) and sources,msg)
    require(all(isinstance(x,dict) and all(isinstance(x.get(k),str) for k in ('id','label','text','exact')) for x in sources),msg)
    require(all(type(x.get('unit')) is int and x['unit']>0 for x in sources),msg)
    refs={x['id'] for x in sources};require(len(refs)==len(sources) and all(x['exact'] and x['exact'] in x['text'] for x in sources),msg)
    g=book.get('guide');require(isinstance(g,dict),msg)
    require(all(isinstance(g.get(k),str) for k in ('title','author','intro','coverage','coverage_status')),msg)
    require(type(g.get('spoilers')) is bool and g.get('scope') in ('full','partial'),msg)
    require(isinstance(g.get('coverage_notes'),list) and all(isinstance(x,str) for x in g['coverage_notes']),msg)
    def node(n,quote=False):
        require(isinstance(n,dict) and all(isinstance(n.get(k),str) for k in (('text','context') if quote else ('title','text'))),msg)
        require(isinstance(n.get('sourceRefs'),list) and n['sourceRefs'] and all(isinstance(x,str) and x in refs for x in n['sourceRefs']),msg)
    for key in ('synopsis','map','routes'):
        require(isinstance(g.get(key),list) and 1<=len(g[key])<=12,msg)
        for n in g[key]:node(n)
    require(isinstance(g.get('quotes'),list) and len(g['quotes'])<=8,msg)
    for n in g['quotes']:node(n,True)
    require(isinstance(g.get('diagrams'),list) and 1<=len(g['diagrams'])<=2,msg)
    for d in g['diagrams']:
        require(isinstance(d,dict) and isinstance(d.get('title'),str) and d.get('type') in ('topics','sequence','contrast') and isinstance(d.get('nodes'),list) and 2<=len(d['nodes'])<=4,msg)
        for n in d['nodes']:node(n)
    return True

def publish(books,out):
    require(isinstance(books,list) and books, '选书页没有有效导览。')
    for book in books:check_bundle(book)
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    data=json.dumps(books,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    page=(BASE/'assets/template.html').read_text(encoding='utf-8')
    page=page.replace('/*THEMES*/',(BASE/'assets/themes.css').read_text(encoding='utf-8'))
    page=page.replace('/*APP*/',(BASE/'assets/app.js').read_text(encoding='utf-8')).replace('/*BOOKS*/',data)
    reader=BASE/'assets/reader'
    styles=''.join((reader/name).read_text(encoding='utf-8') for name in ('pdf.css','annotations.css'))
    scripts=''.join('<script>'+ (reader/name).read_text(encoding='utf-8')+'</script>' for name in ('motion.js','annotations.js','pdf.js','bridge.js'))
    page=page.replace('</html>','<style>'+styles+'</style>'+(reader/'dialog.html').read_text(encoding='utf-8')+scripts+'</html>')
    if any(book.get('source_format')=='pdf' for book in books):shutil.copytree(reader/'pdfjs',out/'reader/pdfjs',dirs_exist_ok=True)
    shutil.copy2(BASE/'scripts/start_reader.py',out/'start_reader.py')
    (out/'index.html').write_text(page,encoding='utf-8')
    write_json(out/'books.json',books)

def main():
    # Redirected Windows consoles may otherwise reject Chinese status messages.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('preflight')
    ex=sub.add_parser('extract'); ex.add_argument('files',nargs='+'); ex.add_argument('--out',required=True)
    for cmd in ('validate','render'):
        x=sub.add_parser(cmd); x.add_argument('guide'); x.add_argument('--source',required=True); x.add_argument('--review',required=True)
        if cmd=='render': x.add_argument('--out',required=True)
    rv=sub.add_parser('prepare-review'); rv.add_argument('guide'); rv.add_argument('--source',required=True); rv.add_argument('--reading',required=True); rv.add_argument('--out',required=True)
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
        elif args.cmd=='prepare-review':
            require(not Path(args.out).exists(), '核对记录已存在，请使用新文件名，保留旧记录。')
            write_json(args.out,new_review(read_json(args.guide),read_json(args.source),read_json(args.reading)))
            print('核对草稿已创建，语义与剧透检查尚待完成。')
        elif args.cmd in ('validate','render'):
            g=read_json(args.guide); s=read_json(args.source); review=read_json(args.review); validate(g,s,review)
            if args.cmd=='render':
                publish([bundle(g,s,review)],args.out)
                packed=bundle(g,s,review)
                lines=['# '+(s['title'] if g['spoilers'] else g['title']),packed['guide']['coverage_status'],]
                if g['spoilers']: lines+=['> 以下含故事情节与结局，确认后再展开。','<details><summary>展开完整导览（含剧透）</summary>']
                lines.extend([g['intro'],'覆盖范围：'+g['coverage']])
                for key,label in [('synopsis','梗概'),('map','全书脑图' if g['scope']=='full' else '已读部分脑图'),('routes','怎么读')]:
                    lines.append('## '+label)
                    for n in g[key]: lines.extend(['### '+n['title'],n['text'],'来源：'+', '.join('U'+str(i) for i in n['units'])])
                lines.append('## 短摘录')
                for q in g['quotes']: lines.extend(['> '+q['text'],q['context']+f"（U{q['unit']}）"])
                for d in g['diagrams']:
                    lines.append('## '+d['title'])
                    for n in d['nodes']: lines.append(n['title']+'：'+n['text']+'（'+','.join('U'+str(i) for i in n['units'])+'）')
                lines+=['## 覆盖缺口与排除说明']+packed['guide']['coverage_notes']
                lines.append('## 原文依据')
                lines.extend(f"{e['id']} · {e['label']}\n\n> {e['text']}" for e in packed['sources'])
                lines.append('## 来源位置')
                lines.extend(f"U{u['id']}：{u['label']}" for u in s['units'])
                if g['spoilers']: lines.append('</details>')
                (Path(args.out)/'guide.md').write_text('\n\n'.join(lines),encoding='utf-8')
            print('格式、逐字依据与核对记录一致性通过；不等于自动确认语义正确。'+(' 网页与 Markdown 已生成。' if args.cmd=='render' else ''))
        elif args.cmd=='shelf':
            books={}
            for d in args.directories:
                incoming=read_json(Path(d)/'books.json')
                require(isinstance(incoming,list), 'books.json 应为导览列表，请重新生成。')
                for b in incoming:
                    check_bundle(b)
                    books[b['id']]=b
            if not books: raise ValueError('书架中没有已生成的书。')
            publish(list(books.values()),args.out); print('选书网页已生成。')
        return 0
    except Exception as e: print('未完成：'+str(e),file=sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
