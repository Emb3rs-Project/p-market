## Test pydantic 

from market_module.short_term.datastructures.inputstructs import MarketSettings, AgentData

# good settings
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", market_design="pool", network_type=None,
                    el_dependent=False, el_price=None)

# bad settings
settings = MarketSettings(nr_of_h="2", offer_type="simple", product_diff="noPref", market_design="pool", 
                    network_type=None,
                    el_dependent=False, el_price=None)

settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff=4, market_design=5, network_type=None,
                    el_price=None, el_dependent=True)

# bad settings
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="co2Emissions", 
                market_design="pool", network_type=None,
                el_dependent=False, el_price=None)

# bad community settings 
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", 
                market_design="community", network_type=None,
                el_dependent=False, el_price=None, community_objective="autonomy", 
                                gamma_peak=10,
                                gamma_imp=None, 
                                gamma_exp=None)

settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", 
                market_design="community", network_type=None,
                el_dependent=False, el_price=None, community_objective="autonomy", 
                                gamma_peak=None,
                                gamma_imp=None, 
                                gamma_exp=None)

settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", 
                market_design="community", network_type=None,
                el_dependent=False, el_price=None, community_objective="autonomy", 
                                gamma_peak=5,
                                gamma_imp=None, 
                                gamma_exp=-10)
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", 
                market_design="community", network_type=None,
                el_dependent=False, el_price=None, community_objective="peakShaving", 
                                gamma_peak=None,
                                gamma_imp=5, 
                                gamma_exp=-6)
## Agentdata
# good settings
from market_module.short_term.datastructures.inputstructs import MarketSettings, AgentData

settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="noPref", market_design="pool", network_type=None,
                    el_dependent=False, el_price=None)

# good agent data
agent_data = AgentData(settings=settings,
                        agent_name=["1", "3", "6"],
                           gmax=[[1,2,3], [1,2,3]],
                           lmax=[[1,2,3],[1,2,3]],
                           cost=[[1,2,3],[1,2,3]], util=[[1,2,3],[1,2,3]],
                           co2=None,
                           is_in_community=None,
                           block=None, is_chp=None,
                           chp_pars=None)

# bad agentdata: missing co2. 
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="co2Emissions", market_design="p2p", network_type=None,
                    el_dependent=False, el_price=None)

agent_data = AgentData(settings=settings,
                        agent_name=["1", "3", "6"],
                           gmax=[[1,2,3], [1,2,3]],
                           lmax=[[1,2,3],[1,2,3]],
                           cost=[[1,2,3],[1,2,3]], util=[[1,2,3],[1,2,3]],
                           co2=None,
                           is_in_community=None,
                           block=None, is_chp=None,
                           chp_pars=None)
# bad agentdata: missing co2. 
settings = MarketSettings(nr_of_h=2, offer_type="simple", product_diff="co2Emissions", market_design="p2p", network_type=None,
                    el_dependent=False, el_price=None)

agent_data = AgentData(settings=settings,
                        agent_name=["1", "3", "6"],
                           gmax=[[1,2,3], [1,2,3]],
                           lmax=[[1,2,3],[1,2,3]],
                           cost=[[1,2,3],[1,2,3]], util=[[1,2,3],[1,2,3]],
                           co2=None,
                           is_in_community=None,
                           block=None, is_chp=None,
                           chp_pars=None)