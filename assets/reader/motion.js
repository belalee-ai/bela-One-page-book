// Apple Design: immediate feedback, interruptible critically damped springs.
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const liveSprings=new Set(), springStates=new WeakMap(), contentAnimations=new Map(), folds=new WeakMap();
let motionReady=false, springFrame=0, lastSpringTime=0;
function springTo(element,value,target,paint,done=()=>{},epsilon=.001){
 let state=springStates.get(element);
 if(!state){state={element,value,velocity:0};springStates.set(element,state)}
 Object.assign(state,{target,paint,done,epsilon});
 if(reducedMotion.matches){finishSpring(state);return}
 liveSprings.add(state);
 if(!springFrame){lastSpringTime=performance.now();springFrame=requestAnimationFrame(stepSprings)}
}
function finishSpring(s){
 s.value=s.target;s.velocity=0;s.paint(s.target);s.done();liveSprings.delete(s);springStates.delete(s.element);
}
function stepSprings(now){
 const dt=Math.min((now-lastSpringTime)/1000,.032);lastSpringTime=now;
 for(const s of liveSprings){
  if(!s.element.isConnected){liveSprings.delete(s);springStates.delete(s.element);continue}
  const count=Math.max(1,Math.ceil(dt/.008)),h=dt/count,omega=28;
  for(let i=0;i<count;i++){s.velocity+=(-omega*omega*(s.value-s.target)-2*omega*s.velocity)*h;s.value+=s.velocity*h}
  s.paint(s.value);
  if(Math.abs(s.value-s.target)<s.epsilon&&Math.abs(s.velocity)<s.epsilon*12)finishSpring(s);
 }
 springFrame=liveSprings.size?requestAnimationFrame(stepSprings):0;
}
function revealContent(element){
 if(!motionReady||reducedMotion.matches)return;
 const previous=contentAnimations.get(element),style=getComputedStyle(element);
 const start=previous?{opacity:style.opacity,translate:style.translate}:{opacity:.65,translate:'0 6px'};
 previous?.cancel();
 const animation=element.animate([start,{opacity:1,translate:'0 0'}],{duration:220,easing:'cubic-bezier(.2,.7,.2,1)'});
 contentAnimations.set(element,animation);
 animation.onfinish=()=>{if(contentAnimations.get(element)===animation)contentAnimations.delete(element)};
}
function isDisclosureOpen(details){return folds.get(details)?.target??details.open}
function bindDisclosures(root){
 root.querySelectorAll('details').forEach(details=>{
  if(folds.has(details))return;
  const summary=details.querySelector(':scope > summary');if(!summary)return;
  const body=document.createElement('div');body.className='fold-content';
  while(summary.nextSibling)body.append(summary.nextSibling);details.append(body);
  folds.set(details,{body,summary,target:details.open});summary.setAttribute('aria-expanded',String(details.open));
  summary.addEventListener('click',event=>{event.preventDefault();setDisclosure(details,!isDisclosureOpen(details))});
 });
}
function setDisclosure(details,open){
 const fold=folds.get(details);if(!fold){details.open=open;return}
 const {body,summary}=fold,current=details.open?body.getBoundingClientRect().height:0;
 fold.target=open;summary.setAttribute('aria-expanded',String(open));
 if(!open&&body.contains(document.activeElement))summary.focus({preventScroll:true});
 details.open=true;body.inert=!open;body.style.height='auto';
 const target=open?body.getBoundingClientRect().height:0;
 body.style.height=current+'px';body.style.overflow='clip';
 springTo(body,current,target,value=>body.style.height=Math.max(0,value)+'px',()=>{
  details.open=fold.target;body.style.height='';body.style.overflow='';body.inert=!fold.target;
 },.25);
}
const pressedControls=new Set();
function pressControl(element){
 if(!element||element.disabled)return;pressedControls.add(element);
 springTo(element,1,.975,value=>element.style.scale=String(value));
}
function releaseControls(){
 for(const element of pressedControls)springTo(element,.975,1,value=>element.style.scale=String(value),()=>element.style.removeProperty('scale'));
 pressedControls.clear();
}
document.addEventListener('pointerdown',event=>{if(event.button===0)pressControl(event.target.closest('button,.primary,.secondary'))});
document.addEventListener('pointerup',releaseControls);
document.addEventListener('pointercancel',releaseControls);
window.addEventListener('blur',releaseControls);
document.addEventListener('keydown',event=>{if(!event.repeat&&['Enter',' '].includes(event.key))pressControl(event.target.closest('button,.primary,.secondary'))});
document.addEventListener('keyup',releaseControls);
function settleMotion(){
 for(const s of [...liveSprings])finishSpring(s);
 for(const animation of contentAnimations.values())animation.cancel();contentAnimations.clear();
 releaseControls();
}
reducedMotion.addEventListener('change',()=>{if(reducedMotion.matches)settleMotion()});
window.addEventListener('resize',settleMotion);
document.addEventListener('visibilitychange',()=>{if(document.hidden)settleMotion()});
