#!/usr/bin/env python3
"""Build local VSIX or Zed dev extension; all output stays under .build/editors."""
import argparse
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT.parent / ".build" / "editors"


def vscode():
    package = json.loads((ROOT / "vscode/package.json").read_text(encoding="utf-8"))
    target = BUILD / "lip-language.vsix"
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{package['name']}" Version="{package['version']}" Publisher="{package['publisher']}"/>
    <DisplayName>{escape(package['displayName'])}</DisplayName>
    <Description xml:space="preserve">{escape(package['description'])}</Description>
    <Tags>lip,language</Tags><Categories>Programming Languages,Snippets</Categories>
    <Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="{package['engines']['vscode']}"/></Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
  <Dependencies/>
  <Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>
'''
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("extension.vsixmanifest", manifest)
        archive.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="json" ContentType="application/json"/>
<Default Extension="js" ContentType="application/javascript"/>
<Default Extension="md" ContentType="text/markdown"/>
<Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>''')
        for file in sorted((ROOT / "vscode").rglob("*")):
            if file.is_file() and not any(part.startswith(".") for part in file.relative_to(ROOT / "vscode").parts):
                archive.write(file, "extension/" + file.relative_to(ROOT / "vscode").as_posix())
    print(target)


def zed():
    if not shutil.which("tree-sitter"):
        raise SystemExit("Zed packaging needs tree-sitter CLI >= 0.25 on PATH (npm install -g tree-sitter-cli).")
    if not shutil.which("git"):
        raise SystemExit("Zed packaging needs git on PATH.")
    target = BUILD / "zed"
    grammar = BUILD / "tree-sitter-lip"
    grammar.mkdir(parents=True, exist_ok=True)
    for file in (ROOT / "tree-sitter-lip").iterdir():
        if file.is_file():
            shutil.copy2(file, grammar / file.name)
    subprocess.run(["tree-sitter", "generate", "--abi", "14"], cwd=grammar, check=True)
    for args in [["init", "-q"], ["add", "grammar.js", "tree-sitter.json", "src"],
                 ["-c", "user.name=LIP editor package", "-c", "user.email=editor@localhost", "-c", "commit.gpgsign=false",
                  "commit", "-q", "--allow-empty", "-m", "Local LIP editor grammar"]]:
        subprocess.run(["git", *args], cwd=grammar, check=True)
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=grammar, text=True).strip()
    shutil.copytree(ROOT / "zed/languages", target / "languages", dirs_exist_ok=True)
    shutil.copytree(ROOT / "zed/snippets", target / "snippets", dirs_exist_ok=True)
    (target / "extension.toml").write_text(
        'id = "lip"\nname = "LIP"\nversion = "1.0.0"\nschema_version = 1\n'
        'description = "LIP 1.0 syntax, indentation and outline"\nauthors = ["LIP contributors"]\n'
        'languages = ["languages/lip"]\n\n[grammars.lip]\n'
        f'repository = {json.dumps(grammar.as_uri())}\nrev = {json.dumps(rev)}\n', encoding="utf-8"
    )
    print(f"In Zed run 'zed: install dev extension' and select {target}")
    print("The local grammar repository must remain present until installation finishes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("editor", choices=["vscode", "zed"])
    args = parser.parse_args()
    {"vscode": vscode, "zed": zed}[args.editor]()
