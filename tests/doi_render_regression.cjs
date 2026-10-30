// Exercise the shipped HTM templates and event handlers without network or a DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

async function check(language, success) {
  const states = [];
  let cursor = 0, component, tree, calls = 0, copied = null;
  const context = vm.createContext({
    console, FormData, URL, Uint8Array,
    navigator: { clipboard: { writeText: async value => { copied = value; } } },
    setTimeout: () => 0, clearTimeout() {},
    localStorage: { getItem: key => key === 'knowledge_ocean_lang' ? language : null, setItem() {}, removeItem() {} },
    document: { getElementById: id => id === 'root' ? {} : null },
    window: { location: { protocol: 'https:', hostname: 'example.hf.space' } },
    fetch: async (url, options) => {
      calls++;
      assert.equal(url, '/api/doi-lookup');
      assert.equal(options.body.get('doi'), '10.1000/example');
      return { ok: success, json: async () => success ? {
        ok: true, paper: {
          doi: '10.1000/example', doi_url: 'https://doi.org/10.1000/example',
          title: 'Climate and biodiversity', authors: ['Test Author'],
          year: '2025', journal: 'Test Journal', sources: ['crossref'],
          apa: 'Author (2025). Climate and biodiversity.',
          apa_html: '<p>Author (2025). <i>Test Journal</i>.</p>',
          bibtex: '@article{example, title={Climate and biodiversity}}'
        }
      } : { ok: false, error: 'Identifier was not found' } };
    }
  });
  context.self = context;
  for (const file of ['react.production.min.js', 'htm.min.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, 'static/js', file), 'utf8'), context);
  }
  const createElement = context.React.createElement;
  Object.assign(context.React, {
    createElement(type, props, ...children) {
      // React DOM's style contract: a string here unmounts the entire app (#62).
      if (props && props.style != null) assert.equal(typeof props.style, 'object', 'React style props must be objects');
      return createElement(type, props, ...children);
    },
    useState(initial) {
      const index = cursor++;
      if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial;
      return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }];
    },
    useEffect() {}, useRef: () => ({ current: null }), useMemo: fn => fn()
  });
  function render() { cursor = 0; tree = component(); }
  context.ReactDOM = { createRoot: () => ({ render: element => { component = element.type; render(); } }) };
  vm.runInContext(fs.readFileSync(process.env.KO_TEST_APP_SOURCE || path.join(root, 'static/js/app.js'), 'utf8'), context);
  function nodes(value) {
    if (Array.isArray(value)) return value.flatMap(child => nodes(child));
    if (!value || typeof value !== 'object') return [];
    return [value, ...nodes(value.props?.children)];
  }
  function text(value) {
    if (Array.isArray(value)) return value.map(text).join('');
    if (value && typeof value === 'object') return text(value.props?.children);
    return value == null || value === false ? '' : String(value);
  }
  const hub = nodes(tree).find(n => n.type === 'button' && text(n).includes(language === 'ar' ? 'منظومة توثيق' : 'DOI & Citation Resolver'));
  assert.ok(hub, 'DOI navigation is present');
  hub.props.onClick(); render();
  const input = nodes(tree).find(n => n.props?.id === 'doi_input_field');
  assert.ok(input, 'DOI input is present');
  input.props.onChange({ target: { value: '10.1000/example' } }); render();
  const lookup = nodes(tree).find(n => n.type === 'button' && text(n).includes(language === 'ar' ? 'فحص واسترجاع المعرف' : 'Lookup & Verify'));
  await lookup.props.onClick(); render();
  assert.equal(calls, 1);
  assert.ok(nodes(tree).some(n => n.props?.id === 'doi_input_field'), 'The app stays mounted');
  assert.ok(text(tree).includes(success ? 'Climate and biodiversity' : 'Identifier was not found'));
  if (success) {
    const citation = nodes(tree).find(n => n.props?.dangerouslySetInnerHTML?.__html?.includes('Test Journal'));
    assert.ok(citation, 'Formatted citation renders');
    assert.equal(citation.props.style.fontSize, '14pt');
    assert.ok(citation.props.className.includes('citation-text'));
    assert.ok(!citation.props.className.includes('select-all'));
    const copySelection = nodes(tree).find(n => n.type === 'button' && text(n) === (language === 'ar' ? 'نسخ الجزء المحدد' : 'Copy selection'));
    assert.ok(copySelection, 'Partial-copy control is available');
    let prevented = false;
    copySelection.props.onMouseDown({ preventDefault() { prevented = true; } });
    assert.ok(prevented, 'Clicking copy preserves the selection');
    const anchor = {}, focus = {};
    context.window.getSelection = () => ({ anchorNode: anchor, focusNode: focus, toString: () => '2025' });
    const container = { contains: node => node === anchor || node === focus };
    const event = { currentTarget: { closest: () => ({ querySelector: () => container }) } };
    copySelection.props.onClick(event);
    await Promise.resolve();
    assert.equal(copied, '2025', 'Copy only the selected substring');
    copied = null;
    context.window.getSelection = () => ({ anchorNode: {}, focusNode: focus, toString: () => 'outside text' });
    copySelection.props.onClick(event);
    assert.equal(copied, null, 'Do not copy text selected outside the citation');
    context.window.getSelection = () => null;
    copySelection.props.onClick(event);
    assert.equal(copied, null, 'Empty selections do not copy the full citation');
  }
}

(async () => {
  for (const language of ['en', 'ar']) {
    await check(language, true);
    await check(language, false);
  }
  console.log('DOI success and failure views render in Arabic and English.');
})().catch(error => { console.error(error); process.exitCode = 1; });
