#%%
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
#%%
scenarios_lp = {}
for scenario_id, scenario in scenarios.items():
# Read this scenario's pue load profiles
    scenarios_lp[scenario_id] = pd.read_csv(
        cache_dir_path + 'load_profile_scenario_' + str(scenario_id) + '.csv',  # path to RAMP modelled load profiles
        index_col=0,
        parse_dates=True)

#%% Plotting

fig = make_subplots(1,1)

fig = plotting.plotly_high_res_df(fig, scenario)
fig. show_dash(mode='external')

#%% prepare data
col_new = ['1_comb_husking_mill', '1_broyeur', '2_comb_husking_mill',
 '2_broyeur', '3_huller', '3_polisher', '3_broyeur', '4_broyeur', '5_comb_husking_mill', '6_comb_husking_mill', '7_industrial_husking_mill', 'total', 'peak_power_profile']


scenario.columns = col_new

#%%
col_sel = ['1_comb_husking_mill', '1_broyeur', '2_comb_husking_mill',
 '2_broyeur', '3_huller', '3_polisher', '3_broyeur', '4_broyeur', '5_comb_husking_mill', '6_comb_husking_mill']
df = scenario[col_sel]

df2 = pd.DataFrame(index=df.index)
df2['Total load'] = df.sum(axis='columns')
df2['Total load, 1h_res'] = df2['Total load'].resample('1h').mean()

df3 = scenario[['peak_power_profile']]
df2['peak_power'] = df2['Total load'] + scenario['peak_power_profile']
#%%
fig = make_subplots(1,1)
fig = plotting.plotly_high_res_df(fig, df2[['peak_power', 'Total load', 'Total load, 1h_res']], legend=['peak_power', '1min_rs', '1h_res'], linestyle={'shape': 'vh'})
fig = plotting.plotly_high_res_df(fig, df3, linestyle={'shape': 'vh'}, opacity=0.5)
fig.show_dash(mode='external')

fig.update_layout(
    font=dict(
                size=12
            ),
        yaxis_title="P [kW]",
        margin=dict(l=0, r=0, t=20, b=0),
        height=250,

)

#%%
load_profiles = pd.DataFrame()
for scenario_id, lp in scenarios_lp.items():
    load_profiles[scenario_id] = lp['total']

#%%
# Calculate average weekly load profile
load_profiles['week'] = load_profiles.index.strftime('%a - %H:%M')
avg_week = load_profiles.groupby(load_profiles.index.strftime('%a - %H:%M'), sort=False).mean()

fig2 = make_subplots(2, 1, shared_xaxes=True, vertical_spacing=0.02)
fig_2 = plotting.plotly_df(fig2, avg_week[['a', 'b', 'c', 'd']], legend=['A', 'B', 'C', 'D'] ,subplot_row=1)
fig_2 = plotting.plotly_df(fig2, avg_week[['a2', 'b2', 'c2', 'd2']], legend=['A_no_lim', 'B_no_lim', 'C_no_lim', 'D_no_lim'], subplot_row=2)

fig2.update_layout(
    font=dict(
                size=12
            ),
        yaxis_title="P [kW]",
        margin=dict(l=0, r=0, t=20, b=0),
        height=500,

)

fig_2.show()
