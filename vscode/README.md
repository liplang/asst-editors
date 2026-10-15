# LIP 1.0

Support for `.lip`: syntax highlighting, snippets, core function completion and hover, Flow/function symbols, saved-file diagnostics, and run/build commands.

Build the tools with `make -C editors tools` from the LIP repository. Set `lip.compilerPath` and `lip.checkerPath` to the generated `lipc` and `lipcheck` executables, or put them on PATH. Use **LIP: Check File**, **LIP: Run File**, and **LIP: Build Executable** from the command palette. Checking saves the file and compiles it without running its Flow; native import discovery follows the compiler's normal behavior.

Use `lip.arguments` for common flags such as `["-entry", "Main", "-host", "demo"]`, `lip.runArguments` for run-only flags such as `-input`, and `lip.projectRoot` for the static import boundary. `lip.checkOnSave` is optional and defaults to false. Tool execution requires a trusted workspace.

`#` starts a comment; `//` is division. Triple-quoted strings preserve indentation. No LSP, formatter, debugger, or semantic rename provider is bundled. See `editors/README.md` in the repository for installation, other editors, and detailed examples.
