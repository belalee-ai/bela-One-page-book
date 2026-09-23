"""Local text-book import. Never executes or serves markup from a book."""
import io, os, posixpath, re, shutil, struct, subprocess, tempfile, zipfile
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

MAX_UPLOAD = 60 * 1024 * 1024
MAX_EXPANDED = 200 * 1024 * 1024
MAX_TEXT = 15000000

def converter():
    candidates = [shutil.which('ebook-convert'), '/Applications/calibre.app/Contents/MacOS/ebook-convert']
    for key in ('ProgramFiles', 'ProgramFiles(x86)'):
        if os.environ.get(key): candidates.append(str(Path(os.environ[key])/'Calibre2/ebook-convert.exe'))
    return next((p for p in candidates if p and Path(p).is_file()), None)

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.skip=0; self.heading=[]; self.in_heading=False
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','iframe','object'): self.skip+=1
        if tag in ('p','div','h1','h2','h3','br','li','section'): self.parts.append('\n')
        if tag in ('h1','h2','h3') and not self.heading: self.in_heading=True
    def handle_endtag(self, tag):
        if tag in ('script','style','iframe','object') and self.skip: self.skip-=1
        if tag in ('p','div','h1','h2','h3','li','section'): self.parts.append('\n')
        if tag in ('h1','h2','h3'): self.in_heading=False
    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)
            if self.in_heading: self.heading.append(text)
    def text(self): return re.sub(r'\n[ \t]*\n+', '\n\n', ''.join(self.parts)).strip()

def xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('电子书包含不支持的 XML 声明，请重新导出 EPUB。')
    return ET.fromstring(raw)

def decode(raw):
    try: return raw.decode('utf-8-sig')
    except UnicodeDecodeError: return raw.decode('gb18030')

def palmdoc(data, limit):
    """Expand one PalmDOC record, stopping before MOBI's trailing metadata."""
    out=bytearray();i=0
    while i<len(data) and len(out)<limit:
        c=data[i];i+=1
        if 1<=c<=8:
            if i+c>len(data): raise ValueError('MOBI 正文记录不完整。')
            out.extend(data[i:i+c]);i+=c
        elif c<128: out.append(c)
        elif c<192:
            if i>=len(data): raise ValueError('MOBI 压缩记录不完整。')
            pair=(c<<8)|data[i];i+=1
            distance=(pair>>3)&2047;length=(pair&7)+3
            if not distance or distance>len(out): raise ValueError('MOBI 压缩记录损坏。')
            for _ in range(length): out.append(out[-distance])
        else: out.extend((32,c^128))
    if len(out)<limit: raise ValueError('MOBI 正文记录不完整。')
    return bytes(out[:limit])

def mobi_text(raw):
    if len(raw)<86: raise ValueError('MOBI 文件不完整。')
    count=struct.unpack_from('>H',raw,76)[0]
    if not 2<=count<=20000 or 78+count*8>len(raw): raise ValueError('MOBI 目录损坏。')
    offsets=[struct.unpack_from('>I',raw,78+i*8)[0] for i in range(count)]
    if offsets!=sorted(offsets) or offsets[0]<78+count*8 or offsets[-1]>=len(raw): raise ValueError('MOBI 记录位置不正确。')
    header=raw[offsets[0]:offsets[1]]
    if len(header)<160 or header[16:20]!=b'MOBI': raise ValueError('这份 MOBI 的正文格式无法直接识别。')
    if struct.unpack_from('>H',header,12)[0]: raise ValueError('MOBI 已加密，请提供可读取的 EPUB 或文字版。')
    compression=struct.unpack_from('>H',header,0)[0]
    if compression not in (1,2): raise ValueError('这份 MOBI 使用了暂不支持的压缩格式。')
    length=struct.unpack_from('>I',header,4)[0]
    records=struct.unpack_from('>H',header,8)[0]
    block=struct.unpack_from('>H',header,10)[0]
    encoding=struct.unpack_from('>I',header,28)[0]
    if not 0<length<=MAX_TEXT or not 0<records<count or not 0<block<=65536 or records*block<length:
        raise ValueError('MOBI 正文大小或记录数量不正确。')
    if encoding not in (65001,1252): raise ValueError('MOBI 文字编码暂不支持，请转换为 EPUB。')
    chunks=[];remaining=length
    for i in range(1,records+1):
        start=offsets[i];end=offsets[i+1] if i+1<count else len(raw)
        expected=min(block,remaining);data=raw[start:end]
        part=palmdoc(data,expected) if compression==2 else data[:expected]
        if len(part)!=expected: raise ValueError('MOBI 正文记录不完整。')
        chunks.append(part);remaining-=expected
    if remaining: raise ValueError('MOBI 正文缺页。')
    codec='utf-8' if encoding==65001 else 'cp1252'
    try: markup=b''.join(chunks).decode(codec)
    except UnicodeDecodeError as error: raise ValueError('MOBI 文字编码损坏，请转换为 EPUB。') from error
    name_offset=struct.unpack_from('>I',header,0x54)[0]
    name_length=struct.unpack_from('>I',header,0x58)[0]
    title=header[name_offset:name_offset+name_length].decode(codec,errors='replace') if name_length<=500 and name_offset+name_length<=len(header) else ''
    sections=re.split(r'<mbp:pagebreak\b[^>]*>',markup,flags=re.I)
    units=[]
    for section in sections:
        parser=PlainText();parser.feed(section);text=parser.text()
        if text: units.append({'title':(''.join(parser.heading).strip() or '第 '+str(len(units)+1)+' 节')[:200],'text':text})
    return title,units

def epub(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist()
        if len(infos)>20000 or sum(i.file_size for i in infos)>MAX_EXPANDED or any(i.file_size>20*1024*1024 for i in infos):
            raise ValueError('EPUB 解压内容过大，请分卷后添加。')
        names=set(z.namelist())
        if len(names)!=len(infos): raise ValueError('EPUB 包含重复文件路径，请重新导出。')
        if 'META-INF/encryption.xml' in names: raise ValueError('EPUB 含加密资源，请提供未加密的 EPUB 或文字版。')
        container=xml(z.read('META-INF/container.xml'))
        root=next((e.get('full-path') for e in container.iter() if e.tag.split('}')[-1]=='rootfile'),None)
        if not root or root.startswith('/') or '..' in root.split('/'): raise ValueError('EPUB 缺少有效的正文入口。')
        package=xml(z.read(root))
        title=next((e.text for e in package.iter() if e.tag.split('}')[-1]=='title' and e.text),'')
        manifest={e.get('id'):e for e in package.iter() if e.tag.split('}')[-1]=='item'}
        units=[]
        for e in package.iter():
            if e.tag.split('}')[-1]!='itemref': continue
            item=manifest.get(e.get('idref'))
            if item is None: raise ValueError('EPUB 目录引用了缺失的章节。')
            href=unquote(item.get('href','').split('#')[0]); parsed=urlsplit(href)
            name=posixpath.normpath(posixpath.join(posixpath.dirname(root),href))
            if not href or parsed.scheme or parsed.netloc or href.startswith('/') or name.startswith('../') or '\\' in href:
                raise ValueError('EPUB 正文路径不受支持，请重新导出。')
            p=PlainText();p.feed(decode(z.read(name)));text=p.text()
            # Keep empty image-only sections visible as a limitation, not silently omitted.
            units.append({'title':(''.join(p.heading).strip() or '第 '+str(len(units)+1)+' 节')[:200], 'text':text})
        return title,units

def parse_book(raw, ext):
    if not raw or len(raw)>MAX_UPLOAD: raise ValueError('文件为空或超过 60 MB，请分卷后添加。')
    if ext not in ('epub','mobi','txt','md','markdown'): raise ValueError('请添加 PDF、EPUB、MOBI、TXT 或 Markdown。')
    warnings=['文字阅读版不保留原书图片和版式；图片中的文字未识别。']
    try:
        if ext=='mobi':
            try: title,units=mobi_text(raw)
            except ValueError as error:
                if '加密' in str(error): raise
                tool=converter()
                if not tool: raise ValueError(str(error)+' 如需继续，请在本机用 Calibre 转成 EPUB 后添加。') from error
                with tempfile.TemporaryDirectory(prefix='bela-book-') as temp:
                    src=Path(temp)/'source.mobi';dst=Path(temp)/'book.epub';src.write_bytes(raw)
                    try: result=subprocess.run([tool,str(src),str(dst)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180)
                    except subprocess.TimeoutExpired: raise ValueError('MOBI 转换超时，请在 Calibre 中转成 EPUB 后重试。')
                    if result.returncode or not dst.is_file() or dst.stat().st_size>MAX_UPLOAD: raise ValueError('MOBI 转换失败，请检查加密或损坏情况，或提供 EPUB。')
                    title,units=epub(dst.read_bytes())
        elif ext=='epub': title,units=epub(raw)
        else:
            text=decode(raw);title='';units=[{'title':'文本片段 '+str(i//6000+1),'text':text[i:i+6000]} for i in range(0,len(text),6000)]
    except (zipfile.BadZipFile,KeyError,ET.ParseError,UnicodeError,RuntimeError) as error:
        raise ValueError('文件损坏、加密或文字编码无法读取，请重新导出 EPUB 或 UTF-8 文本。') from error
    if not units or not any(u['text'].strip() for u in units): raise ValueError('没有提取到正文，图片书请先识别文字后再添加。')
    if len(units)>10000 or sum(len(u['text']) for u in units)>MAX_TEXT: raise ValueError('正文过长，请分卷后添加。')
    for i,u in enumerate(units): u['index']=i+1
    if any(not u['text'].strip() for u in units): warnings.append('部分章节没有可提取文字，请对照原书检查。')
    return {'title':title.strip()[:200], 'units':units, 'sourceFormat':ext, 'warnings':warnings}
