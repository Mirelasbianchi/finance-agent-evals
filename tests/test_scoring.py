import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "run_evals", Path(__file__).parent.parent / "evals" / "run_evals.py"
)
run_evals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_evals)


def test_numbers_in_handles_both_locales_and_trailing_punctuation():
    assert 1200.0 in run_evals.numbers_in("You spent R$ 1,200.00.")
    assert 1200.0 in run_evals.numbers_in("Você gastou R$ 1.200,00.")
    assert 58.9 in run_evals.numbers_in("iFood: R$ 58,90, Uber: R$ 23,40")
