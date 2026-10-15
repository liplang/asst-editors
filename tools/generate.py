#!/usr/bin/env python3
"""Generate declarative editor assets from language.json, without dependencies."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "language.json").read_text(encoding="utf-8"))


def write(path, value, prefix=""):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=False)
    if target.suffix == ".sublime-syntax":
        # Sublime capture indices are YAML integer keys, not JSON string keys.
        text = re.sub(r'(?m)^(\s*)"([0-9]+)"(:)', r'\1\2\3', text)
    target.write_text(prefix + text + "\n", encoding="utf-8")


def words(items):
    return r"\b(?:" + "|".join(items) + r")\b"


escape = r'\\(?:["\\nrt]|u\{[0-9a-fA-F]{1,6}\})'
number = r"\b(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"
operator = r"<\+|->|=>|==|!=|<=|>=|&&|\|\||//|\*\*|\*/|\|>|[=+*/%!<>?\-]"
grammar = {
    "name": "LIP", "scopeName": "source.lip", "fileTypes": ["lip"],
    "patterns": [{"include": "#comments"}, {"include": "#strings"}, {"include": "#code"}],
    "repository": {
        "comments": {"name": "comment.line.number-sign.lip", "begin": "#", "end": "$"},
        "strings": {"patterns": [
            {"name": "string.quoted.triple.lip", "begin": '"""', "end": '"""', "patterns": [{"include": "#escapes"}]},
            {"name": "string.quoted.double.lip", "begin": '"', "end": '"|$', "patterns": [{"include": "#escapes"}]},
        ]},
        "escapes": {"patterns": [
            {"name": "constant.character.escape.lip", "match": escape},
            {"name": "invalid.illegal.escape.lip", "match": r"\\."},
        ]},
        "code": {"patterns": [
            {"match": r"\b(fn|flow)\s+([A-Za-z_][A-Za-z0-9_]*)", "captures": {
                "1": {"name": "keyword.declaration.lip"}, "2": {"name": "entity.name.function.lip"}}},
            {"match": r"(:|->)\s*(" + "|".join(data["types"] + ["void", "null"]) + r")\b(\?)?", "captures": {
                "1": {"name": "punctuation.separator.type.lip"}, "2": {"name": "storage.type.lip"},
                "3": {"name": "keyword.operator.optional.lip"}}},
            {"name": "keyword.control.lip", "match": words(data["keywords"])},
            {"name": "constant.language.lip", "match": words(["true", "false", "null"])},
            {"name": "support.function.builtin.lip", "match": r"(?<![\w.])(?:" + "|".join(["claim"] + list(data["builtins"])) + r")\b"},
            {"name": "entity.name.function.call.lip", "match": r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"},
            {"name": "constant.numeric.lip", "match": number},
            {"name": "keyword.operator.lip", "match": operator},
            {"name": "punctuation.section.lip", "match": r"[()\[\]{}]"},
            {"name": "punctuation.separator.lip", "match": "[.,:;]"},
            {"name": "punctuation.separator.continuation.lip", "match": r"\\$"},
        ]},
    },
}
write("vscode/syntaxes/lip.tmLanguage.json", grammar)
write("vscode/snippets/lip.json", data["snippets"])
write("vscode/language-configuration.json", {
    "comments": {"lineComment": "#"},
    "brackets": [["{", "}"], ["[", "]"], ["(", ")"]],
    "autoClosingPairs": [{"open": a, "close": b, "notIn": ["string", "comment"]}
                         for a, b in [("{", "}"), ("[", "]"), ("(", ")"), ('"', '"')]],
    "surroundingPairs": [["{", "}"], ["[", "]"], ["(", ")"], ['"', '"']],
    "wordPattern": r"[A-Za-z_][A-Za-z0-9_]*",
    "indentationRules": {
        "increaseIndentPattern": r'^\s*[^#]*[\{\[(]\s*(?:#.*)?$',
        "decreaseIndentPattern": r"^\s*[}\])]",
    },
})
write("vscode/language-data.json", {key: data[key] for key in ["keywords", "types", "builtins"]})
write("zed/snippets/lip.json", data["snippets"])
sublime = {
    "name": "LIP", "file_extensions": ["lip"], "scope": "source.lip", "version": 2,
    "contexts": {
        "main": [
            {"match": "#", "scope": "punctuation.definition.comment.lip", "push": [
                {"meta_scope": "comment.line.number-sign.lip"}, {"match": "$", "pop": True}]},
            {"match": '"""', "scope": "punctuation.definition.string.begin.lip", "push": "triple"},
            {"match": '"', "scope": "punctuation.definition.string.begin.lip", "push": "string"},
        ] + [{"match": p["match"], **({"scope": p["name"]} if "name" in p else {
            "captures": {int(k): v["name"] for k, v in p["captures"].items()}})}
             for p in grammar["repository"]["code"]["patterns"]],
        "escapes": [{"match": escape, "scope": "constant.character.escape.lip"},
                    {"match": r"\\.", "scope": "invalid.illegal.escape.lip"}],
        "triple": [{"meta_scope": "string.quoted.triple.lip"}, {"include": "escapes"},
                   {"match": '"""', "scope": "punctuation.definition.string.end.lip", "pop": True}],
        "string": [{"meta_scope": "string.quoted.double.lip"}, {"include": "escapes"},
                   {"match": '"|$', "scope": "punctuation.definition.string.end.lip", "pop": True}],
    },
}
write("sublime/LIP.sublime-syntax", sublime, "%YAML 1.2\n---\n")
write("sublime/LIP.sublime-completions", {
    "scope": "source.lip - string - comment",
    "completions": [{"trigger": snippet["prefix"], "contents": "\n".join(snippet["body"])
                     if isinstance(snippet["body"], list) else snippet["body"]}
                    for snippet in data["snippets"].values()] + list(data["builtins"]),
})
print("Generated VS Code, Zed snippets, and Sublime Text assets.")
