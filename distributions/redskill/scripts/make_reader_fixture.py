"""Create an original two-page PDF and its explicit test-only guide, without dependencies."""
from pathlib import Path
import hashlib,json,copy
import booktool as b
HERE=Path(__file__).resolve().parent.parent/'examples/reader'
def main():
    HERE.mkdir(parents=True,exist_ok=True)
    texts=['Read one page. Keep one question. Return when you are ready.','A bookmark remembers the place. A note remembers the thought.']
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for i,t in enumerate(texts):
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {5+i*2} 0 R >>'.encode())
        content=f'BT /F1 16 Tf 48 700 Td ({t}) Tj ET'.encode();objects.append(b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    pdf=b'%PDF-1.4\n'; offsets=[0]
    for n,obj in enumerate(objects,1):offsets.append(len(pdf));pdf+=f'{n} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()+b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets[1:])+f'trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    (HERE/'reading-demo.pdf').write_bytes(pdf);sha=hashlib.sha256(pdf).hexdigest()
    source={'id':sha[:24],'sha256':sha,'title':'阅读与书签 · 原创测试','format':'pdf','warnings':[],'units':[{'id':i+1,'label':f'PDF 文件第 {i+1} 页','text':t} for i,t in enumerate(texts)]}
    nodes=[{'title':'从一页开始','text':'原文邀请读者读一页、留一个问题，准备好时再回来。','units':[1],'evidence':[{'unit':1,'text':texts[0]}]},{'title':'留住位置和想法','text':'书签记住位置，笔记记住想法。','units':[2],'evidence':[{'unit':2,'text':texts[1]}]}]
    guide={'title':source['title'],'author':'一页读书 · 原创验收文本','intro':'两页短文，用于检验阅读器与标注功能，不是真实出版物。','coverage':'完整覆盖两页原创测试文本。','scope':'full','spoilers':False,'synopsis':nodes,'map':nodes,'routes':nodes,'diagrams':[{'title':'阅读与记录','type':'sequence','nodes':nodes}],'quotes':[{'text':texts[0],'context':'第一页的阅读邀请。','unit':1}]}
    ledger=b.new_reading(source)
    for row,t in zip(ledger['units'],texts):row.update(status='read',note=t)
    review=b.new_review(guide,source,ledger)
    review['semantic']={'status':'reviewed','notes':'仅此固定原创验收样例：第一页对应读一页、留问题、准备好再回来；第二页对应书签记位置、笔记记想法。逐项一致。'}
    review['spoiler_check']={'status':'reviewed','notes':'两句原创阅读提示，无故事结局。仅适用于此固定测试材料。'}
    for name,value in [('source',source),('guide',guide),('review',review)]:b.write_json(HERE/(name+'.json'),value)
if __name__=='__main__':main()
