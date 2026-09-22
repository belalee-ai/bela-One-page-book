// Pure boundary checks; IndexedDB and rendering are checked separately in a browser.
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const window={},ctx=vm.createContext({window,Intl,Date,Number,Array,Map,Set,Error,Promise,Event});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../assets/reader/annotations.js'),'utf8'),ctx);
const api=window.readingAnnotations,hash='a'.repeat(64),base={id:'test-one',bookId:'pdf:'+hash,fingerprint:hash,page:1,text:'Original sample',rects:[[1,2,40,20]],note:'',style:'underline',deleted:false,createdAt:100,updatedAt:100};
(async()=>{
 assert.equal(api.validate([base]).length,1);
 const invalid=[{...base,bookId:'pdf:'+'b'.repeat(64)},{...base,createdAt:200},{...base,page:0},{...base,page:1.2},{...base,rects:[[0,1,0,2]]},{...base,rects:[[0,1,Infinity,2]]},{...base,note:'x'.repeat(6001)},{...base,text:''},{...base,id:'__proto__'},{...base,style:'script'}];
 for(const value of invalid)assert.throws(()=>api.validate([value]));
 assert.throws(()=>api.validate([base,base]));
 for(const patch of [{bookId:'pdf:'+'b'.repeat(64)},{fingerprint:'b'.repeat(64)},{createdAt:200},{id:'changed'}])await assert.rejects(api.update(base.id,patch));
 console.log('16 annotation boundary checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
