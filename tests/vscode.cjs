'use strict';
const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { pathToFileURL, fileURLToPath } = require('node:url');
const commands = {}, providers = {}, events = {}, messages = [], tasks = [];
let diagnostics;
class Position { constructor(line, character) { this.line = line; this.character = character; } }
class Range {
  constructor(...args) {
    this.start = args.length === 2 ? args[0] : new Position(args[0], args[1]);
    this.end = args.length === 2 ? args[1] : new Position(args[2], args[3]);
  }
}
function uri(file) { return { fsPath: file, scheme: 'file', toString() { return pathToFileURL(file).href; } }; }
const disposable = () => ({ dispose() {} });
const mock = {
  Range, Position,
  Uri: { file: uri, parse: text => uri(fileURLToPath(text)) },
  Diagnostic: class { constructor(range, message) { this.range = range; this.message = message; } },
  DiagnosticSeverity: { Error: 0 },
  CompletionItem: class { constructor(label) { this.label = label; } },
  CompletionItemKind: {}, SymbolKind: { Function: 1 },
  DocumentSymbol: class { constructor(name) { this.name = name; } }, Hover: class {},
  TaskScope: { Global: 1 }, TaskRevealKind: { Always: 1 }, TaskPanelKind: { Dedicated: 1 },
  ProcessExecution: class { constructor(command, args) { this.command = command; this.args = args; } },
  Task: class { constructor(definition, scope, name, source, execution) { this.execution = execution; } },
  commands: { registerCommand(name, handler) { commands[name] = handler; return disposable(); } },
  tasks: { executeTask(task) { tasks.push(task); } },
  window: { showErrorMessage(message) { messages.push(message); } },
  workspace: {
    isTrusted: true,
    getConfiguration() { return { get(key, fallback) {
      if (key === 'checkerPath') return path.resolve(__dirname, '../../.build/editors/bin/lipcheck');
      return fallback;
    } }; },
    getWorkspaceFolder() {},
    onDidSaveTextDocument(handler) { events.save = handler; return disposable(); },
    onDidChangeTextDocument(handler) { events.change = handler; return disposable(); },
    onDidCloseTextDocument(handler) { events.close = handler; return disposable(); },
    async openTextDocument(value) { return document(value.fsPath); },
  },
  languages: {
    createDiagnosticCollection() {
      diagnostics = new Map();
      return { clear() { diagnostics.clear(); }, set(key, value) { diagnostics.set(key.toString(), value); }, dispose() {} };
    },
    registerCompletionItemProvider(language, provider) { providers.completion = provider; return disposable(); },
    registerHoverProvider(language, provider) { providers.hover = provider; return disposable(); },
    registerDocumentSymbolProvider(language, provider) { providers.symbol = provider; return disposable(); },
  },
};
const load = Module._load;
Module._load = function(name, ...args) { return name === 'vscode' ? mock : load.call(this, name, ...args); };
const extension = require('../vscode/extension');
Module._load = load;
function document(file) {
  const text = fs.readFileSync(file, 'utf8'), lines = text.split('\n');
  return {
    uri: uri(file), fileName: file, languageId: 'lip', version: 1, isClosed: false,
    lineCount: lines.length, lineAt(row) { return { text: lines[row] }; },
    getText() { return text; }, async save() { return true; },
    positionAt(offset) {
      const prefix = text.slice(0, offset).split('\n');
      return new Position(prefix.length - 1, prefix.at(-1).length);
    },
  };
}
async function until(predicate) {
  const end = Date.now() + 10000;
  while (!predicate()) {
    if (Date.now() > end) throw new Error('Timed out waiting for checker');
    await new Promise(resolve => setTimeout(resolve, 20));
  }
}
(async () => {
  const context = { subscriptions: [] };
  extension.activate(context);
  assert(providers.completion.provideCompletionItems().some(item => item.label === 'parse_number'));
  const sample = '# fn comment() -> any {}\ntext = """\nflow fake() -> void {}\n"""\nflow Main() -> void {}';
  const mask = extension.codeMask(sample);
  assert.equal(mask.length, sample.length);
  assert(!mask.includes('fake'));
  assert(!mask.includes('comment'));
  assert(mask.includes('Main'));
  assert(!extension.codeMask('x = """\nflow fake()').includes('fake'));
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'LIP 空格 '));
  try {
    const file = path.join(directory, 'program file.lip');
    fs.writeFileSync(file, 'flow Main() -> number { text = "𐀀é"; return missing }\n');
    const source = document(file);
    mock.window.activeTextEditor = { document: source };
    await commands['lip.check']();
    await until(() => diagnostics.size > 0 || messages.length > 0);
    assert.deepEqual(messages, []);
    assert.match(diagnostics.get(source.uri.toString())[0].message, /^E-NAME:/);
    assert.equal(diagnostics.get(source.uri.toString())[0].range.start.character, source.getText().indexOf('missing'));
    assert.deepEqual(providers.symbol.provideDocumentSymbols(source).map(symbol => symbol.name), ['Main']);
    events.change({ document: source });
    assert.equal(diagnostics.size, 0);
    await commands['lip.run']();
    assert.deepEqual(tasks[0].execution.args, ['run', file]);
    mock.workspace.isTrusted = false;
    await commands['lip.run']();
    assert.equal(tasks.length, 1);
    assert.match(messages.at(-1), /Trust this workspace/);
  } finally {
    for (const subscription of context.subscriptions) subscription.dispose();
    fs.rmSync(directory, { recursive: true, force: true });
  }
  process.stdout.write('VS Code commands, real diagnostics, symbols, and literal process arguments passed.\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
