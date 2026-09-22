// Pure state tests with a minimal DOM stub; these are NOT browser visual tests.
const vm=require('node:vm'), fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const code=fs.readFileSync(path.join(__dirname,'../assets/app.js'),'utf8');
const n={title:'主题',text:'说明',units:[1],sourceRefs:['ref-1']}, book={id:'demo',title:'原始书名',verification:'测试',guide:{title:'测试',author:'测试',intro:'测试',coverage:'测试',coverage_status:'全书导览',scope:'full',spoilers:false,synopsis:[n],map:[n],diagrams:[{title:'图',type:'topics',nodes:[n,n]}],quotes:[],routes:[n]},warnings:[],sources:[{id:'ref-1',label:'第一章',text:'原文'}]};
function setup(fail=false){const elements={};const get=id=>elements[id]||(elements[id]={textContent:'',value:'',dataset:{},setAttribute(){},querySelectorAll(){return[]},scrollIntoView(){},tagName:'SECTION',focus(){},close(){}});get('books-data').textContent=JSON.stringify([book]);const ctx=vm.createContext({window:{dispatchEvent(){}},Event,document:{getElementById:get,documentElement:{dataset:{}}},localStorage:{getItem(){return null},setItem(){if(fail)throw Error('blocked')},removeItem(){}},matchMedia(){return{matches:true}},JSON,Number,String,Array,Error,Object,Blob,setTimeout,URL});vm.runInContext(code,ctx);return {ctx,get,read:x=>vm.runInContext(x,ctx)};}
(async()=>{
const t=setup();assert.equal(t.get('start').textContent,'开始读');t.get('start').onclick();assert.equal(t.get('start').textContent,'继续读');
t.get('done').onclick();assert.equal(t.read('record().done'),true);assert.equal(t.read('record().originalDone'),false);
t.get('original').onclick();assert.equal(t.read('record().originalDone'),true);
await t.get('backup').onchange({target:{files:[{size:100,text:async()=>JSON.stringify({version:1,records:{demo:{started:false,done:false,originalDone:false,section:'map-0'}}})}],value:'x'}});
assert.equal(t.read('record().done'),true);assert.equal(t.read('record().originalDone'),true);
assert.throws(()=>t.read('cleanState({version:2,records:{}})'));
assert.throws(()=>t.read('cleanState({version:1,records:{demo:{done:"yes"}}})'));
const bad=setup(true);bad.get('start').onclick();assert.match(bad.get('notice').textContent,/无法持久保存/);assert.equal(bad.read('record().started'),true);
assert.equal(t.read('esc("<img>")'),'&lt;img&gt;');
assert.match(bad.get('notice').textContent,/无法持久保存/);
assert.throws(()=>t.read('cleanState(JSON.parse(\'{"version":1,"records":{"__proto__":{"started":true,"done":false,"originalDone":false,"section":"map"}}}\'))'));
// Deliberately place spoiler markers in every generated surface.
t.read("current.guide.spoilers=true;current.guide.title='SECRET_TITLE';current.guide.intro='SECRET_INTRO';current.guide.coverage='SECRET_COVERAGE';current.guide.synopsis[0].title='SECRET_NODE';render()");
assert.doesNotMatch(t.get('main').innerHTML,/SECRET_/);
t.get('start').onclick();assert.doesNotMatch(t.get('main').innerHTML,/SECRET_/);
t.get('reveal').onclick();assert.match(t.get('main').innerHTML,/SECRET_INTRO/);
assert.match(t.get('main').innerHTML,/SECRET_NODE/);
console.log('13 state/render invariant groups passed (not browser visual tests).');
})().catch(e=>{console.error(e);process.exit(1)});
