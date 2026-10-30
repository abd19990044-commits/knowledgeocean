const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

async function check(language) {
  const states = [];
  let cursor = 0, component, tree;
  const records = Array.from({length: 10001}, (_, i) => ({title:`Water record ${i}`, doi:`10.1000/water${i}`, authors:['Test Author'], year:'2025', sources:['crossref'], abstract:'Complete abstract describing the experimental methods and results.'}));
  const context = vm.createContext({
    console, FormData, URL, Uint8Array,
    setTimeout: () => 0, clearTimeout() {},
    localStorage: {getItem: key => key === 'knowledge_ocean_lang' ? language : null, setItem() {}, removeItem() {}},
    document: {getElementById: id => id === 'root' ? {} : null},
    window: {location: {protocol:'https:', hostname:'example.hf.space'}},
    fetch: async url => ({ok:true, json:async () => url === '/api/history' ? {files:[{filename:'test.zip',query:'Water collection',download_url:'/test.zip'}]} : {ok:true, data:{papers:records, query:'Water collection', with_abstracts:true, file_type:'zip'}}})
  });
  context.self = context;
  for (const file of ['react.production.min.js','htm.min.js']) vm.runInContext(fs.readFileSync(path.join(root,'static/js',file),'utf8'),context);
  Object.assign(context.React, {
    useState(initial) {const idx=cursor++; if (!(idx in states)) states[idx]=typeof initial==='function'?initial():initial; return [states[idx], value=>{states[idx]=typeof value==='function'?value(states[idx]):value}];},
    useEffect() {}, useRef:()=>({current:null}), useMemo: fn=>fn()
  });
  function render() {cursor=0;tree=component();}
  context.ReactDOM={createRoot:()=>({render:element=>{component=element.type;render();}})};
  vm.runInContext(fs.readFileSync(path.join(root,'static/js/app.js'),'utf8'),context);
  function nodes(value) {if(Array.isArray(value))return value.flatMap(nodes); if(!value||typeof value!=='object')return [];return [value,...nodes(value.props?.children)];}
  function text(value) {if(Array.isArray(value))return value.map(text).join('');if(value&&typeof value==='object')return text(value.props?.children);return value==null||value===false?'':String(value);}
  const button=label=>nodes(tree).find(n=>n.type==='button'&&text(n).trim()===label);
  await button(language==='ar'?'تحديث ◫':'Refresh ◫').props.onClick();render();
  await button(language==='ar'?'👁️ النتائج':'👁️ Results').props.onClick();render();
  const cards=()=>nodes(tree).filter(n=>n.type==='h4');
  assert.equal(cards().length,50,'Mount only one page of a 10,001-record result set');
  assert.equal(text(cards()[0]),'Water record 0');
  const next=language==='ar'?'التالي':'Next';
  button(next).props.onClick();render();
  assert.equal(cards().length,50);
  assert.equal(text(cards()[0]),'Water record 50','Next page contains the next records');
  button(language==='ar'?'السابق':'Previous').props.onClick();render();
  assert.equal(text(cards()[0]),'Water record 0');
  const filter=nodes(tree).find(n=>n.type==='input'&&String(n.props.placeholder).includes(language==='ar'?'بحث وتصفية':'Filter results'));
  filter.props.onChange({target:{value:'Water record 10000'}});render();
  assert.equal(cards().length,1,'Filtering searches every record, including records beyond the visible page');
  assert.equal(text(cards()[0]),'Water record 10000');
  assert.ok(text(tree).includes('Complete abstract describing'),'History restores abstract display mode');
}

(async()=>{await check('en');await check('ar');console.log('Large result pagination renders and navigates in both languages.');})().catch(error=>{console.error(error);process.exitCode=1;});
