import unittest
# Note: tests_execution.py tests the old Executor class which is now ExecutionEngine
# These tests are deprecated and can be skipped
# For new executor tests, see test_router.py or test_execution_engine.py


class TestExecutorDeprecated(unittest.TestCase):
    def test_skip_old_executor_tests(self):
        """Old Executor class has been replaced with ExecutionEngine."""
        self.skipTest("Old Executor class replaced; see ExecutionEngine tests")


if __name__ == "__main__":
    unittest.main()
