// Optional PDF reader. All files and notes remain in this browser.
(()=>{
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n};
 const view=document.getElementById('pdf-reader');
 window.readingModal={show:d=>d.showModal(),close:(d,done)=>{d.close();done?.()}};
 let dispose=()=>{},mountVersion=0,activePdf=null,opening=false;
 const positionKey=KEY+'-pdf-pages';
 let positions={};try{const p=JSON.parse(localStorage.getItem(positionKey)||'{}');if(p&&typeof p==='object'&&!Array.isArray(p))for(const [id,n]of Object.entries(p))if(/^pdf:[a-f0-9]{64}$/.test(id)&&Number.isSafeInteger(n)&&n>0)positions[id]=n}catch{}
 const belongs=(file,book)=>file.hash?.slice(0,24)===book.id&&(!book.source_sha256||book.source_sha256===file.hash);
 readingPdf.configure({page:(id,p)=>{positions[id]=p;try{localStorage.setItem(positionKey,JSON.stringify(positions))}catch{}},finish:()=>{if(activePdf){record().originalDone=!record().originalDone;save();readingPdf.setFinished(record().originalDone)}}});
 async function openFile(file,book,page,annotationId){if(opening||current.id!==book.id)return;opening=true;try{activePdf=file;await readingPdf.open({id:file.id,title:book.guide.title,pdfPage:page||positions[file.id]||1,annotationId,originalFinishedAt:record().originalDone})}finally{opening=false}}
 function backupControls(){
  const exp=document.getElementById('export'),imp=document.getElementById('backup');if(!exp||!imp)return;
  exp.textContent='导出进度与标注';document.getElementById('import').textContent='导入进度与标注';
  exp.onclick=async()=>{try{const data={version:2,progress:state,annotations:await readingAnnotations.all()},url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=el('a');a.href=url;a.download='一页读书-进度与标注.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch{const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'})),a=el('a');a.href=url;a.download='一页读书-仅阅读进度-不含标注.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('notice').textContent='无法读取标注：本次仅导出阅读进度，不含标注，请检查浏览器存储。'}};
  imp.onchange=async e=>{const notice=document.getElementById('notice');try{const f=e.target.files[0];if(!f)return;if(f.size>16*1024*1024)throw Error('备份不能超过 16 MB');const data=JSON.parse(await f.text());if(![1,2].includes(data.version))throw Error('这不是便携版备份；本地书架旧版备份请在原书架恢复');const incoming=cleanState(data.version===2?data.progress:data),marks=data.version===2?readingAnnotations.validate(data.annotations):[];
   const next=cleanState(state);for(const [id,r]of Object.entries(incoming.records)){const old=next.records[id];next.records[id]=old?{...r,started:old.started||r.started,done:old.done||r.done,originalDone:old.originalDone||r.originalDone}:r}
   const before=localStorage.getItem(KEY);if(data.version===1)localStorage.setItem(KEY,JSON.stringify(next));else await readingAnnotations.merge(marks,()=>localStorage.setItem(KEY,JSON.stringify(next)),()=>{if(before===null)localStorage.removeItem(KEY);else localStorage.setItem(KEY,before)});state=next;updateStatus();notice.textContent='进度与标注已合并；原书文件需单独添加。';
  }catch(err){notice.textContent='导入失败：'+err.message}finally{e.target.value=''}};
 }
 async function mount(){
  document.getElementById('source-pdf-link')?.remove();const v=++mountVersion,book=current;dispose();dispose=()=>{};document.getElementById('portable-pdf-tools')?.remove();backupControls();
  // Do not reveal book-specific annotations before the spoiler gate is opened.
  if(!document.getElementById('synopsis')||book.source_format!=='pdf')return;
  const tools=el('div'),open=el('button','打开 PDF 原书'),add=el('button','添加这本 PDF'),hint=el('p'),input=el('input');tools.id='portable-pdf-tools';tools.className='actions';hint.className='annotation-muted';hint.style.flexBasis='100%';hint.setAttribute('role','status');input.type='file';input.accept='.pdf,application/pdf';input.hidden=true;tools.append(open,add,hint,input);document.querySelector('#main .actions').after(tools);
  if(location.protocol==='file:'||!window.isSecureContext||!window.indexedDB||!crypto.subtle||typeof HTMLDialogElement==='undefined'){open.disabled=add.disabled=true;hint.textContent='PDF 划线需要本地阅读服务和现代浏览器。请运行同目录的 start_reader.py，再打开显示的地址；现在仍可阅读导览和出处片段。';return}
  let file;try{file=(await readingPdf.list()).find(f=>belongs(f,book))}catch{hint.textContent='浏览器存储不可用，请换普通窗口或允许网站保存数据。';open.disabled=add.disabled=true;return}if(v!==mountVersion)return;
  const showExcerpts=()=>{dispose();dispose=()=>{};if(!file)return;dispose=readingAnnotations.excerptSection(file.id,document.getElementById('quotes')||document.getElementById('map'),m=>'#annotation-'+m.id)||(()=>{});document.getElementById('my-excerpts').addEventListener('click',e=>{const link=e.target.closest('a[data-annotation]');if(!link)return;e.preventDefault();readingAnnotations.list(file.id).then(rows=>{const mark=rows.find(m=>m.id===link.dataset.annotation);if(mark)openFile(file,book,mark.page,mark.id)})})};
  open.disabled=!file;hint.textContent=file?'选中文字即可划线、标重点、写笔记；自动保存到此浏览器。':'添加生成这份导览时使用的同一份 PDF，即可划线和记笔记。';showExcerpts();
  document.querySelectorAll('#main [data-source]').forEach(button=>button.addEventListener('click',()=>{
   document.getElementById('source-pdf-link')?.remove();const source=book.sources.find(s=>s.id===button.dataset.source);if(!file||!Number.isInteger(source?.unit))return;
   const jump=el('button','在 PDF 中打开此页');jump.id='source-pdf-link';jump.onclick=()=>{document.getElementById('source').close();openFile(file,book,source.unit)};document.getElementById('source').append(jump);
  }));
  open.onclick=()=>openFile(file,book);add.onclick=()=>input.click();
  input.onchange=async()=>{const selected=input.files[0];input.value='';if(!selected)return;add.disabled=true;try{if(selected.size>100*1024*1024)throw Error('PDF 超过 100 MB，请分卷');const bytes=await selected.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(!belongs({hash},book))throw Error('这不是生成当前导览时的同一份 PDF，请切换到对应导览');const result=await readingPdf.add(selected);if(v!==mountVersion)return;file=result.meta;open.disabled=false;hint.textContent='原书已保存到此浏览器，可以开始标注。';showExcerpts();await openFile(file,book)}catch(err){if(v===mountVersion)hint.textContent=err.message||'原书添加失败，请检查文件和浏览器'}finally{add.disabled=false}};
 }
 // render() announces after changing books or unlocking spoilers, avoiding a DOM-wide observer.
 window.addEventListener('book-rendered',mount);mount();
})();
