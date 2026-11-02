#!/usr/bin/env python3
"""Static Python checks for backend/ that need no Django: (1) every file parses, (2) every `from <local app> import name`
resolves to a module and a defined name, (3) no undefined names (module files with a star-import are skipped for (3)).
This is NOT a substitute for importing the code under Django. Exit 1 on any finding."""
import ast
import builtins
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / 'backend'
SKIP = {'__pycache__', '.venv', 'media_files', 'staticfiles'}
BUILTINS = set(dir(builtins)) | {'__file__', '__name__', '__doc__'}
apps = {p.name for p in ROOT.iterdir() if p.is_dir() and (p / '__init__.py').exists()}
findings = []


def defined_names(tree):
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add((a.asname or a.name).split('.')[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
    return names


def module_file(parts):
    base = ROOT.joinpath(*parts)
    if base.with_suffix('.py').exists():
        return base.with_suffix('.py')
    if (base / '__init__.py').exists():
        return base / '__init__.py'
    return None


files = sorted(p for p in ROOT.rglob('*.py') if not (set(p.parts) & SKIP))
trees = {}
for f in files:
    try:
        trees[f] = ast.parse(f.read_text(), filename=str(f))
    except SyntaxError as e:
        findings.append(f'{f.relative_to(ROOT)}:{e.lineno}: syntax error: {e.msg}')

for f, tree in trees.items():
    rel = f.relative_to(ROOT)
    star = any(isinstance(n, ast.ImportFrom) and any(a.name == '*' for a in n.names) for n in ast.walk(tree))
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if n.level > 0:
                base = f.parent
                for _ in range(n.level - 1):
                    base = base.parent
                parts = list(base.relative_to(ROOT).parts) + (n.module.split('.') if n.module else [])
            elif (n.module or '').split('.')[0] in apps:
                parts = n.module.split('.')
            else:
                continue
            target = module_file(parts)
            if target is None:
                # `from pkg import submodule`
                if all(module_file(parts + [a.name]) for a in n.names):
                    continue
                findings.append(f'{rel}:{n.lineno}: cannot resolve module {".".join(parts)}')
                continue
            if target not in trees:
                continue
            exported = defined_names(trees[target])
            for a in n.names:
                if a.name != '*' and a.name not in exported and module_file(parts + [a.name]) is None:
                    findings.append(f'{rel}:{n.lineno}: {".".join(parts)} has no name {a.name!r}')
    if star:
        continue
    known = defined_names(tree) | BUILTINS
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in known:
            findings.append(f'{rel}:{n.lineno}: undefined name {n.id!r}')

if findings:
    print(f'FAIL — {len(findings)} finding(s):')
    for x in findings:
        print('  -', x)
    sys.exit(1)
print(f'OK — {len(trees)} Python files parse, local imports resolve, no undefined names (static only).')
