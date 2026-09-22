// Local PDF annotations. No framework, network service, or modification of the original file.
window.readingAnnotations=(()=>{
 'use strict';
 const DB='bela-pdf-annotations-v1',LIMIT=10000;let connection;
 let channel=null;try{if(typeof BroadcastChannel==='function')channel=new BroadcastChannel(DB)}catch{}
 function announce(){window.dispatchEvent(new Event('annotations-changed'));channel?.postMessage('changed')}
 if(channel)channel.onmessage=()=>window.dispatchEvent(new Event('annotations-changed'));
 function database(){return connection??=new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>{const s=r.result.createObjectStore('marks',{keyPath:'id'});s.createIndex('bookId','bookId')};r.onsuccess=()=>{r.result.onversionchange=()=>{r.result.close();connection=null};resolve(r.result)};r.onblocked=()=>{connection=null;reject(Error('请关闭其他旧版阅读窗口后重试'))};r.onerror=()=>{connection=null;reject(r.error)}})}
 function validate(rows){
  if(!Array.isArray(rows)||rows.length>LIMIT)throw Error('标注数量不正确');const seen=new Set();
  return rows.map(m=>{
   if(!m||typeof m.id!=='string'||!/^[a-z0-9-]{1,80}$/i.test(m.id)||seen.has(m.id)||typeof m.bookId!=='string'||!(/^(pdf:[a-f0-9]{64}|isbn:9787521741124)$/.test(m.bookId))||typeof m.fingerprint!=='string'||!/^[a-f0-9]{64}$/.test(m.fingerprint))throw Error('标注身份不正确');seen.add(m.id);
   if(!Number.isInteger(m.page)||m.page<1||m.page>100000||!['highlight','underline'].includes(m.style)||typeof m.text!=='string'||!m.text.trim()||m.text.length>8000||typeof m.note!=='string'||m.note.length>6000||typeof m.deleted!=='boolean'||![m.createdAt,m.updatedAt].every(v=>Number.isSafeInteger(v)&&v>0&&v<=8640000000000000))throw Error('标注内容不正确');
   if((m.bookId.startsWith('pdf:')&&m.bookId!=='pdf:'+m.fingerprint)||m.updatedAt<m.createdAt)throw Error('标注身份或日期不一致');
   if(!Array.isArray(m.rects)||!m.rects.length||m.rects.length>250||m.rects.some(r=>!Array.isArray(r)||r.length!==4||r.some(v=>!Number.isFinite(v)||Math.abs(v)>100000)||r[0]===r[2]||r[1]===r[3]))throw Error('标注位置不正确');
   return {id:m.id,bookId:m.bookId,fingerprint:m.fingerprint,page:m.page,style:m.style,text:m.text,note:m.note,deleted:m.deleted,createdAt:m.createdAt,updatedAt:m.updatedAt,rects:m.rects.map(r=>r.slice())};
  });
 }
 async function all(){const db=await database();return new Promise((resolve,reject)=>{const r=db.transaction('marks').objectStore('marks').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
 async function list(bookId){return (await all()).filter(m=>m.bookId===bookId&&!m.deleted).sort((a,b)=>a.page-b.page||a.createdAt-b.createdAt)}
 async function put(mark){validate([mark]);const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('marks','readwrite'),s=tx.objectStore('marks');let saved;const r=s.get(mark.id);r.onsuccess=()=>{const prev=r.result;if(prev&&(prev.bookId!==mark.bookId||prev.fingerprint!==mark.fingerprint||prev.createdAt!==mark.createdAt)){tx.abort();return}const count=s.count();count.onsuccess=()=>{if(!prev&&count.result>=LIMIT){tx.abort();return}saved={...mark,updatedAt:Math.max(Date.now(),(prev?.updatedAt||0)+1)};s.put(saved)}};tx.oncomplete=()=>{announce();resolve(saved)};tx.onabort=tx.onerror=()=>reject(tx.error||Error('标注保存失败'))})}
 async function update(id,patch){if(!patch||Object.keys(patch).some(k=>!['note','style','deleted'].includes(k)))throw Error('不能修改标注身份或首次日期');const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('marks','readwrite'),s=tx.objectStore('marks');let saved;const r=s.get(id);r.onsuccess=()=>{try{if(!r.result)throw Error();saved={...r.result,...patch,updatedAt:Math.max(Date.now(),r.result.updatedAt+1)};validate([saved]);s.put(saved)}catch{tx.abort()}};tx.oncomplete=()=>{announce();resolve(saved)};tx.onabort=tx.onerror=()=>reject(tx.error||Error('标注保存失败'))})}
 async function merge(rows,apply=()=>{},rollback=()=>{}){
  rows=validate(rows);const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('marks','readwrite'),s=tx.objectStore('marks');let applied=false;const r=s.getAll();r.onsuccess=()=>{try{const result=new Map(r.result.map(m=>[m.id,m]));for(const m of rows){const old=result.get(m.id);if(old&&(old.bookId!==m.bookId||old.fingerprint!==m.fingerprint||old.createdAt!==m.createdAt))throw Error();if(!old||m.updatedAt>old.updatedAt)result.set(m.id,m)}if(result.size>LIMIT)throw Error();for(const m of result.values())s.put(m);apply();applied=true}catch{tx.abort()}};tx.oncomplete=()=>{announce();resolve()};tx.onabort=tx.onerror=()=>{if(applied)rollback();reject(tx.error||Error('备份未导入'))}})
 }
 function element(tag,cls,text){const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=text;return el}
 function button(text,action){const b=element('button','',text);b.type='button';b.onclick=action;return b}
 const annotationDate=new Intl.DateTimeFormat('zh-CN',{year:'numeric',month:'long',day:'numeric'});
 function createdTime(mark){const date=new Date(mark.createdAt),time=element('time','annotation-muted annotation-created','标注于 '+annotationDate.format(date));time.dateTime=date.toISOString();return time}
 function excerptSection(bookId,after,urlFor){
  if(!after||!bookId.startsWith('pdf:')&&bookId!=='isbn:9787521741124')return;
  const section=element('section','personal-excerpts');section.id='my-excerpts';
  const heading=element('h2','','我的摘录与笔记'),hint=element('p','annotation-muted'),content=element('div','excerpt-cards');
  let expanded=false,version=0,foldAnimation;const lifecycle=new AbortController();
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  const more=button('查看全部',()=>{expanded=!expanded;if(!expanded&&section.getBoundingClientRect().top<0)section.scrollIntoView({block:'start',behavior:reduce.matches?'instant':'smooth'});refresh(true)});
  more.hidden=true;more.setAttribute('aria-expanded','false');content.id='personal-excerpt-cards';more.setAttribute('aria-controls',content.id);
  section.append(heading,hint,content,more);after.after(section);
  async function refresh(animate=false){
   const token=++version;
   try{
    const marks=(await list(bookId)).sort((a,b)=>b.updatedAt-a.updatedAt||b.createdAt-a.createdAt||a.id.localeCompare(b.id));if(token!==version||lifecycle.signal.aborted)return;
    const before=content.getBoundingClientRect().height;foldAnimation?.cancel();content.style.overflow='';
    hint.textContent=marks.length?marks.length+' 条 · 按最近更新时间排列':'在原书里选一段喜欢的话，它会留在这里。';
    content.replaceChildren();
    for(const m of marks.slice(0,expanded?marks.length:4)){
     const card=element('article','excerpt-card');
     card.append(element('small','annotation-muted','PDF 第 '+m.page+' 页 · '+(m.style==='underline'?'划线':'重点')),element('blockquote','',m.text));
     if(m.note){const note=element('details','excerpt-note');note.append(element('summary','','我的笔记'),element('p','',m.note));card.append(note)}
     const a=element('a','excerpt-source','回到原文');a.href=urlFor(m);a.dataset.annotation=m.id;card.append(createdTime(m),a);content.append(card);
    }
    more.hidden=marks.length<=4;more.textContent=expanded?'收起，只看最新 4 条':'查看全部 '+marks.length+' 条';more.setAttribute('aria-expanded',String(expanded));
    if(animate&&!reduce.matches){const after=content.getBoundingClientRect().height;content.style.overflow='clip';foldAnimation=content.animate([{height:before+'px'},{height:after+'px'}],{duration:260,easing:'cubic-bezier(.2,.7,.2,1)'});foldAnimation.onfinish=()=>{content.style.overflow='';foldAnimation=null}}
   }catch{hint.textContent='摘录暂时无法读取，请检查浏览器存储后重试。'}
  }
  reduce.addEventListener('change',()=>{if(reduce.matches){foldAnimation?.cancel();content.style.overflow=''}},{signal:lifecycle.signal});
  window.addEventListener('annotations-changed',()=>refresh(),{signal:lifecycle.signal});window.addEventListener('focus',()=>refresh(),{signal:lifecycle.signal});refresh();return ()=>{lifecycle.abort();foldAnimation?.cancel();section.remove()};
 }
 function reader(view,goPage){
  const paper=view.querySelector('#pdf-paper'),stage=view.querySelector('#pdf-stage');let current=null,selected=null,marks=[],editor=null,draft='',saveTimer,queue=Promise.resolve(),drawVersion=0,undo=null,pendingId=null;
  function visible(el,show){
   const target=show?'open':'closed';if(el.dataset.motion===target)return;
   const value=el.hidden?0:Number(getComputedStyle(el).opacity);el.dataset.motion=target;el.inert=!show;
   if(show){el.hidden=false;el.style.opacity=String(value)}
   const panelMotion=el.classList.contains('annotation-panel'),mobile=matchMedia('(max-width:680px)').matches;
   const paint=v=>{el.style.opacity=String(v);el.style.translate=reducedMotion.matches?'none':panelMotion&&!mobile?`${(1-v)*10}px 0`:`0 ${(1-v)*(panelMotion?12:4)}px`};
   springTo(el,value,show?1:0,paint,()=>{el.hidden=!show;el.style.opacity='';el.style.translate=''});
  }
  function markMotion(el,show){
   const value=el.hidden?0:Number(getComputedStyle(el).opacity);el.hidden=false;
   springTo(el,value,show?1:0,v=>{el.style.opacity=String(v);el.style.clipPath=!reducedMotion.matches&&el.classList.contains('underline')?`inset(0 ${(1-v)*100}% 0 0)`:'none'},()=>{if(!show)el.remove();else{el.style.opacity='';el.style.clipPath=''}});
  }
  const toolbar=element('div','annotation-selection');toolbar.hidden=true;toolbar.setAttribute('role','toolbar');toolbar.setAttribute('aria-label','标注选中文字');
  const panel=element('aside','annotation-panel');panel.hidden=true;panel.setAttribute('aria-label','本书标注');
  const panelTop=element('div','annotation-panel-top');panelTop.append(element('strong','','本书标注'),button('关闭',async()=>{if(await flush()){visible(panel,false);view.querySelector('#pdf-marks').focus({preventScroll:true})}}));
  const status=element('p','annotation-status');status.setAttribute('role','status');
  const body=element('div','annotation-body');panel.append(panelTop,status,body);view.append(toolbar,panel);
  const entry=button('本书标注',async()=>{if(await flush()){editor=null;visible(panel,true);await refresh();showList()}});entry.id='pdf-marks';view.querySelector('.pdf-top').insertBefore(entry,view.querySelector('#pdf-finish'));
  function tell(text,error=false){status.textContent=text;status.dataset.error=String(error)}
  function showPanel(){visible(panel,true);visible(toolbar,false)}
  function showList(){if(editor)return;body.replaceChildren();if(!current){body.append(element('p','','请先打开原书'));return}const valid=marks.filter(m=>m.fingerprint===current.fingerprint);body.append(element('p','annotation-muted',valid.length?'共 '+valid.length+' 条，按原书页序排列。':'选中文字后，可以划线、标重点或写笔记。扫描页需先识别文字。'));if(marks.length>valid.length)body.append(element('p','annotation-muted','另一版本的标注已保留，未绘制在这份 PDF 上。'));for(const m of valid){const row=element('article','annotation-row');row.append(button('第 '+m.page+' 页 · '+(m.style==='underline'?'划线':'重点'),async()=>{if(!await flush())return;pendingId=m.id;await goPage(m.page);openEditor(m.id)}),element('p','annotation-quote',m.text));if(m.note)row.append(element('p','annotation-muted',m.note));row.append(createdTime(m));body.append(row)}}
  function saveDraft(){clearTimeout(saveTimer);if(!editor||draft===editor.note)return queue;const id=editor.id,note=draft;tell('保存中…');queue=queue.catch(()=>{}).then(()=>update(id,{note})).then(saved=>{if(editor?.id===id){editor=saved;tell(draft===note?'已保存到此浏览器':'保存中…')}return true}).catch(()=>{tell('尚未保存，请重试；不要关闭页面。',true);return false});return queue}
  async function flush(){await saveDraft();await queue;return !editor||draft===editor.note}
  function openEditor(id){const m=marks.find(m=>m.id===id&&!m.deleted);if(!m)return;editor=m;draft=m.note;showPanel();body.replaceChildren();const text=element('textarea','annotation-note');text.maxLength=6000;text.value=draft;text.setAttribute('aria-label','这段摘录的笔记');text.placeholder='记下你此刻的想法…';text.oninput=()=>{draft=text.value;tell('保存中…');clearTimeout(saveTimer);saveTimer=setTimeout(saveDraft,450)};text.onblur=saveDraft;
   const actions=element('div','annotation-actions');for(const [style,label] of [['underline','划线'],['highlight','重点']]){const b=button(label,async()=>{if(!await flush())return;try{editor=await update(id,{style});await refresh();openEditor(id)}catch{tell('样式未保存，请重试。',true)}});b.setAttribute('aria-pressed',String(m.style===style));actions.append(b)}
   actions.append(button('移除标注',async()=>{if(!await flush())return;try{undo=await update(id,{deleted:true});editor=null;await refresh();showList();tell('已移除标注');const restore=button('撤销移除',async()=>{try{await update(undo.id,{deleted:false});undo=null;restore.remove();tell('标注已恢复');await refresh()}catch{tell('恢复失败，请重试。',true)}});body.prepend(restore)}catch{tell('移除未保存，请重试。',true)}}));
   const retry=button('重试保存',saveDraft);retry.className='annotation-retry';body.append(button('全部标注',async()=>{if(await flush()){editor=null;showList()}}),element('p','annotation-muted','PDF 第 '+m.page+' 页'),createdTime(m),element('blockquote','annotation-quote',m.text),text,actions,button('完成',async()=>{if(await flush()){visible(panel,false);editor=null;entry.focus({preventScroll:true})}}),retry);tell('已保存到此浏览器');
  }
  async function create(style,withNote=false){const target=selected;if(!target||!current||target.token!==current.token)return;visible(toolbar,false);try{if(!await flush())return;const time=Date.now();const same=marks.find(m=>!m.deleted&&m.bookId===target.bookId&&m.fingerprint===target.fingerprint&&m.page===target.page&&m.text===target.text&&JSON.stringify(m.rects)===JSON.stringify(target.rects));const mark=same||await put({id:crypto.randomUUID(),bookId:target.bookId,fingerprint:target.fingerprint,page:target.page,text:target.text,rects:target.rects,note:'',style,deleted:false,createdAt:time,updatedAt:time});getSelection()?.removeAllRanges();selected=null;await refresh();if(withNote){openEditor(mark.id);body.querySelector('textarea')?.focus()}else{tell('已保存到此浏览器');entry.textContent='本书标注 · 已保存';setTimeout(()=>entry.textContent='本书标注',1800)}}catch{showPanel();tell('标注尚未保存，请检查浏览器存储后重试。',true);body.replaceChildren(element('p','annotation-quote',target.text),button('重试保存',()=>create(style,withNote)))}}
  toolbar.append(button('划线',()=>create('underline')),button('重点',()=>create('highlight')),button('笔记',()=>create('highlight',true)));
  toolbar.addEventListener('pointerdown',e=>e.preventDefault());
  function selection(){
   selected=null;if(!current){visible(toolbar,false);return}const sel=getSelection();if(!sel||sel.isCollapsed||!sel.rangeCount){visible(toolbar,false);return}const range=sel.getRangeAt(0),layer=current.holder.querySelector('.textLayer');if(!layer.contains(range.startContainer)||!layer.contains(range.endContainer)){visible(toolbar,false);return}const text=sel.toString().trim();if(!text||text.length>8000){visible(toolbar,false);return}const box=current.holder.getBoundingClientRect(),raw=[...range.getClientRects()].filter(r=>r.width>1&&r.height>1&&r.right>box.left&&r.left<box.right&&r.bottom>box.top&&r.top<box.bottom);const rects=[];
   for(const r of raw){const a=current.viewport.convertToPdfPoint(Math.max(0,r.left-box.left),Math.max(0,r.top-box.top)),b=current.viewport.convertToPdfPoint(Math.min(box.width,r.right-box.left),Math.min(box.height,r.bottom-box.top));const v=[...a,...b].map(n=>Math.round(n*1000)/1000);if(!rects.some(x=>x.every((n,i)=>Math.abs(n-v[i])<.1)))rects.push(v)}if(!rects.length||rects.length>250){visible(toolbar,false);return}
   selected={bookId:current.bookId,fingerprint:current.fingerprint,page:current.page,token:current.token,text,rects};visible(toolbar,true);const r=range.getBoundingClientRect(),v=view.getBoundingClientRect();toolbar.style.left=Math.max(8,Math.min(r.left-v.left,view.clientWidth-toolbar.offsetWidth-8))+'px';const top=r.top-v.top-toolbar.offsetHeight-8;toolbar.style.top=Math.max(8,Math.min(top>110?top:r.bottom-v.top+8,view.clientHeight-toolbar.offsetHeight-8))+'px';
  }
  paper.addEventListener('pointerup',async e=>{selection();if(getSelection()?.isCollapsed&&current){const hit=[...current.holder.querySelectorAll('.annotation-mark')].find(el=>{const r=el.getBoundingClientRect();return e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom+5});if(hit&&!hit.dataset.retiring&&await flush())openEditor(hit.dataset.id)}});
  paper.addEventListener('keyup',selection);document.addEventListener('selectionchange',()=>{if(view.open&&current)selection()});stage.addEventListener('scroll',()=>{visible(toolbar,false)});
  function draw(){
   if(!current)return;let layer=current.holder.querySelector('.annotation-layer');const restoring=!layer;
   if(!layer){layer=element('div','annotation-layer');layer.setAttribute('aria-hidden','true');current.holder.append(layer)}
   const remaining=new Map([...layer.children].map(el=>[el.dataset.key,el]));
   for(const m of marks.filter(m=>m.page===current.page&&m.fingerprint===current.fingerprint))m.rects.forEach((rect,i)=>{
    const key=m.id+':'+i,[x1,y1,x2,y2]=[...current.viewport.convertToViewportPoint(rect[0],rect[1]),...current.viewport.convertToViewportPoint(rect[2],rect[3])];let el=remaining.get(key),fresh=!el;
    if(!el){el=element('span','annotation-mark '+m.style);el.dataset.key=key;el.dataset.id=m.id;layer.append(el)}
    remaining.delete(key);el.className='annotation-mark '+m.style;
    Object.assign(el.style,{left:Math.min(x1,x2)+'px',top:Math.min(y1,y2)+'px',width:Math.abs(x2-x1)+'px',height:Math.abs(y2-y1)+'px'});
    if(fresh&&!restoring){el.style.opacity='0';markMotion(el,true)}else if(el.dataset.retiring){delete el.dataset.retiring;markMotion(el,true)}
   });
   for(const el of remaining.values())if(!el.dataset.retiring){el.dataset.retiring='true';markMotion(el,false)}
   if(pendingId){const el=[...layer.children].find(el=>el.dataset.id===pendingId&&!el.dataset.retiring);if(el){el.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});if(!reducedMotion.matches)el.animate([{opacity:.65},{opacity:1}],{duration:320,easing:'ease-out'});pendingId=null}}
  }
  async function refresh(){if(!current)return;const token=++drawVersion,bookId=current.bookId;try{const rows=await list(bookId);if(token!==drawVersion||current?.bookId!==bookId)return;marks=rows;draw();if(!panel.hidden&&!editor)showList()}catch(error){console.error('Annotation refresh failed',error);showPanel();tell('无法读取标注，原有数据未被覆盖。',true)}}
  window.addEventListener('annotations-changed',refresh);window.addEventListener('focus',()=>{if(view.open)refresh()});
  window.addEventListener('beforeunload',e=>{if(editor&&draft!==editor.note){saveDraft();e.preventDefault();e.returnValue=''}});
  return {flush,async attach(context){current={...context,token:Symbol()};selected=null;visible(toolbar,false);await refresh()},invalidate(){current=null;selected=null;visible(toolbar,false);++drawVersion},async reset(){if(!await flush())return false;editor=null;pendingId=null;visible(panel,false);this.invalidate();return true},focus(id){pendingId=id},openNote:openEditor};
 }
 return {all,list,put,update,validate,merge,excerptSection,reader};
})();
