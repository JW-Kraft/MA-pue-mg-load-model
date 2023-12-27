#%% Build oemof microgrid model
import os
import json
from tqdm import tqdm

# to avoid pickle problems, see:
# https://stackoverflow.com/questions/68679806/attributeerror-cant-pickle-local-object-pre-datasets-locals-lambda-when
import dill as pickle

import pandas as pd

from oemof import solph
from plotly.subplots import make_subplots

import plotting
from model.data_input import InputData
from model.oemof_model import OemofModel
import helpers


#%% ---- Prepare ----

# Request user to enter run name to read previously modeled load profiles from cache
while True:
    run_name = input("Enter run name:")
    cache_dir_path = "./data_cache/" + str(run_name) + "/"

    if os.path.exists(cache_dir_path):  # check if this dir exists
        with open(cache_dir_path + "scenarios_information.json", "r") as file:
            # read scenario_information from json

            scenarios = json.load(file)  # dict to store original scenarios_information (paths to files)

        break
    else:
        if run_name == 'break':
            break
        else:
            print(run_name + ' does not exist at: ' + cache_dir_path)

short = False

#%% Run oemof model for every scenario
# Get PV resource data -> same for all scenarios
pv_data = pd.read_csv("pv_resource_model/pv_resource_data/1min_res_pv_mhv.csv",
                      index_col=0, parse_dates=True)


# Get household baseload -> same for all scenarios
household_baseload = pd.read_csv("model_input_data/oemof_model_input/1min_household_load_profile.csv",
                                 index_col=0,
                                 parse_dates=True)


for scenario_id, scenario_data in scenarios.items():
    if scenario_id != 'b':
        continue

    print('Run oemof model for scenario ' + scenario_id)

    # Read this scenario's oemof input data
    oemof_input = InputData()
    oemof_input.get_all_tables("./model_input_data/" + scenario_data['oemof_input_file_name'])

    # Read this scenario's pue load profiles
    pue_load_profiles = pd.read_csv(
        cache_dir_path + 'load_profile_scenario_' + str(scenario_id) + '.csv',  # path to RAMP modelled load profiles
        index_col=0,
        parse_dates=True)

    if scenario_id == 'a':
        peak_power_a = pue_load_profiles['peak_power_profile']

    if scenario_id == 'c':
        pue_load_profiles['peak_power_profile'] = peak_power_a

    if short:
        timeframe = pd.date_range("2018-01-01", periods=short * 24 * 60, freq="Min")
        pue_load_profiles = pue_load_profiles.loc[timeframe]

    # Initialise instance of OemofModel with scenario's input data
    mg_model = OemofModel(
        pue_load_profile=pue_load_profiles['total'],
        household_baseload=household_baseload['household_load'],
        peak_power_profile=pue_load_profiles['peak_power_profile'],
        system_data=oemof_input.tables_dict,
        pv_gen_ts=pv_data['north_20'],
        freq='1h',
        peak_power_model=True,
        pue_load_exists=True,
        household_baseload_exists=True,
        pv_east_west_exists=False,
        pv_east_ts=pv_data['east_20'],
        pv_west_ts=pv_data['west_20']
    )
    mg_model.build_energysystem()  # Create energysystem's components and build system

    print('solve model')
    mg_model.om.solve(solver='cbc')  # Solve the model

    # Process and save oemof results
    print('process results')
    mg_model.results_oemof = solph.processing.results(mg_model.om)

    # Add mg_model to scenario_data dict
    scenario_data['mg_model'] = mg_model

#%%
# Pickle dict of scenarios with oemof results
#with open(cache_dir_path + 'model_results.pickle', 'wb') as file:
#    print('Pickle and dump results')
#    pickle.dump(scenarios, file, protocol=pickle.HIGHEST_PROTOCOL)

# %% Run results analysis
# Dict to collect all scenarios' system KPIs
scenarios_system_kpis = {}
scenarios_system_capacities = {}
for scenario_id, scenario_data in scenarios.items():
    if scenario_id != 'b':
        continue
    # Extract and process oemof results
    scenario_data['mg_model'].extract_results(scenario_data['mg_model'].results_oemof)

    # Copy this scenario's system results in systems_kpis dict
    scenarios_system_kpis[scenario_id] = scenario_data['mg_model'].results_system
    scenarios_system_capacities[scenario_id] = scenario_data['mg_model'].results_components_capacities.loc['capacity_total']


scenarios_system_kpis = pd.DataFrame(scenarios_system_kpis)
scenarios_system_capacities = pd.DataFrame(scenarios_system_capacities)

# Save dfs as xlsx
scenarios_system_results = pd.concat([scenarios_system_capacities, scenarios_system_kpis])

scenarios_system_results.to_excel(cache_dir_path + '/scenarios_system_results.xlsx')

#%%

fig = make_subplots(1,1)
fig =  plotting.plotly_df(fig, mg_model.results_ac_flows[['pv_l - bus_ac_l', 'unsupplied_pue_demand_l - bus_ac_pue_l']], legend=['PV generation', 'unsupplied PUE load'])
fig.update_layout(
    yaxis_title='P [kW]',
    font=dict(
            size=12
        )
)
fig.show()