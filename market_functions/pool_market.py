import cvxpy as cp
import numpy as np
from datastructures.resultobject import ResultData
from datastructures.inputstructs import AgentData, MarketSettings
from constraintbuilder.ConstraintBuilder import ConstraintBuilder


def make_pool_market(name: str, agent_data: AgentData, settings: MarketSettings):
    """
    Makes the pool market, solves it, and returns a ResultData object with all needed outputs
    :param agent_data:
    :param settings:
    :return: ResultData object.
    """

    if settings.offer_type != "simple":
        ValueError("not implemented yet")
    else:
        # collect named constraints in cb
        cb = ConstraintBuilder()

        # prepare parameters
        Gmin = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.gmin.to_numpy())
        Gmax = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.gmax.to_numpy())
        Lmin = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.lmin.to_numpy())
        Lmax = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.lmax.to_numpy())

        cost = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.cost.to_numpy())
        util = cp.Parameter((settings.nr_of_h, agent_data.nr_of_agents), value=agent_data.util.to_numpy())

        # variables
        Pn = cp.Variable((settings.nr_of_h, agent_data.nr_of_agents), name="Pn")
        Gn = cp.Variable((settings.nr_of_h, agent_data.nr_of_agents), name="Gn")
        Ln = cp.Variable((settings.nr_of_h, agent_data.nr_of_agents), name="Ln")

        # variable limits
        #  Equality and inequality constraints are elementwise, whether they involve scalars, vectors, or matrices.
        cb.add_constraint(Gmin <= Gn, str_="G_lb")
        cb.add_constraint(Gn <= Gmax, str_="G_ub")
        cb.add_constraint(Lmin <= Ln, str_="L_lb")
        cb.add_constraint(Ln <= Lmax, str_="L_ub")

        # define power injection as net generation
        cb.add_constraint(Pn == Gn - Ln, str_="def_P")

        # power balance at each time - a list of n_t constraints
        cb.add_constraint(cp.sum(Pn, axis=1) == 0, str_="powerbalance")

        # objective function
        total_cost = cp.sum(cp.multiply(cost, Gn))  # cp.multiply is element-wise multiplication
        total_util = cp.sum(cp.multiply(util, Ln))
        objective = cp.Minimize(total_cost - total_util)


        # define the problem and solve it.
        prob = cp.Problem(objective, constraints=cb.get_constraint_list())
        result_ = prob.solve(solver=cp.ECOS)
        print("problem status: %s" %prob.status)

        if prob.status not in ["infeasible", "unbounded"]:
            # Otherwise, problem.value is inf or -inf, respectively.
            print("Optimal value: %s" % prob.value)
        else:
            print("Problem is %s" % prob.status)

        # store result in result object
        result = ResultData(name, prob, cb, agent_data, settings)

    return result
