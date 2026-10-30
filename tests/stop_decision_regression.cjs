const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

async function check(language, action) {
  const states = [];
  let cursor = 0, component, tree;
  let poll, currentStatus = 'awaiting_stop_decision';
  const actions = [];
  const context = vm.createContext({
    console, FormData, URL, Uint8Array,
    setTimeout: () => 0, clearTimeout() {}, setInterval: callback => {poll=callback;return 1;}, clearInterval() {},
    localStorage: {getItem:key=>key==='knowledge_ocean_lang'?language:null,setItem(){},removeItem(){}},
    document:{getElementById:id=>id==='root'?{}:null},
    window:{location:{protocol:'https:',hostname:'example.hf.space'}},
    fetch:async (url, options) => ({ok:true,json:async()=>{
      if(url==='/api/search')return {task_id:'test'};
      if(String(url).startsWith('/api/guest-quota'))return {remaining:40,remaining_summary:20,quota_limit:50};
      if(url==='/api/cancel/test'){
        const action=options.body.get('action');actions.push(action);
        return {status:'stopping',collected_count:6,quota_charged_units:10};
      }
      assert.equal(url,'/api/status/test');
      return {status:currentStatus,collected_count:7,quota_charged_units:10,progress:30,message:'Collection stopped',papers:[]};
    }})
  });
  context.self = context;
  for (const file of ['react.production.min.js','htm.min.js']) vm.runInContext(fs.readFileSync(path.join(root,'static/js',file),'utf8'),context);
  Object.assign(context.React, {
    useState(initial) {const idx=cursor++; if (!(idx in states)) states[idx]=typeof initial==='function'?initial():initial; return [states[idx], value=>{states[idx]=typeof value==='function'?value(states[idx]):value}];},
    useEffect() {}, useRef:initial=>{const idx=cursor++;return states[idx]||(states[idx]={current:initial});}, useMemo: fn=>fn()
  });
  function render() {cursor=0;tree=component();}
  context.ReactDOM={createRoot:()=>({render:element=>{component=element.type;render();}})};
  vm.runInContext(fs.readFileSync(path.join(root,'static/js/app.js'),'utf8'),context);
  function nodes(value) {if(Array.isArray(value))return value.flatMap(nodes); if(!value||typeof value!=='object')return [];return [value,...nodes(value.props?.children)];}
  function text(value) {if(Array.isArray(value))return value.map(text).join('');if(value&&typeof value==='object')return text(value.props?.children);return value==null||value===false?'':String(value);}
  const button=label=>nodes(tree).find(n=>n.type==='button'&&text(n).trim()===label);
  const input=nodes(tree).find(n=>n.props?.id==='query');
  input.props.onChange({target:{value:'Water analysis'}});render();
  await nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});render();
  await nodes(tree).find(n=>n.type==='button'&&n.props.title===(language==='ar'?'إيقاف عملية البحث الجارية فوراً':'Stop ongoing search immediately')).props.onClick();render();
  let dialog=nodes(tree).find(n=>n.props?.role==='dialog'&&n.props['aria-labelledby']==='stop-decision-title');
  assert.ok(dialog,'Show a stop decision dialog');
  const keep=language==='ar'?'عرض النتائج وإنشاء PDF':'View results and generate PDFs';
  const discard=language==='ar'?'إلغاء البحث نهائيًا':'Discard search';
  assert.equal(button(keep).props.disabled,true,'Wait for the backend to freeze the exact count');
  await poll();render();
  dialog=nodes(tree).find(n=>n.props?.role==='dialog'&&n.props['aria-labelledby']==='stop-decision-title');
  assert.ok(text(dialog).includes('7'),'Display the acknowledged final count');
  assert.ok(text(dialog).includes('10'),'Disclose the retained quota');
  assert.equal(button(keep).props.disabled,false);
  await button(action==='preserve'?keep:discard).props.onClick();render();
  assert.deepEqual(actions,['pause',action]);
  assert.ok(!nodes(tree).find(n=>n.props?.role==='dialog'&&n.props['aria-labelledby']==='stop-decision-title'));
  if(action==='discard'){currentStatus='cancelled';await poll();render();assert.ok(text(tree).includes(language==='ar'?'الرصيد المستخدم مخصومًا':'charged quota is retained'));}

}

(async()=>{for(const lang of ['en','ar'])for(const action of ['preserve','discard'])await check(lang,action);console.log('Stop decisions show exact counts and retained quota in both languages.');})().catch(error=>{console.error(error);process.exitCode=1;});
