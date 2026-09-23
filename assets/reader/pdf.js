window.readingPdf=(()=>{
 const ROOT=new URL('reader/pdfjs/',location.href),DB='bela-portable-pdf-files-v1';
 const view=document.getElementById('pdf-reader'),stage=document.getElementById('pdf-stage'),paper=document.getElementById('pdf-paper'),message=document.getElementById('pdf-message');
 let dbPromise,libPromise,hooks={},doc=null,job=null,paintJob=null,textJob=null,version=0,pageVersion=0,currentId=null,page=1,fingerprint=null,textBook=null;
 const annotations=window.readingAnnotations.reader(view,paint);
 const assets={cMapUrl:new URL('cmaps/',ROOT).href,cMapPacked:true,standardFontDataUrl:new URL('standard_fonts/',ROOT).href,wasmUrl:new URL('wasm/',ROOT).href,isEvalSupported:false,enableXfa:false,enableScripting:false};
 function library(){return libPromise??=import(new URL('pdf.min.mjs',ROOT).href).then(lib=>{lib.GlobalWorkerOptions.workerSrc=new URL('pdf.worker.min.mjs',ROOT).href;return lib})}
 function database(){return dbPromise??=new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>r.result.createObjectStore('files',{keyPath:'id'});r.onsuccess=()=>{r.result.onversionchange=()=>r.result.close();resolve(r.result)};r.onerror=()=>{dbPromise=null;reject(r.error)}})}
 async function request(mode,action){const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('files',mode),r=action(tx.objectStore('files'));let result;r.onsuccess=()=>result=r.result;tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error||Error('无法写入文件库'));tx.onabort=()=>reject(tx.error||Error('无法写入文件库'))})}
 async function list(){const rows=await request('readonly',s=>s.getAll());return rows.map(({blob,units,...meta})=>meta)}
 function get(id){return request('readonly',s=>s.get(id))}
 async function addText(file){
  if(file.size>60*1024*1024)throw Error('文件超过 60 MB，请分卷后添加');
  const ext=file.name.split('.').pop().toLowerCase();
  if(!['epub','mobi','txt','md','markdown'].includes(ext))throw Error('支持 PDF、EPUB、MOBI、TXT 和 Markdown');
  const bytes=await file.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join(''),id='text:'+hash;
  const previous=await get(id);if(previous)return {duplicate:true,meta:previous};
  let status;try{const r=await fetch('/api/status');if(!r.ok)throw Error();status=await r.json()}catch{throw Error('请先启动本地读书服务，再添加电子书。')}
  let r;try{r=await fetch('/api/import-book?format='+ext,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Book-Token':status.token},body:bytes,signal:AbortSignal.timeout(210000)})}catch{throw Error('转换服务中断或超时，请确认本地服务正在运行，再重试。')}
  const data=await r.json();if(!r.ok)throw Error(data.error||'电子书无法读取');
  const meta={id,title:data.title||file.name.replace(/\.[^.]+$/,'').slice(0,200),hash,pageCount:data.units.length,size:file.size,sourceFormat:ext,addedAt:new Date().toISOString(),warnings:data.warnings};
  await request('readwrite',store=>store.put({...meta,units:data.units,blob:file.slice()}));return {duplicate:false,meta};
 }
 async function add(file,builtinHash){
  if(!/\.pdf$/i.test(file.name))return addText(file);
  if(!/\.pdf$/i.test(file.name)||file.size<5)throw Error('请选择有效的 PDF 文件');
  if(file.size>100*1024*1024)throw Error('文件超过 100 MB，请分卷后添加');
  const head=new TextDecoder('latin1').decode(await file.slice(0,1024).arrayBuffer());if(!head.includes('%PDF-'))throw Error('文件内容不是 PDF');
  const bytes=await file.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  const id=hash===builtinHash?'isbn:9787521741124':'pdf:'+hash;
  if(await get(id))return {duplicate:true,meta:(await get(id))};
  const lib=await library(),task=lib.getDocument({...assets,data:new Uint8Array(bytes)});let pdf;
  try{pdf=await task.promise;const meta={id,title:file.name.replace(/\.pdf$/i,'').slice(0,200),hash,pageCount:pdf.numPages,size:file.size,addedAt:new Date().toISOString()};await request('readwrite',s=>s.put({...meta,blob:file.slice(0,file.size,'application/pdf')}));return {duplicate:false,meta}}
  catch(error){if(error.name==='PasswordException')throw Error('文件有密码，请先解密再添加');if(error.name==='InvalidPDFException')throw Error('PDF 内容损坏或不完整');throw error}
  finally{await task.destroy()}
 }
 async function extract(record,onProgress,signal){
  const saved=await get(record.id);if(!saved)throw Error('当前浏览器没有原书文件，请先重新添加同一份文件。');if(saved.units){if(signal.aborted)throw new DOMException('取消','AbortError');onProgress(saved.units.length,saved.units.length);return {units:saved.units}}
  const lib=await library(),task=lib.getDocument({...assets,data:new Uint8Array(await saved.blob.arrayBuffer())});
  try{const source=await task.promise,units=[];for(let n=1;n<=source.numPages;n++){if(signal.aborted)throw new DOMException('取消','AbortError');const p=await source.getPage(n),content=await p.getTextContent();let text='';for(const item of content.items)if(typeof item.str==='string')text+=item.str+(item.hasEOL?'\n':' ');units.push({index:n,text});p.cleanup();onProgress(n,source.numPages)}return {units}}
  finally{await task.destroy()}
 }
 function buttons(loading=false){const n=textBook?.units.length||doc?.numPages||0;document.getElementById('pdf-prev').disabled=loading||page<=1;document.getElementById('pdf-next').disabled=loading||page>=n;document.getElementById('pdf-page').disabled=loading;document.querySelector('#pdf-page-form button').disabled=loading;document.getElementById('pdf-page').value=page;document.getElementById('pdf-page').max=n||1;document.getElementById('pdf-pages').textContent='/ '+(n||'—')+(textBook?' 节':' 页')}
 async function paint(target,save=true){
  if(textBook){
   if(!await annotations.flush())return;annotations.invalidate();
   page=Math.max(1,Math.min(textBook.units.length,Number(target)||1));buttons();
   const unit=textBook.units[page-1],article=document.createElement('article'),heading=document.createElement('h3'),body=document.createElement('div'),note=document.createElement('p');
   article.className='ebook-text-page';heading.textContent=unit.title;body.className='ebook-text-body';body.textContent=(unit.text.startsWith(unit.title+'\n')?unit.text.slice(unit.title.length).trimStart():unit.text)||'这一节没有可提取的文字，请对照原书查看图片。';note.className='ebook-text-note';note.textContent='文字阅读版 · 保留正文，图片与原版式请在原书中查看。';article.append(note,heading,body);paper.replaceChildren(article);message.hidden=true;
   if(save)stage.scrollTop=0;revealContent(paper);if(save)hooks.page?.(currentId,page,textBook.units.length);await annotations.attach({bookId:currentId,fingerprint:textBook.hash,page,holder:article,body,text:true});return;
  }
  if(!doc||!await annotations.flush())return;annotations.invalidate();page=Math.max(1,Math.min(doc.numPages,Number(target)||1));const token=++pageVersion,loadedDoc=doc,loadedId=currentId;paintJob?.cancel();textJob?.cancel();buttons();
  try{const lib=await library(),p=await loadedDoc.getPage(page);if(token!==pageVersion||doc!==loadedDoc)return;
   const natural=p.getViewport({scale:1}),width=Math.max(200,Math.min(stage.clientWidth-40,1060)),scale=width/natural.width*Number(document.getElementById('pdf-zoom').value),viewport=p.getViewport({scale});
   const holder=document.createElement('div');holder.className='pdf-page-surface';holder.style.width=viewport.width+'px';holder.style.height=viewport.height+'px';holder.style.setProperty('--total-scale-factor',scale);
   const canvas=document.createElement('canvas'),ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.floor(viewport.width*ratio);canvas.height=Math.floor(viewport.height*ratio);canvas.style.width=viewport.width+'px';canvas.style.height=viewport.height+'px';canvas.setAttribute('aria-hidden','true');holder.append(canvas);
   paintJob=p.render({canvasContext:canvas.getContext('2d'),viewport,transform:ratio===1?null:[ratio,0,0,ratio,0,0]});await paintJob.promise;if(token!==pageVersion||doc!==loadedDoc)return;
   const layer=document.createElement('div');layer.className='textLayer';holder.append(layer);textJob=new lib.TextLayer({textContentSource:p.streamTextContent(),container:layer,viewport});await textJob.render();if(token!==pageVersion)return;
   paper.replaceChildren(holder);message.hidden=true;if(save)stage.scrollTop=0;revealContent(paper);if(save)hooks.page?.(loadedId,page,doc.numPages);await annotations.attach({bookId:loadedId,fingerprint,page,holder,viewport});
  }catch(e){if(token!==pageVersion||e.name==='RenderingCancelledException'||e.name==='AbortException')return;message.hidden=false;message.textContent='这一页暂时无法显示，请切换页面或重新打开。'}
 }
 async function open(record){
  if(!await annotations.reset())return;
  const token=++version;++pageVersion;paintJob?.cancel();textJob?.cancel();job?.destroy();doc=null;textBook=null;currentId=record.id;page=record.pdfPage||1;
  document.getElementById('pdf-title').textContent=record.title;paper.replaceChildren();message.hidden=false;message.textContent='正在打开原书…';setFinished(Boolean(record.originalFinishedAt));buttons(true);window.readingModal.show(view);
  try{const saved=await get(record.id);if(token!==version)return;
   textBook=saved?.units?saved:null;view.classList.toggle('text-book-reader',Boolean(textBook));
   document.getElementById('pdf-zoom').hidden=Boolean(textBook);document.getElementById('pdf-marks').hidden=false;
   document.getElementById('pdf-prev').textContent=textBook?'上一节':'上一页';document.getElementById('pdf-next').textContent=textBook?'下一节':'下一页';
   document.getElementById('pdf-prev').setAttribute('aria-label',textBook?'上一节':'上一页');document.getElementById('pdf-next').setAttribute('aria-label',textBook?'下一节':'下一页');document.getElementById('pdf-page').setAttribute('aria-label',textBook?'跳转到原书分节':'跳转到 PDF 页序');
   if(textBook){if(record.annotationId)annotations.focus(record.annotationId);await paint(page);return}
   const lib=await library();if(token!==version)return;
   if(!saved)throw Error('missing');
   const options={data:new Uint8Array(await saved.blob.arrayBuffer())};if(token!==version)return;
   job=lib.getDocument({...assets,...options});const loaded=await job.promise;if(token!==version){loaded.destroy();return}doc=loaded;fingerprint=saved.hash;if(!fingerprint)throw Error('missing');if(record.annotationId)annotations.focus(record.annotationId);page=Math.min(page,doc.numPages);await paint(page);
  }catch(e){if(token!==version)return;message.hidden=false;message.textContent=e.message==='missing'?'当前浏览器没有这本原书文件，请返回书架重新添加同一文件，阅读记录会保留。':e.name==='PasswordException'?'这份 PDF 需要密码，请先解密再添加。':'这份原书暂时无法打开，请返回书架重新添加文件。';buttons(true)}
 }
 function setFinished(done){const b=document.getElementById('pdf-finish');b.textContent=done?'原书已读完':'读完了';b.setAttribute('aria-pressed',String(done))}
 async function close(){if(!await annotations.reset())return;++version;++pageVersion;paintJob?.cancel();textJob?.cancel();job?.destroy();doc=null;textBook=null;job=null;window.readingModal.close(view,()=>{paper.replaceChildren();hooks.back?.()})}
 document.getElementById('pdf-back').addEventListener('click',close);view.addEventListener('cancel',e=>{e.preventDefault();close()});
 document.getElementById('pdf-zoom').addEventListener('change',()=>paint(page,false));
 document.getElementById('pdf-prev').addEventListener('click',()=>paint(page-1));document.getElementById('pdf-next').addEventListener('click',()=>paint(page+1));
 document.getElementById('pdf-page-form').addEventListener('submit',e=>{e.preventDefault();paint(document.getElementById('pdf-page').value)});
 document.getElementById('pdf-finish').addEventListener('click',()=>{if(currentId)hooks.finish?.(currentId)});
 view.addEventListener('keydown',e=>{if(e.target.closest('input,button,textarea,.annotation-panel')||e.altKey||e.ctrlKey||e.metaKey)return;if(e.key==='ArrowRight'){e.preventDefault();paint(page+1)}if(e.key==='ArrowLeft'){e.preventDefault();paint(page-1)}});
 let resize;window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>{if(view.open&&doc)paint(page,false);else if(view.open&&textBook)annotations.redraw()},150)});
 return {configure(value){hooks=value},add,list,get,extract,open,setFinished,isOpen:()=>view.open};
})();
