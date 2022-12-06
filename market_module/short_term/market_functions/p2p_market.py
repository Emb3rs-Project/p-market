import cvxpy as cp
import numpy as np
import itertools
from math import ceil
import pandas as pd
from pyscipopt.scip import Model
from ...short_term.datastructures.resultobject import ResultData
from ...short_term.datastructures.inputstructs import AgentData, MarketSettings, Network
from ...short_term.constraintbuilder.ConstraintBuilder import ConstraintBuilder
from ...short_term.market_functions.add_energy_budget import add_energy_budget
from ...cases.exceptions.module_runtime_exception import ModuleRuntimeException

def make_p2p_market(agent_data: AgentData, settings: MarketSettings, network: Network):
    """
    Makes the pool market, solves it, and returns a ResultData object with all needed outputs
    :param name: string, can give the resulting ResultData object a name.
    :param agent_data:
    :param settings:
    :return: ResultData object.
    """
    prob_stat = True
    day_nr = []

    ## ITERATE PER DAY 
    h_per_iter = 24 
    nr_of_iter = ceil(settings.nr_of_h / h_per_iter)
    iter_days = range(nr_of_iter)
    h_on_last = settings.nr_of_h - (nr_of_iter - 1)*h_per_iter 

    ## store variables here
    Pn_t = pd.DataFrame(0.0, index=np.arange(settings.nr_of_h), columns=agent_data.agent_name)
    Ln_t = pd.DataFrame(0.0, index=np.arange(settings.nr_of_h), columns=agent_data.agent_name)
    Gn_t = pd.DataFrame(0.0, index=np.arange(settings.nr_of_h), columns=agent_data.agent_name)
    shadow_price_t = []
    Tnm_t = []

    # convert gmin gmax etc
    gmin = agent_data.gmin.to_numpy()
    gmax = agent_data.gmax.to_numpy()
    lmin = agent_data.lmin.to_numpy()
    lmax = agent_data.lmax.to_numpy()
    cost_new = agent_data.cost.to_numpy()
    util_new = agent_data.util.to_numpy()

    for iter_ in iter_days:
        print("running market for day " + str(iter_ + 1) + " of " + str(nr_of_iter))
        # set the number of timesteps in this iteration
        if iter_ == (nr_of_iter - 1):
            nr_of_timesteps = h_on_last
        else:
            nr_of_timesteps = h_per_iter

        selected_timesteps = range(iter_*h_per_iter, iter_*h_per_iter + nr_of_timesteps)


        # collect named constraints in cb
        cb = ConstraintBuilder()

        # prepare parameters
        Gmin = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=gmin[selected_timesteps, :])
        Gmax = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=gmax[selected_timesteps, :])
        Lmin = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=lmin[selected_timesteps, :])
        Lmax = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=lmax[selected_timesteps, :])
        cost = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=cost_new[selected_timesteps, :])
        util = cp.Parameter(
            (nr_of_timesteps, agent_data.nr_of_agents), value=util_new[selected_timesteps, :])

        # variables
        Pn = cp.Variable((nr_of_timesteps, agent_data.nr_of_agents), name="Pn")
        Gn = cp.Variable((nr_of_timesteps, agent_data.nr_of_agents), name="Gn")
        Ln = cp.Variable((nr_of_timesteps, agent_data.nr_of_agents), name="Ln")
        # trades. list of matrix variables, one for each time step.
        Tnm = [cp.Variable((agent_data.nr_of_agents, agent_data.nr_of_agents),
                        name="Tnm_" + str(t)) for t in range(nr_of_timesteps)]
        Snm = [cp.Variable((agent_data.nr_of_agents, agent_data.nr_of_agents),
                        name="Snm_" + str(t)) for t in range(nr_of_timesteps)]
        Bnm = [cp.Variable((agent_data.nr_of_agents, agent_data.nr_of_agents),
                        name="Bnm_" + str(t)) for t in range(nr_of_timesteps)]

        # variable limits -----------------------------
        #  Equality and inequality constraints are element-wise, whether they involve scalars, vectors, or matrices.
        cb.add_constraint(Gmin <= Gn, str_="G_lb")
        cb.add_constraint(Gn <= Gmax, str_="G_ub")
        cb.add_constraint(Lmin <= Ln, str_="L_lb")
        cb.add_constraint(Ln <= Lmax, str_="L_ub")
        # limits on trades
        for t in range(nr_of_timesteps):
            cb.add_constraint(0 <= Bnm[t], str_="B_lb_t" + str(t))
            cb.add_constraint(0 <= Snm[t], str_="S_lb_t" + str(t))
            cb.add_constraint(Tnm[t] == Snm[t] - Bnm[t], str_="def_S_B_t" + str(t))
            # cannot sell more than I generate
            cb.add_constraint(cp.sum(Snm[t], axis=1) == Gn[t, :], str_="S_ub_t" + str(t))
            # cannot buy more than my load
            cb.add_constraint(cp.sum(Bnm[t], axis=1) == Ln[t, :], str_="S_ub_t" + str(t))

        # constraints ----------------------------------
        # define relation between generation, load, and power injection
        cb.add_constraint(Pn == Gn - Ln, str_="def_P")
        for t in range(nr_of_timesteps):
            # trade reciprocity
            for i, j in itertools.product(range(agent_data.nr_of_agents), range(agent_data.nr_of_agents)):
                # if not i == j:
                if j >= i:
                    cb.add_constraint(Tnm[t][i, j] + Tnm[t][j, i] == 0,
                                    str_="reciprocity_t" + str(t) + str(i) + str(j))
            # total trades have to match power injection
            cb.add_constraint(Pn[t, :] == cp.sum(Tnm[t], axis=1), str_="p2p_balance_t" + str(t))

        # add extra constraint if offer type is energy Budget.
        if settings.offer_type == "energyBudget":
            # add energy budget.
            tot_budget = np.sum(0.5 * (lmin[selected_timesteps, :] + lmax[selected_timesteps, :]), axis=0)
            cb = add_energy_budget(cb, load_var=Ln, total_budget=tot_budget, agent_data=agent_data)

        if settings.offer_type == "block":
            # Binary variable
            b = cp.Variable((nr_of_timesteps, agent_data.nr_of_agents), boolean=True, name="b")

            for agent in agent_data.block:
                for j in agent_data.block[agent]:
                    for hour in j:
                        # agent_ids.index(agent)->getting the agent's index
                        cb.add_constraint(Gn[hour, agent_data.agent_name.index(agent)] == Gmax[hour][agent_data.agent_name.index(
                            agent)]*b[hour, agent_data.agent_name.index(agent)], str_='block_constraint1')
                        cb.add_constraint(cp.sum(b[j, agent_data.agent_name.index(agent)]) == len(
                            j)*b[j[0], agent_data.agent_name.index(agent)], str_='block_constraint2')
    #
        # objective function
        # cp.multiply is element-wise multiplication
        total_cost = cp.sum(cp.multiply(cost, Gn))
        total_util = cp.sum(cp.multiply(util, Ln))
        # make different objfun depending on preference settings
        if settings.product_diff == "noPref":
            objective = cp.Minimize(total_cost - total_util)
        else:
            # construct preference matrix
            if settings.product_diff == "co2Emissions":
                emissions_p = np.tile(network.emissions_percentage, (len(agent_data.agent_name), 1))
                for t in range(nr_of_timesteps):
                    co2_penalty = cp.sum(cp.multiply(np.array(emissions_p), Snm[t]))
                objective = cp.Minimize(total_cost - total_util + co2_penalty)
                # print(co2_penalty)

            if settings.product_diff == "networkDistance":
                for t in range(nr_of_timesteps):
                    distance_penalty = cp.sum(cp.multiply(network.all_distance_percentage, Snm[t]))
                objective = cp.Minimize(total_cost - total_util + distance_penalty)

            if settings.product_diff == "losses":
                for t in range(nr_of_timesteps):
                    losses_penalty = cp.sum(cp.multiply(network.all_losses_percentage, Snm[t]))

                objective = cp.Minimize(total_cost - total_util + losses_penalty)

        # define the problem and solve it.
        prob = cp.Problem(objective, constraints=cb.get_constraint_list())
        if settings.offer_type == "block":
            result_ = prob.solve(solver=cp.SCIP)
        else:
            result_ = prob.solve(solver=cp.GUROBI)

        print("problem status: %s" % prob.status)

        if prob.status not in ["infeasible", "unbounded"]:
            # Otherwise, problem.value is inf or -inf, respectively.
            print("Optimal value: %s" % prob.value)
        else:
            print("Problem status is %s" % prob.status)
            prob_stat = False
            day_nr += int(iter_)
            # raise RuntimeError("the problem on day " + str(iter_) + " is " + prob.status)
        
        # compute shadow price 
        shadow_price = [pd.DataFrame(index=agent_data.agent_name, columns=agent_data.agent_name)
                                     for t in settings.timestamps]
        for t in range(nr_of_timesteps):
            if settings.offer_type == 'block':
                if settings.product_diff == 'noPref':
                    max_cost_disp = []
                    for agent in agent_data.agent_name:
                        if Gn[agent][t] > 0:
                            max_cost_disp.append(
                                agent_data.cost[agent][t])
                    for i, j in itertools.product(range(agent_data.nr_of_agents), range(agent_data.nr_of_agents)):
                        if len(max_cost_disp) > 0:
                            shadow_price[t].iloc[i, j] = max(
                                max_cost_disp)
                        elif len(max_cost_disp) == 0:  # if there is no generation
                            shadow_price[t].iloc[i, j] = min(
                                agent_data.cost.T[t])
                        if j == i:
                            shadow_price[t].iloc[i, j] = 0
                else:
                    for i, j in itertools.product(range(agent_data.nr_of_agents), range(agent_data.nr_of_agents)):
                        shadow_price[t].iloc[i,j] = agent_data.cost[agent_data.agent_name[i]][t]
                        if j == i:
                            shadow_price[t].iloc[i, j] = 0

            else:
                for i, j in itertools.product(range(agent_data.nr_of_agents), range(agent_data.nr_of_agents)):
                    # if not i == j:
                    if j >= i:
                        constr_name = "reciprocity_t" + str(t) + str(i) + str(j)
                        shadow_price[t].iloc[i, j] = cb.get_constraint(str_=constr_name).dual_value
                        shadow_price[t].iloc[j, i] = - shadow_price[t].iloc[i, j]

        # store result in result object ---------------------------------------------------------
        variables = prob.variables()
        varnames = [prob.variables()[i].name() for i in range(len(prob.variables()))]
        Pn_t.iloc[selected_timesteps] = list(variables[varnames.index("Pn")].value)
        Ln_t.iloc[selected_timesteps] = list(variables[varnames.index("Ln")].value)
        Gn_t.iloc[selected_timesteps] = list(variables[varnames.index("Gn")].value)
        shadow_price_t += shadow_price
        for t in range(nr_of_timesteps):
            Tnm_t += [pd.DataFrame(Tnm[t].value, columns=agent_data.agent_name, index=agent_data.agent_name)]

    # done iterating
    # store result in result object
    result = ResultData(prob_status=prob_stat, day_nrs=day_nr, 
                        Pn_t=Pn_t, Ln_t=Ln_t, Gn_t=Gn_t, shadow_price_t=shadow_price_t, 
                        agent_data=agent_data, settings=settings, Tnm_t=Tnm_t)

    return result
