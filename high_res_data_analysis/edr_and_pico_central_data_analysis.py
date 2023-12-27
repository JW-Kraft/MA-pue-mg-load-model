#%%
import pandas as pd
import numpy as np

from high_res_data_analysis import read_high_res_data
import plotting
from plotly.subplots import make_subplots

#%% Read original EDR and Pico data
edr_data = read_high_res_data.read_edr_data('./high_res_data_analysis/EDR/2023-09-29 10.00-13.00 local time/', 2)
pico_raw_data, pico_data = read_high_res_data.read_pico_data('./high_res_data_analysis/Pico/2023-09-29_mhv_pv_output.csv',
                                                             agg_dur='20ms')

# Shift offset between EDR and Pico data
pico_raw_data = pico_raw_data.shift(freq='2680ms')
pico_data = pico_data.shift(freq='2680ms')

#%%
# Save processed 20ms data as CSV
pico_raw_data.to_csv('./high_res_data_analysis/Pico/2023-09-29_mhv_pv_output_processed.csv')
pico_data.to_csv('./high_res_data_analysis/Pico/2023-09-29_mhv_pv_output_processed_20ms.csv')


#%% Read processes EDR and Pico data from CSV
edr_data = pd.read_csv('./high_res_data_analysis/EDR/2023-09-29 10.00-13.00 local time combined_v02.csv',
                      header=[0, 1], index_col=0, parse_dates=[0])

pico_data = pd.read_csv('./high_res_data_analysis/Pico/2023-09-29_mhv_pv_output_processed_20ms.csv',
                        header=[0, 1], index_col=0, parse_dates=[0])

pico_raw_data = pd.read_csv('./high_res_data_analysis/Pico/2023-09-29_mhv_pv_output_processed.csv',
                            header=[0, 1], index_col=0, parse_dates=[0])

#%% Adjust to correct local time
edr_data = edr_data.shift(freq='3h')
pico_data = pico_data.shift(freq='3h')

#%% Calculate current delivered by battery (Sunny Island) -> = difference of grid current and PV current
bat_data = edr_data['L3']['I_eff'] - pico_data['L3']['I_eff']
bat_data =pd.DataFrame(bat_data)

#%% Plot EDR and Pico Data
fig = make_subplots(3,1, shared_xaxes=True, vertical_spacing=0.03)


fig = plotting.plotly_high_res_df(fig, pico_data['L3'][['I_eff']], prefix='L3 PV ', subplot_row=2)
fig = plotting.plotly_high_res_df(fig, bat_data, prefix='L3 Bat ', subplot_row=2)
fig = plotting.plotly_high_res_df(fig, edr_data['L3'][['I_eff']], prefix='L3 grid total ', subplot_row=2)

fig = plotting.plotly_high_res_df(fig, edr_data['L3'][['freq']], subplot_row=3, legend=['frequency'])

fig = plotting.plotly_df(fig, (edr_data['L1'][['S']]+edr_data['L2'][['S']]+
                               edr_data['L3'][['S']])/1000,
                         legend=['S grid total'] ,subplot_row=1)

fig = plotting.plotly_df(fig, (edr_data['L1'][['P']]+edr_data['L2'][['P']]+
                               edr_data['L3'][['P']])/1000,
                         legend=['P grid total'] ,subplot_row=1)

#%%
# Format figure
fig.update_yaxes(title_text="P [kW], S [kVA]", row = 1, col = 1)
fig.update_yaxes(title_text="I_eff [A]", row = 2, col = 1)
fig.update_yaxes(title_text="f [Hz]", row = 3, col = 1)

fig.update_layout(
    height=500,
margin=dict(l=0, r=0, t=20, b=0)
)


fig.show_dash(mode='external')

#%% quick



edr_data = read_high_res_data.read_edr_data('./high_res_data_analysis/EDR/2023-09-27 MHV 100ms/', current_corr_factor=2)

edr_data = edr_data.shift(freq='3h')

fig = make_subplots(1,1)
high_res_p = (edr_data['L1'][['P']]+edr_data['L2'][['P']]+edr_data['L3'][['P']])/1000

fig = plotting.plotly_high_res_df(fig, high_res_p, legend=['P high res'] ,subplot_row=1)
fig = plotting.plotly_high_res_df(fig, high_res_p.resample('15min').mean())
fig.show_dash(mode='external')
