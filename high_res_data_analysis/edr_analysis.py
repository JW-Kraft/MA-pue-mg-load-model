#%%
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error

import plotting
from high_res_data_analysis import read_high_res_data
from plotly.subplots import make_subplots
import plotly.express as px
import tqdm

#%%
# Read EDR 100MS CSV data
edr_data = read_high_res_data.read_edr_data('./high_res_data_analysis/EDR/MHV_1s_complete/',
                                            current_corr_factor=2)

#%% Only keep power data
edr_1s = edr_data['L1'][['P', 'S', 'Q', 'I_eff', 'I_thd', 'freq']]

for phase in ['L2', 'L3']:
    edr_1s = edr_1s + edr_data[phase][['P', 'S', 'Q', 'I_eff']]

edr_1s = edr_1s.shift(freq='3h')

#%% Save in one CSV
edr_1s.to_csv('./high_res_data_analysis/EDR/2023 MHV 1s complete.csv')


#%% Plot
fig = make_subplots(3, 1, shared_xaxes=True, vertical_spacing=0.02)
fig = plotting.plotly_high_res_df(fig, edr_1s['L1'][['I_eff']], subplot_row=1)
fig = plotting.plotly_high_res_df(fig, edr_1s['L1'][['U_eff']], subplot_row=2)
fig = plotting.plotly_high_res_df(fig, (edr_1s['L1'][['S']] + edr_1s['L2'][['S']] + edr_1s['L3'][['S']])/1000,
                                  subplot_row=3)


fig.update_yaxes(title_text="I_eff [A]", row = 1, col = 1)
fig.update_yaxes(title_text="U_eff [V]", row = 2, col = 1)
fig.update_yaxes(title_text="S [kVA]", row = 3, col = 1)

fig.update_layout(
    height=600
)


fig.show_dash(mode='external')

#%% load modeled load profile
scen_a = pd.read_csv('./data_cache/final_8_v03/load_profile_scenario_a.csv', index_col=0, parse_dates=[0])
scen_a = scen_a[['total', 'peak_power_profile']]

df = pd.read_csv('./model_input_data/oemof_model_input/1min_household_load_profile.csv', index_col=0, parse_dates=[0])
scen_a['household'] = df['household_load']

idx = pd.date_range('2023-09-25 0:00', '2023-10-24 23:59', freq='1min')

scen_a = scen_a.head(len(idx))
scen_a.index = idx

#%% Add household baseload to modelled load profile
scen_a['Total modeled'] = scen_a['household'] + scen_a['total'] + 1.2

# EDR data to kW
edr_1s = pd.read_csv('./high_res_data_analysis/EDR/2023 MHV 1s complete.csv', index_col=0, parse_dates=[0])/1000

# Cut all timeseries to same length
start = pd.Timestamp('2023-09-27 0:00')
end = pd.Timestamp('2023-09-29 23:59')

edr_1s = edr_1s[start:end]
scen_a = scen_a[start:end]

#%%
# Resample profiles to 1-h resolution -> meand and std
edr_1h = edr_1s.resample('1h').mean()
edr_1h_std = edr_1s.resample('1h').std()
scen_a_1h = scen_a.resample('1h').mean()#.iloc[8:]
scen_a_1h_std = scen_a.resample('1h').std()#.iloc[8:]

# Calculate MSE
mse = pd.DataFrame(index=edr_1h.index)
mse['MSE_1h_avg'] = mean_absolute_percentage_error(edr_1h['P'], scen_a_1h['Total modeled'])
mse['MSE_std_avg'] = mean_absolute_percentage_error(edr_1h_std['P'], scen_a_1h_std['Total modeled'])

#%% Plot
fig = make_subplots(3, 1, shared_xaxes=True, vertical_spacing=0.02)
fig = plotting.plotly_high_res_df(fig, edr_1s[['P']].resample('1min').mean(), legend=['measured'])
fig = plotting.plotly_high_res_df(fig, scen_a[['Total modeled']], legend=['modeled'])

fig = plotting.plotly_high_res_df(fig, edr_1h[['P']], subplot_row=2, legend=['measured 1h avg'])
fig = plotting.plotly_high_res_df(fig, edr_1h_std[['P']], subplot_row=2, legend=['measured 1h std'])
fig = plotting.plotly_high_res_df(fig, scen_a_1h[['Total modeled']], subplot_row=2, legend=['modeled 1h avg'])
fig = plotting.plotly_high_res_df(fig, scen_a_1h_std[['Total modeled']], subplot_row=2, legend=['modeled 1h std'])

fig = plotting.plotly_high_res_df(fig, mse, subplot_row=3)



fig.update_layout(
    height=600,
    yaxis_title="P [kW]",
    font=dict(
                size=12
            )
)


fig.show_dash(mode='external')

#%%
scen_profiles = {}
for scenario in ['a', 'b', 'c', 'd', 'a2', 'b2', 'c2', 'd2']:
    scen_profiles[scenario] = pd.read_csv('./data_cache/final_8/load_profile_scenario_'+ scenario +'.csv', index_col=0, parse_dates=[0])[['total', 'peak_power_profile']]

#%%
fig = make_subplots(1,1)
scen_cap = ['A', 'B', 'C', 'D']
i = 0
for scen, in ['a', 'b', 'c', 'd']:
    fig = plotting.plotly_high_res_df(fig, scen_profiles[scen][['peak_power_profile']], legend=[scen_cap[i]])
    i = i+1

fig.update_layout(
    height=400,
    yaxis_title="S [kVA]",
    font=dict(
                size=14
            )
)

fig.show_dash(mode='external')

#%%
scen_peak_nr = pd.DataFrame()
for scen, profiles in scen_profiles.items():
    scen_peak_nr[scen] = profiles.groupby('peak_power_profile').size()

scen_peak_nr = scen_peak_nr.iloc[1:]  # Remove counted zeros
#%%
# Create a histogram of the time series data
fig = make_subplots(1,1)
fig = plotting.plotly_df(fig, scen_peak_nr.iloc[3:])
fig.show()