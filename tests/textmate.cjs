// Optional validation with VS Code's real bundled TextMate/Oniguruma engines.
// Run under Electron with ELECTRON_RUN_AS_NODE=1, passing resources/app as argv[2].
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const app = process.argv[2];
const tm = require(path.join(app, 'node_modules.asar/vscode-textmate'));
const onig = require(path.join(app, 'node_modules.asar/vscode-oniguruma'));
(async () => {
  await onig.loadWASM(fs.readFileSync(path.join(app, 'node_modules.asar/vscode-oniguruma/release/onig.wasm')));
  const raw = tm.parseRawGrammar(fs.readFileSync(path.resolve(__dirname, '../vscode/syntaxes/lip.tmLanguage.json'), 'utf8'), 'lip.tmLanguage.json');
  const registry = new tm.Registry({
    onigLib: Promise.resolve({ createOnigScanner: patterns => new onig.OnigScanner(patterns), createOnigString: text => new onig.OnigString(text) }),
    loadGrammar: async scope => scope === 'source.lip' ? raw : null,
  });
  const grammar = await registry.loadGrammar('source.lip');
  let state = tm.INITIAL;
  function tokens(line) {
    const result = grammar.tokenizeLine(line, state);
    state = result.ruleStack;
    return result.tokens.map(token => ({ text: line.slice(token.startIndex, token.endIndex), scopes: token.scopes }));
  }
  function scoped(items, word, scope) {
    assert(items.some(item => item.text.includes(word) && item.scopes.includes(scope)), `${word} missing ${scope}: ${JSON.stringify(items)}`);
  }
  scoped(tokens('flow Main(value: number?) -> string {'), 'number', 'storage.type.lip');
  tokens('text = """');
  const body = tokens('# text { and // operators');
  scoped(body, '# text', 'string.quoted.triple.lip');
  assert(body.every(item => !item.scopes.some(scope => scope.startsWith('comment'))));
  const escapes = tokens('\\u{1F600} \\n \\q');
  scoped(escapes, '\\u{1F600}', 'constant.character.escape.lip');
  scoped(escapes, '\\q', 'invalid.illegal.escape.lip');
  tokens('"""');
  const operators = tokens('return 8 // 2 + 8 */ 2 ** 3 |> stage');
  for (const op of ['//', '*/', '**', '|>']) scoped(operators, op, 'keyword.operator.lip');
  scoped(tokens('# comment'), 'comment', 'comment.line.number-sign.lip');
  const binding = tokens('number = 4');
  assert(!binding.some(item => item.text === 'number' && item.scopes.includes('storage.type.lip')));
  tokens('}');
  assert.equal(state.depth, 1);
  registry.dispose();
  process.stdout.write('Real TextMate/Oniguruma highlighting passed.\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
