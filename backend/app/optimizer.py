"""Local CP-SAT smoke example, not the Solaris domain model."""
from ortools.sat.python import cp_model


def smoke_solve() -> int:
    model = cp_model.CpModel()
    allocation = model.new_int_var(0, 10, "allocation")
    model.add(allocation <= 7)
    model.maximize(allocation)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 1
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("No feasible solution")
    return solver.value(allocation)
