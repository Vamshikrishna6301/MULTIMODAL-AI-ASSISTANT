import concurrent.futures
from core.context_memory import ContextMemory
from execution.executor import ExecutionEngine


def test_parallel_execution_stability():
    engine = ExecutionEngine(ContextMemory())

    decision = {
        "status": "APPROVED",
        "action": "CLICK_INDEX",
        "parameters": {"index": 1}
    }

    def run():
        return engine.execute(decision)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(run) for _ in range(200)]
        results = [f.result() for f in futures]

    assert all(r is not None for r in results)