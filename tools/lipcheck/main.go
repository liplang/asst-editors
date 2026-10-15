// lipcheck is an editor-only, compile-only bridge to the existing LIP checker.
package main

import (
	"errors"
	"flag"
	"fmt"
	"lip/script"
	"os"
	"path/filepath"
)

func main() {
	flags := flag.NewFlagSet("lipcheck", flag.ContinueOnError)
	entry := flags.String("entry", "", "Flow entry (required for multiple Flows)")
	project := flags.String("project", "", "static import project root (default: file directory)")
	hostName := flags.String("host", "", "Host: empty or demo")
	flags.Usage = func() {
		fmt.Fprintln(flags.Output(), "usage: lipcheck [-entry Name] [-project DIR] [-host demo] file.lip\nCompile saved source without running its Flow; diagnostics: absolute-file:line:column: code: message.")
	}
	if err := flags.Parse(os.Args[1:]); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return
		}
		os.Exit(2)
	}
	if flags.NArg() != 1 {
		flags.Usage()
		os.Exit(2)
	}
	filename, err := filepath.Abs(flags.Arg(0))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	root := *project
	if root == "" {
		root = filepath.Dir(filename)
	}
	root, err = filepath.Abs(root)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	host := script.Host{}
	switch *hostName {
	case "":
	case "demo":
		host, err = script.DemoHost()
	default:
		err = fmt.Errorf("unknown Host %q", *hostName)
	}
	if err == nil {
		host = script.NewNativeHost(host)
		defer host.Close()
		var sources script.SourceSet
		sources, err = script.LoadSourceSet(filename, root)
		if err == nil {
			_, err = script.CompileSourceSet(sources, host, script.CompileOptions{Entry: *entry})
		}
	}
	if err == nil {
		return
	}
	line, column, message := 1, 1, err.Error()
	var diagnostic *script.Diagnostic
	if errors.As(err, &diagnostic) {
		if diagnostic.SourceID != "" {
			filename = filepath.Join(root, filepath.FromSlash(diagnostic.SourceID))
		}
		if diagnostic.Line > 0 {
			line, column = diagnostic.Line, max(1, diagnostic.Column)
		}
		message = diagnostic.Code + ": " + diagnostic.Message
	}
	fmt.Fprintf(os.Stderr, "%s:%d:%d: %s\n", filename, line, column, message)
	os.Exit(1)
}
