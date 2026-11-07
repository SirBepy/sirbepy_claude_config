// Run with: node template.test.cjs
// Runs the deck's slide-key handler from template.html against stub state, no browser.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8').replace(/\r\n/g, '\n');
const m = html.match(/document\.addEventListener\('keydown',e=>\{([\s\S]*?)\n\}\);\n\[\.\.\.nav\.children\]/);
assert.ok(m, 'slide keydown handler not found in template.html');
const handler = new Function('e', 'state', `const {sections,show}=state;let current=state.current;${m[1]}`);

function press(key, tag) {
  const shown = [];
  const state = { current: 1, sections: [{ querySelector: () => null }, { querySelector: () => null }, { querySelector: () => null }], show: (i) => shown.push(i) };
  handler({ key, target: { tagName: tag }, preventDefault() {} }, state);
  return shown;
}

assert.deepStrictEqual(press('ArrowRight', 'BODY'), [2], 'arrow right changes the slide');
assert.deepStrictEqual(press('ArrowLeft', 'BODY'), [0], 'arrow left changes the slide');
assert.deepStrictEqual(press('ArrowRight', 'INPUT'), [], 'a focused seek slider keeps the arrow for itself');
assert.deepStrictEqual(press('ArrowLeft', 'INPUT'), [], 'a focused seek slider keeps the arrow for itself');
assert.deepStrictEqual(press('ArrowRight', 'BUTTON'), [2], 'a focused button still lets the arrow change the slide');

console.log('template tests passed');
