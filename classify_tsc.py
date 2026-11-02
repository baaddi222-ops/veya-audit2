#!/usr/bin/env python3
"""Classifies `tsc` diagnostics produced WITHOUT node_modules installed.
Allowed (only a consequence of packages not being installed):
  * TS2307 / TS7016  module not found / no types  — ONLY for non-relative specifiers (a missing relative import is a real bug)
  * TS2304 / TS2591 / TS2593 / TS2580 / TS2582  'Cannot find name X' — ONLY when X is a test-runner / Node global
  * cascades from missing React / React Native types: TS7006 TS7031 TS7053 TS2741 TS18002 TS2875 TS2503 TS2786
Everything else (syntax TS1xxx, undefined identifiers, wrong property, wrong argument ...) is a REAL error -> exit 1.
Usage: classify_tsc.py <tsc output file>        exit 0 = only allowed diagnostics, 1 = real errors found"""
import re
import sys

NODE_TEST_GLOBALS = {'jest', 'describe', 'it', 'test', 'expect', 'beforeEach', 'afterEach', 'beforeAll', 'afterAll',
                     'Buffer', 'process', 'require', 'module', '__dirname', '__DEV__'}
CASCADE = {'TS7006', 'TS7031', 'TS7053', 'TS2741', 'TS18002', 'TS2875', 'TS2503', 'TS2786'}
LINE = re.compile(r"^(?P<file>[^\n(]+)\((?P<pos>\d+,\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$")


def classify(lines):
    real, allowed = [], 0
    for line in lines:
        m = LINE.match(line.rstrip('\n'))
        if not m:
            if 'error TS' in line:
                real.append(line.rstrip('\n'))          # un-parseable diagnostic: treat as real
            continue
        code, msg = m['code'], m['msg']
        if code in ('TS2307', 'TS7016'):
            spec = re.search(r"module '([^']+)'", msg) or re.search(r"'([^']+)'", msg)
            if spec and not spec.group(1).startswith('.'):
                allowed += 1
                continue
        elif code in ('TS2304', 'TS2591', 'TS2593', 'TS2580', 'TS2582'):
            name = re.search(r"name '([^']+)'", msg)
            if name and name.group(1) in NODE_TEST_GLOBALS:
                allowed += 1
                continue
        elif code in CASCADE:
            allowed += 1
            continue
        real.append(line.rstrip('\n'))
    return real, allowed


def main(argv):
    with open(argv[1], encoding='utf-8', errors='replace') as fh:
        real, allowed = classify(fh)
    print(f'{allowed} diagnostic(s) are only consequences of packages not being installed (types NOT verified)')
    if real:
        print(f'{len(real)} REAL error(s):')
        for r in real:
            print('  ', r)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
