#!/usr/bin/env python3
"""Exercise real editor runtimes and the compile-only bridge. No GUI required."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

EDITORS = Path(__file__).resolve().parents[1]
REPO = EDITORS.parent / "lipv1"
BUILD = Path(os.environ.get("LIP_EDITOR_BUILD", EDITORS / ".build")).resolve()
BIN = BUILD / "bin"
LANGUAGE = json.loads((EDITORS / "language.json").read_text())


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], text=True, capture_output=True, timeout=90, **kwargs)


def snippet(name, values=None):
    """Fill tab stops as a user would, retaining repeated placeholder values."""
    body = LANGUAGE["snippets"][name]["body"]
    text = "\n".join(body) if isinstance(body, list) else body
    values = dict(values or {})

    def replace(match):
        index = int(match[1] or match[3])
        return values.setdefault(index, match[2] or "")

    return re.sub(r"\$\{(\d+)(?::([^}]*))?\}|\$(\d+)", replace, text)


class EditorSupport(unittest.TestCase):
    def test_core_function_names_follow_spec(self):
        spec = (REPO / "spec/LIP-1.0-SPEC.md").read_text()
        table = spec.split("### 3.1.", 1)[1].split("核心函数不接受", 1)[0]
        names = re.findall(r"^\| ([a-z_]+)\(", table, re.MULTILINE)
        self.assertEqual(set(LANGUAGE["builtins"]), set(names))
        self.assertTrue(set(LANGUAGE["nativeHelpers"]).isdisjoint(names))

    def test_compile_only_and_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix="LIP editor 空格 ") as directory:
            root = Path(directory)
            source = root / "main file.lip"
            source.write_text('flow Main() -> number { return fail("must not execute") }\n')
            checked = run([BIN / "lipcheck", source])
            self.assertEqual((checked.returncode, checked.stdout, checked.stderr), (0, "", ""))
            source.write_text('flow Main() -> number { return missing }\n')
            checked = run([BIN / "lipcheck", source])
            self.assertEqual(checked.returncode, 1)
            self.assertRegex(checked.stderr, re.escape(str(source)) + r":1:\d+: E-NAME:")
            source.write_text('flow One() -> number { return 1 }\nflow Two() -> number { return 2 }\n')
            self.assertIn("E-ENTRY:", run([BIN / "lipcheck", source]).stderr)
            self.assertEqual(run([BIN / "lipcheck", "-entry", "Two", source]).returncode, 0)
            dependency = root / "lib.lip"
            dependency.write_text('export fn invalid() -> number { missing }\n')
            source.write_text('import lip "lib.lip" as lib\nflow Main() -> number { return lib.invalid() }\n')
            checked = run([BIN / "lipcheck", source])
            self.assertRegex(checked.stderr, re.escape(str(dependency)) + r":1:\d+: E-NAME:")
            dependency.write_text('export fn valid() -> number { 7 }\n')
            child = root / "sub"
            child.mkdir()
            module = child / "program.lip"
            module.write_text('import lip "../lib.lip" as lib\nflow Main() -> number { return lib.valid() }\n')
            self.assertEqual(run([BIN / "lipcheck", "-project", root, module]).returncode, 0)
            self.assertEqual(run([BIN / "lipcheck"]).returncode, 2)

    def test_default_main_and_explicit_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "entry.lip"
            source.write_text('flow Helper() -> number { return 7 }\n'
                              'flow Main() -> number { return 42 }\n')
            self.assertEqual(run([BIN / "lipcheck", source]).returncode, 0)
            for arguments, expected in [([], 42), (["-entry", "Helper"], 7)]:
                executed = run([BIN / "lipc", "run", *arguments, source])
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(json.loads(executed.stdout), expected)
            self.assertIn("E-ENTRY:", run([BIN / "lipcheck", "-entry", "Unknown", source]).stderr)
            source.write_text('flow Helper() -> number { return missing }\n'
                              'flow Main() -> number { return 42 }\n')
            self.assertIn("E-NAME:", run([BIN / "lipcheck", source]).stderr)

    def test_index_slice_snippets_and_native_helper_shadowing(self):
        expressions = {"slice": snippet("Slice"), "reverse": snippet("Reverse"),
                       "indices": snippet("Index list"),
                       "step": "slice(items, null, null, -2)",
                       "clipped": "items[-100:100]", "last": "items[-1]",
                       "unicode": '"A𐀀é"[::-1]',
                       "shadowed": "native_release(native_data(2))"}
        fields = ",\n".join(f"{name}: {expr}" for name, expr in expressions.items())
        with tempfile.TemporaryDirectory(prefix="LIP selection 空格 ") as directory:
            source = Path(directory) / "selections.lip"
            source.write_text('fn native_data(x:number)->number { x+1 }\n'
                              'fn native_release(x:number)->number { x+10 }\n'
                              f'flow Main()->object {{ items=range(5); return {{{fields}}} }}\n')
            checked = run([BIN / "lipcheck", source])
            self.assertEqual(checked.returncode, 0, checked.stderr)
            executed = run([BIN / "lipc", "run", source])
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(json.loads(executed.stdout), {
                "slice": [0, 1, 2, 3, 4], "reverse": [4, 3, 2, 1, 0],
                "indices": [0, 4], "step": [4, 2, 0], "clipped": [0, 1, 2, 3, 4],
                "last": 4, "unicode": "́e𐀀A", "shadowed": 13,
            })
            executable = Path(directory) / "compiled selections"
            built = run([BIN / "lipc", "build", "-o", executable, source], cwd=EDITORS)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            compiled = run([executable])
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(json.loads(compiled.stdout), json.loads(executed.stdout))

    def test_operation_and_snapshot_snippets(self):
        perform = snippet("Perform", {2: "console", 3: "write", 0: '"editor snippet"'})
        snapshot = snippet("Claim snapshot")
        proposal = snippet("Proposal", {2: "console", 3: "write", 0: '"proposal snippet"'})
        saved = snippet("Perform proposal", {1: "second"})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "operations.lip"
            source.write_text(snippet("Host import", {1: "console", 0: "console"}) + '\nflow Main()->object {\n'
                              f'facts=claim()\nfacts <+ 7\n{perform}\n{proposal}\n{saved}\n{snapshot}\n'
                              'complete=facts\nreturn {count:len(complete),seen:len(seen)}\n}\n')
            checked = run([BIN / "lipcheck", "-host", "demo", source])
            self.assertEqual(checked.returncode, 0, checked.stderr)
            executed = run([BIN / "lipc", "run", "-host", "demo", source])
            self.assertEqual(executed.returncode, 0, executed.stderr)
            result = json.loads(executed.stdout)
            self.assertEqual(result["count"], 1)
            self.assertIn(result["seen"], [0, 1])
            self.assertIn("editor snippet", executed.stderr)
            self.assertIn("proposal snippet", executed.stderr)

    @unittest.skipUnless(shutil.which("emacs"), "Emacs is not installed")
    def test_emacs_strings_indentation_completion_and_errors(self):
        script = r'''
(progn
  (require 'lip-mode)
  (with-temp-buffer
    (insert "flow Main() -> string {\ntext = \"\"\"\n# body { fn fake() -> number { 1 }\n  unchanged\n\"\"\"\nreturn text\n}\n")
    (lip-mode)
    (font-lock-ensure)
    (goto-char (point-min)) (forward-line 2)
    (unless (and (nth 3 (syntax-ppss)) (not (nth 4 (syntax-ppss)))) (error "triple body not string"))
    (indent-region (point-min) (point-max))
    (unless (equal (buffer-string) "flow Main() -> string {\n  text = \"\"\"\n# body { fn fake() -> number { 1 }\n  unchanged\n\"\"\"\n  return text\n}\n")
      (error "bad indentation: %S" (buffer-string)))
    (goto-char (point-min)) (forward-line 5)
    (when (or (nth 3 (syntax-ppss)) (nth 4 (syntax-ppss))) (error "string leaked"))
    (unless (equal (mapcar #'car (cdr (assoc "Flows" (lip--imenu-index)))) '("Main")) (error "imenu includes string contents"))
    (when (assoc "Functions" (lip--imenu-index)) (error "fake function in imenu"))
    (goto-char (point-max)) (insert "par")
    (unless (member "parse_number" (nth 2 (lip-completion-at-point))) (error "missing completion")))
  (with-temp-buffer
    (insert "flow Main() -> list {\n  xs = range(5)\n  ys = native_data(xs)\n  return ys[::-1]\n}\n")
    (lip-mode) (font-lock-ensure)
    (goto-char (point-min)) (search-forward "native_data") (backward-char)
    (unless (eq (get-text-property (point) 'face) 'font-lock-builtin-face) (error "missing native helper highlighting"))
    (goto-char (point-max)) (insert "native_")
    (unless (member "native_release" (nth 2 (lip-completion-at-point))) (error "missing native helper completion"))
    (erase-buffer)
    (let ((skeleton-end-newline nil))
      (lip--reverse-template "items"))
    (unless (equal (string-trim (buffer-string)) "items[::-1]") (error "bad reverse template")))
  (with-temp-buffer
    (insert "# \"\"\"\nx = \"hash # and \\\" quote\"\ny = 8 // 2\n")
    (lip-mode) (font-lock-ensure)
    (goto-char (point-max))
    (when (nth 3 (syntax-ppss)) (error "comment opened string")))
  (princ "Emacs passed\n"))
'''
        checked = run(["emacs", "--batch", "-Q", "-L", EDITORS / "emacs", "--eval", script])
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def vim_runtime(self, editor):
        with tempfile.TemporaryDirectory(prefix="lip-editor-test-") as directory:
            root = Path(directory)
            source = root / "file with spaces.lip"
            source.write_text('flow Main() -> string {\ntext = """\n# body {\n  keep\n"""\nreturn text\n}\n')
            result = root / "result.json"
            script = root / "test.vim"
            script.write_text(f'''
set nomore
execute 'set runtimepath^=' . fnameescape({json.dumps(str(EDITORS / 'vim'))})
filetype plugin indent on
syntax on
execute 'edit ' . fnameescape({json.dumps(str(source))})
call assert_equal('lip', &filetype)
call assert_equal('lip#Complete', &omnifunc)
call assert_equal('lipMultilineString', synIDattr(synID(3, 1, 1), 'name'))
normal! gg=G
call assert_equal(['flow Main() -> string {{', '  text = """', '# body {{', '  keep', '"""', '  return text', '}}'], getline(1, '$'))
call assert_true(index(lip#Complete(0, 'par'), 'parse_number') >= 0)
call assert_true(index(lip#Complete(0, 'native_'), 'native_data') >= 0)
call setline(1, ['x = 8 // 2', '# comment', 'x = "# text"'])
syntax sync fromstart
call assert_equal('lipOperator', synIDattr(synID(1, 7, 1), 'name'))
call assert_equal('lipComment', synIDattr(synID(2, 1, 1), 'name'))
enew!
setfiletype lip
LipTemplate claimfor
call assert_equal('results = claim()', getline(1))
enew!
setfiletype lip
LipTemplate reverse
call assert_equal('items[::-1]', getline(1))
enew!
setfiletype lip
LipTemplate snapshot
call assert_equal('seen = perform effect claim.snapshot("facts")', getline(1))
call setline(1, 'snapshot = native_data(items[0:null:2])')
syntax sync fromstart
call assert_equal('lipNativeHelper', synIDattr(synID(1, 12, 1), 'name'))
execute 'edit! ' . fnameescape({json.dumps(str(source))})
call setline(1, ['flow Main() -> number {{', '  text = "𐀀é"; return missing', '}}'])
if line('$') > 3 | 4,$delete _ | endif
let g:lip_check = {json.dumps(str(BIN / 'lipcheck'))}
let expected_column = match(getline(2), 'missing') + 1
LipCheck
call assert_equal(1, len(getqflist()))
call assert_equal(2, getqflist()[0].lnum)
call assert_equal(expected_column, getqflist()[0].col)
call assert_match('E-NAME:', getqflist()[0].text)
cclose
call setline(1, ['flow Main(name: string) -> string {{ return name }}'])
2,$delete _
let b:lip_run_args = ['-input', '{{"name":"Ada $(literal)"}}']
let g:lip_compiler = {json.dumps(str(BIN / 'lipc'))}
LipRun
if has('nvim')
  call assert_equal(0, jobwait([b:terminal_job_id], 10000)[0])
  let terminal_output = join(getline(1, '$'), "\\n")
else
  call term_wait(bufnr('%'), 1000)
  call assert_equal('dead', job_status(term_getjob(bufnr('%'))))
  let terminal_buffer = bufnr('%')
  let terminal_output = join(map(range(1, term_getsize(terminal_buffer)[0]), 'term_getline(terminal_buffer, v:val)'), "\\n")
endif
call assert_match('Ada $(literal)', terminal_output)
call writefile([json_encode(v:errors)], {json.dumps(str(result))})
qa!
''')
            command = [editor, "-u", "NONE", "-i", "NONE", "-n", "-es", "-V1" + str(root / "editor.log"), "-S", script]
            checked = run(command, cwd=REPO, env={**os.environ, "NVIM_LOG_FILE": str(root / "nvim.log")})
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr + (root / "editor.log").read_text())
            self.assertEqual(json.loads(result.read_text()), [])

    @unittest.skipUnless(shutil.which("vim"), "Vim is not installed")
    def test_vim9(self):
        self.vim_runtime("vim")

    @unittest.skipUnless(shutil.which("nvim"), "Neovim is not installed")
    def test_neovim(self):
        self.vim_runtime("nvim")
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "test.lua"
            script.write_text(f'''
vim.opt.runtimepath:prepend({json.dumps(str(EDITORS / 'neovim'))})
require('lip').setup({{ compiler = 'lipc', keymaps = true }})
vim.cmd('filetype plugin indent on')
vim.cmd('edit /tmp/lip-setup-check.lip')
assert(vim.bo.filetype == 'lip')
assert(vim.bo.omnifunc == 'lip#Complete')
assert(vim.fn.exists(':LipCheck') == 2)
vim.cmd('qa!')
''')
            checked = run(["nvim", "--headless", "-u", "NONE", "-l", script],
                          env={**os.environ, "NVIM_LOG_FILE": str(Path(directory) / "nvim.log")})
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_vscode(self):
        checked = run(["node", EDITORS / "tests/vscode.cjs"])
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_real_vscode_textmate(self):
        app = os.environ.get("LIP_TEST_VSCODE_APP")
        candidates = [Path(app)] if app else [
            Path("/usr/share/code/resources/app"),
            Path("/opt/visual-studio-code/resources/app"),
            Path("/var/lib/snapd/snap/code/current/usr/share/code/resources/app"),
        ]
        for app in candidates:
            executable = app.parent.parent / "code"
            if executable.is_file() and (app / "node_modules.asar").is_file():
                checked = run([executable, EDITORS / "tests/textmate.cjs", app],
                              env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"})
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                return
        self.skipTest("Packaged VS Code TextMate runtime is not installed")

    def test_generated_assets_and_vsix(self):
        files = [*EDITORS.glob("vscode/**/*.json"), *EDITORS.glob("zed/snippets/*.json"),
                 *EDITORS.glob("sublime/*.sublime-*")]
        before = {file: file.read_bytes() for file in files}
        checked = run(["python3", EDITORS / "tools/generate.py"])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(before, {file: file.read_bytes() for file in files}, "generated assets are stale")
        for file in files:
            text = file.read_text()
            if text.startswith("%YAML"):
                text = text.split("---\n", 1)[1]
                text = re.sub(r'(?m)^(\s*)([0-9]+)(:)', r'\1"\2"\3', text)
            json.loads(text)
        checked = run(["python3", EDITORS / "tools/package.py", "vscode"])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        with zipfile.ZipFile(BUILD / "lip-language.vsix") as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("extension/syntaxes/lip.tmLanguage.json", archive.namelist())
            self.assertIn("extension/extension.js", archive.namelist())

    @unittest.skipUnless(shutil.which("tree-sitter"), "Tree-sitter CLI is not installed: Zed parser generation not verified")
    def test_tree_sitter(self):
        checked = run(["python3", EDITORS / "tools/package.py", "zed"])
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        grammar = BUILD / "tree-sitter-lip"
        examples = list((REPO / "examples").rglob("*.lip"))
        checked = run(["tree-sitter", "parse", *examples], cwd=grammar)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        for query in (EDITORS / "zed/languages/lip").glob("*.scm"):
            checked = run(["tree-sitter", "query", query, REPO / "examples/advanced/26_flows.lip"], cwd=grammar)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
