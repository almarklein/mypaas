import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_DIR = os.path.dirname(os.path.abspath(sys.modules["__main__"].__file__))
APP_DIR = os.path.join(os.path.dirname(TEST_DIR), "app")

# This makes it possible to run the tests as scripts
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def run_tests(scope):
    """Run all test functions in the given scope."""
    for func in list(scope.values()):
        if callable(func) and func.__name__.startswith("test_"):
            print(f"Running {func.__name__} ...")
            func()
    print("Done")
