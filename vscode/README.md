# LIP 1.0

Support for `.lip`: syntax highlighting, snippets, core function completion and hover, Flow/function symbols, saved-file diagnostics, and run/build commands.

Build the tools with `make tools` from the editors directory alongside `../lipv1`. Set `lip.compilerPath` and `lip.checkerPath` to the generated `.build/bin/lipc` and `.build/bin/lipcheck` executables, or put them on PATH. Use **LIP: Check File**, **LIP: Run File**, and **LIP: Build Executable** from the command palette. Checking saves the file and compiles it without running its Flow; native import discovery follows the compiler's normal behavior.

Use `lip.arguments` for common flags such as `["-entry", "Main", "-host", "demo"]`, `lip.runArguments` for run-only flags such as `-input`, and `lip.projectRoot` for the static import boundary. `lip.checkOnSave` is optional and defaults to false. Tool execution requires a trusted workspace.

The default entry is the root `Main` Flow, otherwise the sole root Flow; `-entry` overrides it. Run arguments also accept `-entry-input`, `-entry-output`, `-parallel`, `-steps`, `-elements`, and `-frames`.

Negative indices, index lists, and slices with omitted bounds and a nonzero step are supported. `slice`, `reverse`, and `indices` snippets cover these forms; `slice` hover describes clipping and null defaults. `perform` inserts `perform effect module.operation(...)`; `performproposal` executes an existing proposal. `snapshot` observes a Claim store in the current Flow. The effectful native Host helpers `native_data` and `native_release` have separate completion and hover documentation, plus `nativedata` and `nativerelease` snippets. They can be shadowed and are separate from the 13 core pure functions.

`#` starts a comment; `//` is floor division. Triple-quoted strings preserve indentation. No LSP, formatter, debugger, or semantic rename provider is bundled. See `../README.md` in the editors package for installation, other editors, and detailed examples.
