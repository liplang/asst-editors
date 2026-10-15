'use strict';
const vscode = require('vscode');
const path = require('path');
const { spawn } = require('child_process');
const data = require('./language-data.json');

// Mask strings/comments while preserving offsets and line breaks for symbols.
function codeMask(text) {
  return text.replace(/"""(?:\\[\s\S]|"(?!"")|[^"\\])*(?:"""|$)|"(?:\\[^\r\n]|[^"\\\r\n])*"?|#[^\r\n]*/g,
    part => part.replace(/[^\r\n]/g, ' '));
}

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection('lip');
  const pending = new Map();
  const results = new Map();
  context.subscriptions.push(diagnostics, { dispose() { for (const child of pending.values()) child.kill(); } });

  function config(document) {
    const cfg = vscode.workspace.getConfiguration('lip', document.uri);
    const folder = vscode.workspace.getWorkspaceFolder(document.uri);
    const expand = value => value.replace(/\$\{workspaceFolder\}/g, () => folder ? folder.uri.fsPath : path.dirname(document.fileName))
      .replace(/\$\{fileDirname\}/g, () => path.dirname(document.fileName));
    const projectValue = expand(cfg.get('projectRoot', ''));
    const project = projectValue ? path.resolve(folder ? folder.uri.fsPath : path.dirname(document.fileName), projectValue) : '';
    return {
      compiler: expand(cfg.get('compilerPath', 'lipc')), checker: expand(cfg.get('checkerPath', 'lipcheck')),
      args: cfg.get('arguments', []).map(expand).concat(project ? ['-project', project] : []),
      runArgs: cfg.get('runArguments', []), cwd: project || path.dirname(document.fileName),
    };
  }
  async function savedDocument() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'lip' || editor.document.uri.scheme !== 'file') {
      vscode.window.showErrorMessage('Open a saved .lip file first.');
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before running LIP tools.');
      return;
    }
    if (await editor.document.save()) return editor.document;
  }
  function publish() {
    diagnostics.clear();
    const combined = new Map();
    for (const entries of results.values()) for (const [uri, items] of entries) {
      combined.set(uri, (combined.get(uri) || []).concat(items));
    }
    for (const [uri, items] of combined) diagnostics.set(vscode.Uri.parse(uri), items);
  }
  async function check(document) {
    if (!vscode.workspace.isTrusted || document.uri.scheme !== 'file') return;
    const key = document.uri.toString();
    if (pending.has(key)) pending.get(key).kill();
    const cfg = config(document), version = document.version;
    const child = spawn(cfg.checker, cfg.args.concat(document.fileName), { cwd: cfg.cwd, shell: false });
    pending.set(key, child);
    let output = '', reported = false;
    const append = chunk => { if (output.length < 1024 * 1024) output += chunk.toString(); };
    child.stdout.on('data', append);
    child.stderr.on('data', append);
    child.on('error', error => {
      reported = true;
      if (pending.get(key) === child) vscode.window.showErrorMessage(`LIP checker: ${error.message}. Set lip.checkerPath to lipcheck.`);
    });
    child.on('close', async code => {
      if (pending.get(key) !== child) return;
      pending.delete(key);
      if (document.version !== version || document.isClosed) return;
      const entries = new Map();
      for (const line of output.split(/\r?\n/)) {
        const match = /^(.*):(\d+):(\d+): (.*)$/.exec(line);
        if (!match) continue;
        const uri = vscode.Uri.file(match[1]);
        const row = Math.max(0, Number(match[2]) - 1);
        let column = Math.max(0, Number(match[3]) - 1);
        try {
          const source = await vscode.workspace.openTextDocument(uri);
          if (row < source.lineCount) column = Array.from(source.lineAt(row).text).slice(0, column).join('').length;
        } catch (_) { /* A removed dependency can still have a file diagnostic. */ }
        const range = new vscode.Range(row, column, row, column + 1);
        const item = new vscode.Diagnostic(range, match[4], vscode.DiagnosticSeverity.Error);
        item.source = 'lipcheck';
        const diagnosticCode = /^(E-[A-Z-]+):/.exec(match[4]);
        if (diagnosticCode) item.code = diagnosticCode[1];
        const uriKey = uri.toString();
        entries.set(uriKey, (entries.get(uriKey) || []).concat(item));
      }
      if (document.version !== version || document.isClosed) return;
      results.set(key, entries);
      publish();
      if (code && !entries.size && !reported) vscode.window.showErrorMessage(`LIP check failed: ${output.trim() || `exit ${code}`}`);
    });
  }
  async function execute(action) {
    const document = await savedDocument();
    if (!document) return;
    if (action === 'check') return check(document);
    const cfg = config(document);
    const args = [action].concat(cfg.args);
    if (action === 'run') args.push(...cfg.runArgs);
    if (action === 'build') {
      const output = await vscode.window.showSaveDialog({
        title: 'Build LIP executable', defaultUri: vscode.Uri.file(document.fileName + '.out'),
      });
      if (!output) return;
      if (output.fsPath === document.fileName || /\.lip$/i.test(output.fsPath)) {
        vscode.window.showErrorMessage('Choose an executable destination that does not overwrite LIP source.');
        return;
      }
      args.push('-o', output.fsPath);
    }
    args.push(document.fileName);
    const task = new vscode.Task({ type: 'lip', action }, vscode.workspace.getWorkspaceFolder(document.uri) || vscode.TaskScope.Global,
      `LIP ${action}`, 'LIP', new vscode.ProcessExecution(cfg.compiler, args, { cwd: cfg.cwd }));
    task.presentationOptions = { reveal: vscode.TaskRevealKind.Always, panel: vscode.TaskPanelKind.Dedicated };
    return vscode.tasks.executeTask(task);
  }
  for (const action of ['check', 'run', 'build']) context.subscriptions.push(vscode.commands.registerCommand(`lip.${action}`, () => execute(action)));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(document => {
    if (document.languageId === 'lip' && vscode.workspace.getConfiguration('lip', document.uri).get('checkOnSave', false)) check(document);
  }));
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(event => {
    const key = event.document.uri.toString();
    if (pending.has(key)) { pending.get(key).kill(); pending.delete(key); }
    if (results.delete(key)) publish();
  }));
  context.subscriptions.push(vscode.workspace.onDidCloseTextDocument(document => {
    const key = document.uri.toString();
    if (pending.has(key)) { pending.get(key).kill(); pending.delete(key); }
    results.delete(key);
    publish();
  }));
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider('lip', {
    provideCompletionItems() {
      return data.keywords.map(word => new vscode.CompletionItem(word, vscode.CompletionItemKind.Keyword))
        .concat(data.types.map(word => new vscode.CompletionItem(word, vscode.CompletionItemKind.TypeParameter)))
        .concat(['true', 'false', 'null', 'claim'].map(word => new vscode.CompletionItem(word, vscode.CompletionItemKind.Constant)))
        .concat(Object.entries(data.builtins).map(([word, description]) => {
          const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.Function);
          item.documentation = description;
          return item;
        }));
    },
  }));
  context.subscriptions.push(vscode.languages.registerHoverProvider('lip', {
    provideHover(document, position) {
      const range = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_]*/);
      const text = range && data.builtins[document.getText(range)];
      if (text) return new vscode.Hover(text, range);
    },
  }));
  context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider('lip', {
    provideDocumentSymbols(document) {
      const code = codeMask(document.getText()), symbols = [];
      const pattern = /\b(fn|flow)\s+([A-Za-z_][A-Za-z0-9_]*)/g;
      let match;
      while ((match = pattern.exec(code))) {
        const start = document.positionAt(match.index);
        const end = document.positionAt(match.index + match[0].length);
        const range = new vscode.Range(start, end);
        symbols.push(new vscode.DocumentSymbol(match[2], match[1], vscode.SymbolKind.Function, range, range));
      }
      return symbols;
    },
  }));
}
module.exports = { activate, codeMask };
