#%%
import os
import dill as pickle

import pandas as pd

from plotly.subplots import make_subplots

from model.results_analysis import ResultsAnalysis
import plotting

from tqdm import tqdm


#%% Open pickled oemof run results
# Request user to enter run name to read previously run oemof models
while True:
    run_name = input("Enter run name:")
    cache_dir_path = "./data_cache/" + str(run_name) + "/"

    if os.path.exists(cache_dir_path):  # check if this dir exists
        if os.path.exists(cache_dir_path):  # check if pickled complete model results exist
            with open(cache_dir_path + "model_results.pickle", 'rb') as file:
                print('loading pickled oemof results')
                scenarios = pickle.load(file)
            break
        else:
            print(run_name + ' does not have results yet. Run oemof model first.')
    else:
        print(run_name + ' does not exist.')

# %% Run results analysis
# Dict to collect all scenarios' system KPIs
scenarios_system_kpis = {}
scenarios_system_capacities = {}
for scenario_id, scenario_data in scenarios.items():
    # Extract and process oemof results
    scenario_data['mg_model'].extract_results(scenario_data['mg_model'].results_oemof)

    # Copy this scenario's system results in systems_kpis dict
    scenarios_system_kpis[scenario_id] = scenario_data['mg_model'].results_system
    scenarios_system_capacities[scenario_id] = scenario_data['mg_model'].results_components_capacities.loc['capacity_total']

scenarios_system_kpis = pd.DataFrame(scenarios_system_kpis)
scenarios_system_capacities = pd.DataFrame(scenarios_system_capacities)

# Save dfs as xlsx
scenarios_system_results = pd.concat([scenarios_system_capacities, scenarios_system_kpis])

scenarios_system_results.to_excel(cache_dir_path + '/scenarios_system_resultsv03.xlsx')

#%% Plot scenarios average weekly load profiles

avg_week = pd.DataFrame()

for scenario_id, scenario_data in tqdm(scenarios.items()):
    # Read this scenario's pue load profiles
    pue_load_profiles = pd.read_csv(
        cache_dir_path + 'load_profile_scenario_' + str(scenario_id) + '.csv',  # path to RAMP modelled load profiles
        index_col=0,
        parse_dates=True)

    pue_load = pue_load_profiles['total']

    # Calculate average weekly load profile
    avg_week[scenario_id] = pue_load.groupby(
        pue_load.index.strftime('%a - %H:%M'), sort=False).mean()

#%%
fig2 = make_subplots(2, 1, shared_xaxes=True, vertical_spacing=0.02)
fig_2 = plotting.plotly_df(fig2, avg_week[['a', 'b', 'c', 'd']], legend=['A', 'B', 'C', 'D'], subplot_row=1)
fig_2 = plotting.plotly_df(fig2, avg_week[['a2', 'b2', 'c2', 'd2']], legend=['A_no_lim', 'B_no_lim', 'C_no_lim', 'D_no_lim'], subplot_row=2)

fig2.update_layout(
    title='Modeled PUE load profiles weekly average',
    yaxis_title='kW',
    font=dict(
            size=18
        )
)
fig_2.show()


#%%
fig = make_subplots(2,1)
fig = plotting.plotly_high_res_df(fig, scenarios['a']['mg_model'].results_ac_flows)
fig = plotting.plotly_high_res_df(fig, scenarios['b2']['mg_model'].results_ac_flows, subplot_row=2)

fig.update_layout(
    height=900
)

fig.show_dash(mode='external')