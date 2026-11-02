import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('classify_tsc', Path(__file__).resolve().parents[1] / 'classify_tsc.py')
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)


def run(*lines):
    return ct.classify([l + '\n' for l in lines])


class Classify(unittest.TestCase):
    def test_missing_package_is_allowed(self):
        real, n = run("src/a.ts(1,1): error TS2307: Cannot find module 'react' or its corresponding type declarations.")
        self.assertEqual((real, n), ([], 1))

    def test_missing_RELATIVE_module_is_real(self):
        real, _ = run("src/a.ts(1,1): error TS2307: Cannot find module './nope' or its corresponding type declarations.")
        self.assertEqual(len(real), 1)

    def test_jest_globals_allowed_but_other_names_real(self):
        ok, _ = run("src/t.ts(1,1): error TS2593: Cannot find name 'describe'. Do you need ...")
        self.assertEqual(ok, [])
        real, _ = run("src/a.ts(5,3): error TS2304: Cannot find name 'userId'.")
        self.assertEqual(len(real), 1)

    def test_buffer_global_allowed(self):
        self.assertEqual(run("src/t.ts(7,15): error TS2591: Cannot find name 'Buffer'. Do you need ...")[0], [])

    def test_syntax_errors_are_real(self):
        self.assertEqual(len(run("src/a.ts(3,10): error TS1109: Expression expected.")[0]), 1)

    def test_property_and_argument_errors_are_real(self):
        self.assertEqual(len(run("src/a.ts(3,10): error TS2339: Property 'x' does not exist on type 'Y'.")[0]), 1)
        self.assertEqual(len(run("src/a.ts(3,10): error TS2345: Argument of type 'string' is not assignable.")[0]), 1)

    def test_did_you_mean_undefined_name_is_real(self):
        self.assertEqual(len(run("src/a.tsx(53,15): error TS2552: Cannot find name 'Alert'. Did you mean 'alert'?")[0]), 1)

    def test_unparseable_error_line_is_real(self):
        self.assertEqual(len(run("error TS5107: Option 'moduleResolution=node10' is deprecated")[0]), 1)


if __name__ == '__main__':
    unittest.main()
