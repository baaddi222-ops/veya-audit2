#!/usr/bin/env python3
"""
STATIC model <-> hand-written-migration consistency checker (v2). Needs only Python.

WHAT IT IS: an `ast` comparison. It replays CreateModel / AddField / AlterField / RemoveField /
DeleteModel / AddIndex / RemoveIndex / AddConstraint / RemoveConstraint (+ options inside CreateModel)
and compares the resulting state with models.py: field types, every kwarg (max_length, null, blank,
unique, db_index, default, choices, validators, related_name, on_delete, auto_now*, editable ...),
FK/M2M targets, Meta.ordering, indexes and constraints (names + definitions, Q-expressions normalised),
fields inherited from AbstractBaseUser / PermissionsMixin, migration dependencies (existence, cycles,
cross-app FK coverage) and apps that have models but no migrations.

WHAT IT IS NOT (never read a PASS as "Django accepts this"):
  * It is NOT Django's autodetector. `python manage.py makemigrations --check --dry-run` stays mandatory.
  * It cannot see SQL generated for PostgreSQL, regex semantics inside CHECK constraints, or real DB state.
  * Anything it cannot interpret is reported under UNVERIFIED (never silently skipped).

Exit codes: 0 = no problems found and nothing uninterpretable; 1 = problems found;
            2 = no problems, but some constructs could not be interpreted (see UNVERIFIED).
"""
import ast
import sys
from pathlib import Path

FK_TYPES = {'ForeignKey', 'OneToOneField', 'ManyToManyField'}
IGNORED_KW = {'serialize', 'verbose_name', 'help_text', 'auto_created', 'verbose_name_plural'}
FALSE_DEFAULT = {'null', 'blank', 'unique', 'db_index', 'primary_key', 'auto_now', 'auto_now_add'}
IMPLICIT = {('EmailField', 'max_length'): '254', ('URLField', 'max_length'): '200', ('SlugField', 'max_length'): '50'}
INHERITED = {
    'AbstractBaseUser': {'password': ('CharField', {'max_length': '128'}),
                         'last_login': ('DateTimeField', {'blank': 'True', 'null': 'True'})},
    'PermissionsMixin': {'is_superuser': ('BooleanField', {'default': 'False'}),
                         'groups': ('ManyToManyField', {'blank': 'True'}, 'auth.group'),
                         'user_permissions': ('ManyToManyField', {'blank': 'True'}, 'auth.permission')},
}
NOT_APPS = {'config', 'core', 'tests', 'scripts', 'tools'}


class Unsupported(Exception):
    pass


def tail(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    return ast.unparse(n)


def nv(n, consts, depth=0):
    """Canonical string for a value expression (module prefixes stripped, constants resolved)."""
    if isinstance(n, ast.Constant):
        return repr(n.value)
    if isinstance(n, ast.Name):
        if n.id in consts and depth < 6:
            return nv(consts[n.id], consts, depth + 1)
        return n.id
    if isinstance(n, (ast.List, ast.Tuple)):
        return '[' + ', '.join(nv(e, consts, depth) for e in n.elts) + ']'
    if isinstance(n, ast.Attribute):
        return n.attr
    if isinstance(n, ast.Call):
        args = [nv(a, consts, depth) for a in n.args]
        kws = sorted(f'{k.arg}={nv(k.value, consts, depth)}' for k in n.keywords)
        return f"{tail(n.func)}({', '.join(args + kws)})"
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        return '-' + nv(n.operand, consts, depth)
    return ast.unparse(n)


def qn(n, consts):
    """Canonical string for a Q-expression (Q(...), ~Q, |, &, nested Q, _negated, _connector)."""
    def fmt(t):
        neg, conn, kids = t
        return f"{'NOT ' if neg else ''}Q[{conn}]({', '.join(sorted(kids))})"

    def build(x):
        if isinstance(x, ast.UnaryOp) and isinstance(x.op, ast.Invert):
            neg, conn, kids = build(x.operand)
            return (not neg, conn, kids)
        if isinstance(x, ast.BinOp) and isinstance(x.op, (ast.BitOr, ast.BitAnd)):
            return (False, 'OR' if isinstance(x.op, ast.BitOr) else 'AND', [fmt(build(x.left)), fmt(build(x.right))])
        if isinstance(x, ast.Call) and tail(x.func) == 'Q':
            neg, conn, kids = False, 'AND', []
            for a in x.args:
                if isinstance(a, ast.Tuple) and len(a.elts) == 2:
                    kids.append(f'({nv(a.elts[0], consts)}, {nv(a.elts[1], consts)})')
                else:
                    kids.append(fmt(build(a)))
            for k in x.keywords:
                if k.arg == '_negated':
                    neg = bool(ast.literal_eval(k.value))
                elif k.arg == '_connector':
                    conn = ast.literal_eval(k.value)
                else:
                    kids.append(f'({k.arg!r}, {nv(k.value, consts)})')
            return (neg, conn, kids)
        raise Unsupported(ast.unparse(x))
    return fmt(build(n))


def collect_consts(body):
    consts = {}
    for st in body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1:
            t = st.targets[0]
            if isinstance(t, ast.Name):
                consts[t.id] = st.value
            elif isinstance(t, ast.Tuple) and isinstance(st.value, ast.Tuple) and len(t.elts) == len(st.value.elts):
                for a, b in zip(t.elts, st.value.elts):
                    if isinstance(a, ast.Name):
                        consts[a.id] = b
    return consts


class Project:
    def __init__(self, root: Path):
        self.root = root
        self.problems, self.unverified = [], []
        self.auth_user_model = 'accounts.user'
        base = root / 'config' / 'settings' / 'base.py'
        if base.exists():
            for st in ast.parse(base.read_text()).body:
                if isinstance(st, ast.Assign) and getattr(st.targets[0], 'id', '') == 'AUTH_USER_MODEL':
                    self.auth_user_model = ast.literal_eval(st.value).lower()
        self.apps = sorted(p.name for p in root.iterdir()
                           if p.is_dir() and p.name not in NOT_APPS and (p / 'models.py').exists())

    def bad(self, msg): self.problems.append(msg)
    def unv(self, msg): self.unverified.append(msg)

    def resolve_to(self, node, consts, app, imports, local_models):
        if node is None:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.lower()
            return v if '.' in v else f'{app}.{v}'
        if isinstance(node, ast.Attribute) and node.attr == 'AUTH_USER_MODEL':
            return self.auth_user_model
        if isinstance(node, ast.Name):
            if node.id in imports:
                return f'{imports[node.id]}.{node.id.lower()}'
            if node.id in local_models:
                return f'{app}.{node.id.lower()}'
        return nv(node, consts).lower()

    def field_sig(self, call, consts, app, imports, local_models):
        typ = tail(call.func)
        kws, to_node = {}, None
        if typ in FK_TYPES and call.args:
            to_node = call.args[0]
        for k in call.keywords:
            if k.arg == 'to':
                to_node = k.value
            elif k.arg and k.arg not in IGNORED_KW:
                kws[k.arg] = nv(k.value, consts)
        for key in FALSE_DEFAULT:
            kws.setdefault(key, 'False')
        kws.setdefault('editable', 'True')
        if (typ, 'max_length') in IMPLICIT:
            kws.setdefault('max_length', IMPLICIT[(typ, 'max_length')])
        return {'type': typ, 'kw': kws, 'to': self.resolve_to(to_node, consts, app, imports, local_models)}

    def named_items(self, node, consts, kind):
        out = []
        if node is None:
            return out
        for el in node.elts:
            name = next((nv(k.value, consts).strip("'") for k in el.keywords if k.arg == 'name'), None)
            typ = tail(el.func)
            try:
                if typ == 'CheckConstraint':
                    cond = next(k.value for k in el.keywords if k.arg in ('condition', 'check'))
                    canon = f'CheckConstraint(name={name}, {qn(cond, consts)})'
                else:
                    canon = nv(el, consts).replace(' ', '')
            except (Unsupported, StopIteration) as e:
                self.unv(f'{kind} {name!r}: cannot interpret ({e})')
                canon = f'UNPARSEABLE:{name}'
            out.append((name, canon))
        return out

    def read_models(self, app):
        tree = ast.parse((self.root / app / 'models.py').read_text())
        imports = {}
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module and n.module.endswith('models'):
                for a in n.names:
                    imports[a.asname or a.name] = n.module.split('.')[0]
        local = {c.name for c in tree.body if isinstance(c, ast.ClassDef)}
        out = {}
        for cls in [c for c in tree.body if isinstance(c, ast.ClassDef)]:
            bases = [tail(b) for b in cls.bases]
            if not set(bases) & {'Model', 'AbstractBaseUser', 'PermissionsMixin'}:
                continue
            consts = collect_consts(cls.body)
            fields, meta = {}, {'ordering': None, 'indexes': [], 'constraints': []}
            for st in cls.body:
                if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) and isinstance(st.targets[0], ast.Name):
                    t = tail(st.value.func)
                    if t.endswith('Field') or t in FK_TYPES:
                        fields[st.targets[0].id] = self.field_sig(st.value, consts, app, imports, local)
                if isinstance(st, ast.ClassDef) and st.name == 'Meta':
                    for m in st.body:
                        if isinstance(m, ast.Assign) and isinstance(m.targets[0], ast.Name):
                            key = m.targets[0].id
                            if key == 'ordering':
                                meta['ordering'] = nv(m.value, consts)
                            elif key in ('indexes', 'constraints'):
                                meta[key] = self.named_items(m.value, consts, key)
                            elif key in ('unique_together', 'index_together'):
                                self.unv(f'{app}.{cls.name}: Meta.{key} is not compared')
            out[cls.name.lower()] = {'fields': fields, 'meta': meta, 'bases': bases}
        return out

    def read_migrations(self, app):
        state, files, deps_by_file = {}, [], {}
        mdir = self.root / app / 'migrations'
        for f in sorted(mdir.glob('0*.py')) if mdir.exists() else []:
            files.append(f.stem)
            tree = ast.parse(f.read_text())
            deps = set()
            cls = next((c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == 'Migration'), None)
            if cls is None:
                self.bad(f'{app}/{f.name}: no Migration class')
                deps_by_file[f.stem] = deps
                continue
            ops_node = None
            for st in cls.body:
                if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name):
                    name = st.targets[0].id
                    if name == 'dependencies':
                        for e in st.value.elts:
                            if isinstance(e, ast.Tuple):
                                deps.add((ast.literal_eval(e.elts[0]), ast.literal_eval(e.elts[1])))
                            elif isinstance(e, ast.Call) and tail(e.func) == 'swappable_dependency':
                                deps.add((self.auth_user_model.split('.')[0], '*'))
                            else:
                                self.unv(f'{app}/{f.name}: unrecognised dependency {ast.unparse(e)}')
                    elif name == 'operations':
                        ops_node = st.value
            deps_by_file[f.stem] = deps
            local_models = set(state)
            for op in (ops_node.elts if ops_node else []):
                if not isinstance(op, ast.Call):
                    self.unv(f'{app}/{f.name}: non-call operation')
                    continue
                opn, kw = tail(op.func), {k.arg: k.value for k in op.keywords}

                def mname():
                    return kw['model_name'].value.lower()
                try:
                    if opn == 'CreateModel':
                        name = kw['name'].value.lower()
                        fields = {t.elts[0].value: self.field_sig(t.elts[1], {}, app, {}, local_models) for t in kw['fields'].elts}
                        ordering = idx = cons = None
                        options = kw.get('options')
                        if options is not None:
                            for k, v in zip(options.keys, options.values):
                                if k.value == 'ordering':
                                    ordering = nv(v, {})
                                elif k.value == 'indexes':
                                    idx = self.named_items(v, {}, 'indexes')
                                elif k.value == 'constraints':
                                    cons = self.named_items(v, {}, 'constraints')
                                elif k.value not in ('abstract', 'verbose_name', 'verbose_name_plural'):
                                    self.unv(f'{app}/{f.name}: CreateModel option {k.value!r} not compared')
                        state[name] = {'fields': fields, 'fk_files': {fn: f.stem for fn in fields},
                                       'meta': {'ordering': ordering, 'indexes': idx or [], 'constraints': cons or []}}
                        local_models.add(name)
                    elif opn in ('AddField', 'AlterField'):
                        s = state[mname()]
                        s['fields'][kw['name'].value] = self.field_sig(kw['field'], {}, app, {}, local_models)
                        s['fk_files'][kw['name'].value] = f.stem
                    elif opn == 'RemoveField':
                        state[mname()]['fields'].pop(kw['name'].value, None)
                    elif opn == 'DeleteModel':
                        state.pop(kw['name'].value.lower(), None)
                    elif opn == 'AddIndex':
                        state[mname()]['meta']['indexes'] += self.named_items(ast.List(elts=[kw['index']]), {}, 'indexes')
                    elif opn == 'RemoveIndex':
                        n = kw['name'].value
                        state[mname()]['meta']['indexes'] = [i for i in state[mname()]['meta']['indexes'] if i[0] != n]
                    elif opn == 'AddConstraint':
                        state[mname()]['meta']['constraints'] += self.named_items(ast.List(elts=[kw['constraint']]), {}, 'constraints')
                    elif opn == 'RemoveConstraint':
                        n = kw['name'].value
                        state[mname()]['meta']['constraints'] = [c for c in state[mname()]['meta']['constraints'] if c[0] != n]
                    else:
                        self.unv(f'{app}/{f.name}: operation {opn} is not interpreted')
                except KeyError as e:
                    self.bad(f'{app}/{f.name}: {opn} refers to unknown model/argument {e}')
        return state, files, deps_by_file

    def compare(self, app, models, state):
        for mname, mod in models.items():
            st = state.get(mname)
            if st is None:
                self.bad(f'{app}.{mname}: model has NO migration')
                continue
            inherited = set()
            for base, expected in INHERITED.items():
                if base not in mod['bases']:
                    continue
                for fname, spec in expected.items():
                    inherited.add(fname)
                    mf = st['fields'].get(fname)
                    if mf is None:
                        self.bad(f'{app}.{mname}.{fname}: inherited from {base} but missing in migrations')
                        continue
                    if mf['type'] != spec[0]:
                        self.bad(f'{app}.{mname}.{fname}: type migration={mf["type"]} expected={spec[0]}')
                    for k, v in spec[1].items():
                        if mf['kw'].get(k) != v:
                            self.bad(f'{app}.{mname}.{fname}.{k}: migration={mf["kw"].get(k)} expected={v}')
                    if len(spec) > 2 and mf['to'] != spec[2]:
                        self.bad(f'{app}.{mname}.{fname}: target migration={mf["to"]} expected={spec[2]}')
            for fname, sig in mod['fields'].items():
                msig = st['fields'].get(fname)
                if msig is None:
                    self.bad(f'{app}.{mname}.{fname}: missing in migrations')
                    continue
                if sig['type'] != msig['type']:
                    self.bad(f'{app}.{mname}.{fname}: type model={sig["type"]} migration={msig["type"]}')
                if sig['to'] != msig['to']:
                    self.bad(f'{app}.{mname}.{fname}: target model={sig["to"]} migration={msig["to"]}')
                for k in sorted(set(sig['kw']) | set(msig['kw'])):
                    if sig['kw'].get(k) != msig['kw'].get(k):
                        self.bad(f'{app}.{mname}.{fname}.{k}: model={sig["kw"].get(k)} migration={msig["kw"].get(k)}')
            for extra in sorted(set(st['fields']) - set(mod['fields']) - inherited - {'id'}):
                self.bad(f'{app}.{mname}.{extra}: in migrations but not in model')
            if mod['meta']['ordering'] != st['meta']['ordering']:
                self.bad(f'{app}.{mname}.Meta.ordering: model={mod["meta"]["ordering"]} migration={st["meta"]["ordering"]}')
            for key in ('indexes', 'constraints'):
                a, b = dict(mod['meta'][key]), dict(st['meta'][key])
                for n in sorted(set(a) | set(b), key=str):
                    if n not in b:
                        self.bad(f'{app}.{mname}.{key}: {n!r} in model, missing in migrations')
                    elif n not in a:
                        self.bad(f'{app}.{mname}.{key}: {n!r} in migrations, missing in model')
                    elif a[n] != b[n]:
                        self.bad(f'{app}.{mname}.{key}.{n}: definition differs | model: {a[n]} | migration: {b[n]}')
        for mname in sorted(set(state) - set(models)):
            self.bad(f'{app}.{mname}: in migrations but not in models')

    @staticmethod
    def _reach(graph, start):
        seen, stack = set(), [start]
        while stack:
            n = stack.pop()
            for m in graph.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        return seen

    def check_dependencies(self, all_deps, all_state):
        apps_with_files = {a for a, (files, _) in all_deps.items() if files}
        nodes = {(a, f) for a, (files, _) in all_deps.items() for f in files}
        graph = {}
        for a, (files, per) in all_deps.items():
            for f in files:
                edges = set()
                for (x, y) in per[f]:
                    if x in apps_with_files:
                        if y == '*':
                            edges |= {(x, g) for g in all_deps[x][0]}
                        elif (x, y) in nodes:
                            edges.add((x, y))
                        else:
                            self.bad(f'{a}/{f}: depends on missing migration {x}.{y}')
                    elif x != 'auth':
                        self.bad(f'{a}/{f}: depends on {x}.{y}, an app with no migrations in this project')
                graph[(a, f)] = edges
        for a, (files, per) in all_deps.items():
            for i, f in enumerate(files[1:], 1):
                if (a, files[i - 1]) not in self._reach(graph, (a, f)):
                    self.bad(f'{a}/{f}: does not (transitively) depend on the previous migration {files[i - 1]}')
        reported = set()
        for start in graph:
            stack, seen = [(start, [start])], set()
            while stack:
                node, path = stack.pop()
                hit = False
                for nxt in graph.get(node, ()):
                    if nxt == start:
                        key = frozenset(path)
                        if key not in reported:
                            reported.add(key)
                            self.bad('dependency cycle: ' + ' -> '.join(f'{x}.{y}' for x, y in path + [start]))
                        hit = True
                        break
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append((nxt, path + [nxt]))
                if hit:
                    break
        for a, state in all_state.items():
            for mname, st in state.items():
                for fname, sig in st['fields'].items():
                    to = sig['to']
                    if not to or to.split('.')[0] == a:
                        continue
                    tapp = to.split('.')[0]
                    fstem = st['fk_files'].get(fname)
                    direct = {x for (x, _) in all_deps[a][1].get(fstem, set())}
                    reach = {x for (x, _) in self._reach(graph, (a, fstem))} | direct
                    if tapp not in reach:
                        self.bad(f'{a}/{fstem}: {mname}.{fname} points to "{to}" but the migration does not depend on app "{tapp}"')

    def run(self):
        all_deps, all_state = {}, {}
        for app in self.apps:
            models = self.read_models(app)
            state, files, per = self.read_migrations(app)
            all_deps[app] = (files, per)
            all_state[app] = state
            if models and not files:
                self.bad(f'{app}: has models but no migration files')
            self.compare(app, models, state)
        self.check_dependencies(all_deps, all_state)
        return self


LIMITS = [
    "Django's real autodetector (`makemigrations --check --dry-run`) was NOT run",
    'generated SQL / PostgreSQL behaviour (e.g. the `\\S` regex CHECK constraints) was NOT tested',
    'no database was touched; applying the migrations (`migrate`) was NOT tested',
]


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[2] / 'backend'
    p = Project(root).run()
    print(f'apps checked: {", ".join(p.apps)}')
    if p.problems:
        print(f'\nFAIL — {len(p.problems)} problem(s):')
        for x in p.problems:
            print('  -', x)
    if p.unverified:
        print(f'\nUNVERIFIED — {len(p.unverified)} construct(s) not interpreted:')
        for x in p.unverified:
            print('  -', x)
    print('\nLimits of this static check (always true):')
    for x in LIMITS:
        print('  *', x)
    if p.problems:
        return 1
    if p.unverified:
        print('\nNO PROBLEMS FOUND, but some constructs were not interpreted (exit 2).')
        return 2
    print('\nOK — no inconsistencies found between models and migrations (static check only).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
