window.readingPdf=(()=>{
 const ROOT=new URL('reader/pdfjs/',location.href),DB='bela-portable-pdf-files-v1';
 const view=document.getElementById('pdf-reader'),stage=document.getElementById('pdf-stage'),paper=document.getElementById('pdf-paper'),message=document.getElementById('pdf-message');
 let dbPromise,libPromise,hooks={},doc=null,job=null,paintJob=null,textJob=null,version=0,pageVersion=0,currentId=null,page=1,fingerprint=null;
 const annotations=window.readingAnnotations.reader(view,paint);
 const assets={cMapUrl:new URL('cmaps/',ROOT).href,cMapPacked:true,standardFontDataUrl:new URL('standard_fonts/',ROOT).href,wasmUrl:new URL('wasm/',ROOT).href,isEvalSupported:false,enableXfa:false,enableScripting:false};
 function library(){return libPromise??=import(new URL('pdf.min.mjs',ROOT).href).then(lib=>{lib.GlobalWorkerOptions.workerSrc=new URL('pdf.worker.min.mjs',ROOT).href;return lib})}
 function database(){return dbPromise??=new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>r.result.createObjectStore('files',{keyPath:'id'});r.onsuccess=()=>{r.result.onversionchange=()=>r.result.close();resolve(r.result)};r.onerror=()=>{dbPromise=null;reject(r.error)}})}
 async function request(mode,action){const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('files',mode),r=action(tx.objectStore('files'));let result;r.onsuccess=()=>result=r.result;tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error||Error('无法写入文件库'));tx.onabort=()=>reject(tx.error||Error('无法写入文件库'))})}
 async function list(){const rows=await request('readonly',s=>s.getAll());return rows.map(({blob,...meta})=>meta)}
 function get(id){return request('readonly',s=>s.get(id))}
 async function add(file,builtinHash){
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
  const saved=await get(record.id);if(!saved)throw Error('当前浏览器没有原书文件，请先重新添加同一份 PDF。');
  const lib=await library(),task=lib.getDocument({...assets,data:new Uint8Array(await saved.blob.arrayBuffer())});
  try{const source=await task.promise,units=[];for(let n=1;n<=source.numPages;n++){if(signal.aborted)throw new DOMException('取消','AbortError');const p=await source.getPage(n),content=await p.getTextContent();let text='';for(const item of content.items)if(typeof item.str==='string')text+=item.str+(item.hasEOL?'\n':' ');units.push({index:n,text});p.cleanup();onProgress(n,source.numPages)}return {units}}
  finally{await task.destroy()}
 }
 function buttons(loading=false){const n=doc?.numPages||0;document.getElementById('pdf-prev').disabled=loading||page<=1;document.getElementById('pdf-next').disabled=loading||page>=n;document.getElementById('pdf-page').disabled=loading;document.querySelector('#pdf-page-form button').disabled=loading;document.getElementById('pdf-page').value=page;document.getElementById('pdf-page').max=n||1;document.getElementById('pdf-pages').textContent='/ '+(n||'—')+' 页'}
 async function paint(target,save=true){
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
  const token=++version;++pageVersion;paintJob?.cancel();textJob?.cancel();job?.destroy();doc=null;currentId=record.id;page=record.pdfPage||1;
  document.getElementById('pdf-title').textContent=record.title;paper.replaceChildren();message.hidden=false;message.textContent='正在打开原书…';setFinished(Boolean(record.originalFinishedAt));buttons(true);window.readingModal.show(view);
  try{const saved=await get(record.id);const lib=await library();if(token!==version)return;
   if(!saved)throw Error('missing');
   const options={data:new Uint8Array(await saved.blob.arrayBuffer())};if(token!==version)return;
   job=lib.getDocument({...assets,...options});const loaded=await job.promise;if(token!==version){loaded.destroy();return}doc=loaded;fingerprint=saved?.hash;if(!fingerprint)throw Error('missing');if(record.annotationId)annotations.focus(record.annotationId);page=Math.min(page,doc.numPages);await paint(page);
  }catch(e){if(token!==version)return;message.hidden=false;message.textContent=e.message==='missing'?'当前浏览器没有这本 PDF，请返回书架重新添加同一文件，阅读记录会保留。':e.name==='PasswordException'?'这份 PDF 需要密码，请先解密再添加。':'这份 PDF 暂时无法打开，请返回书架重新添加文件。';buttons(true)}
 }
 function setFinished(done){const b=document.getElementById('pdf-finish');b.textContent=done?'原书已读完':'读完了';b.setAttribute('aria-pressed',String(done))}
 async function close(){if(!await annotations.reset())return;++version;++pageVersion;paintJob?.cancel();textJob?.cancel();job?.destroy();doc=null;job=null;window.readingModal.close(view,()=>{paper.replaceChildren();hooks.back?.()})}
 document.getElementById('pdf-back').addEventListener('click',close);view.addEventListener('cancel',e=>{e.preventDefault();close()});
 document.getElementById('pdf-zoom').addEventListener('change',()=>paint(page,false));
 document.getElementById('pdf-prev').addEventListener('click',()=>paint(page-1));document.getElementById('pdf-next').addEventListener('click',()=>paint(page+1));
 document.getElementById('pdf-page-form').addEventListener('submit',e=>{e.preventDefault();paint(document.getElementById('pdf-page').value)});
 document.getElementById('pdf-finish').addEventListener('click',()=>{if(currentId)hooks.finish?.(currentId)});
 view.addEventListener('keydown',e=>{if(e.target.closest('input,button,textarea,.annotation-panel')||e.altKey||e.ctrlKey||e.metaKey)return;if(e.key==='ArrowRight'){e.preventDefault();paint(page+1)}if(e.key==='ArrowLeft'){e.preventDefault();paint(page-1)}});
 let resize;window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>{if(view.open&&doc)paint(page,false)},150)});
 return {configure(value){hooks=value},add,list,get,extract,open,setFinished,isOpen:()=>view.open};
})();
