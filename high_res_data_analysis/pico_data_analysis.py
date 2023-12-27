import pandas as pd
from pandas.tseries.frequencies import to_offset
import numpy as np

import plotly.io as pio

from high_res_data_analysis import read_high_res_data
import plotting
from plotly.subplots import make_subplots

pd.options.plotting.backend = "plotly"  # make plotly standard pandas plotting.py engine
pio.renderers.default = "browser"   # show plots in browser window


#%%
pico_raw_data, pico_data = read_high_res_data.read_pico_data(
    './high_res_data_analysis/Pico/2023-09-28_mhv_ms_bruno_v02.csv', agg_dur='20ms')

#%% Read EDR high-res data
edr_data = read_high_res_data.read_edr_data('./high_res_data_analysis/EDR/2023-10-19 MHV 100ms/', 2)

#%%
mean_500ms = pico_data.resample('300ms', label='right').mean()
mean_500ms = mean_500ms.shift(freq='2000ms')


for phase in ['L1', 'L2', 'L3']:
    mean_500ms.loc[:, (phase, 'U_delta')] = edr_data[phase]['U_eff'] - mean_500ms[phase]['U_eff']
    mean_500ms.loc[:, (phase, 'S_line_loss')] = mean_500ms[phase]['I_eff'] * mean_500ms[phase]['U_delta']

load_colors = {
    'L1': '#EAD53C',
    'L2': '#EB4A00',
    'L3': '#EB7F17',
    'S': '#E01000',
    'P': '#3E8CE0'
}

grid_colors = {
    'L1': '#A400EB',
    'L2': '#008DF0',
    'L3': '#00EF67',
    'S': '#7424E1',
    'P': '#3B8B4F'
}

freq_color = '#E038A1'

fig = make_subplots(4,1, shared_xaxes=True, vertical_spacing=0.03)

for phase in ['L1', 'L2', 'L3']:

    # Plot main grid currents
    fig = plotting.plotly_df(fig, edr_data[phase][['I_eff']].loc[mean_500ms.index], subplot_row=1, legend=[phase + ' grid'],
                             legendgroup='grid', linestyle=dict(color=grid_colors[phase]), opacity=0.7)

    # Plot load current
    fig = plotting.plotly_df(fig, mean_500ms[phase][['I_eff']], subplot_row=1, legend=[phase + ' ASM'],
                             legendgroup='load', linestyle=dict(color=load_colors[phase]), opacity=0.7)


    # Plot load voltage
    fig = plotting.plotly_df(fig, mean_500ms[phase][['U_eff']], subplot_row=2, legend=[phase + ' ASM'],
                                      legendgroup='load', linestyle=dict(color=load_colors[phase]),
                                      showlegend=False, opacity=0.7)

    # Plot main grid voltage
    fig = plotting.plotly_df(fig, edr_data[phase][['U_eff']].loc[mean_500ms.index], subplot_row=2, legend=[phase + ' grid'],
                             legendgroup='grid', linestyle=dict(color=grid_colors[phase]),
                             showlegend=False, opacity=0.7)



# Plot load S and P
fig = plotting.plotly_df(fig, (mean_500ms['L1'][['P']]+mean_500ms['L2'][['P']]+mean_500ms['L3'][['P']])/1000,
                                  subplot_row=3,
                                  legend=['P ASM total'],
                         linestyle=dict(color=load_colors['P'])
                                  )
fig = plotting.plotly_df(fig, (mean_500ms['L1'][['S']]+mean_500ms['L2'][['S']]+mean_500ms['L3'][['S']])/1000,
                         legend=['S ASM total'] ,subplot_row=3, linestyle=dict(color=load_colors['S']))

# Plot line losses (S)
fig = plotting.plotly_df(fig, (mean_500ms['L1'][['S_line_loss']]+mean_500ms['L2'][['S_line_loss']]+mean_500ms['L3'][['S_line_loss']])/1000,
                         legend=['S line losses'] ,subplot_row=3, linestyle=dict(color=load_colors['S']))

# Plot grid S and P
fig = plotting.plotly_df(fig, (edr_data['L1'][['P']]+edr_data['L2'][['P']]+
                               edr_data['L3'][['P']]).loc[mean_500ms.index]/1000,
                         legend=['P grid total'] ,subplot_row=3, linestyle=dict(color=grid_colors['P']))

fig = plotting.plotly_df(fig, (edr_data['L1'][['S']]+edr_data['L2'][['S']]+
                               edr_data['L3'][['S']]).loc[mean_500ms.index]/1000,
                         legend=['S grid total'] ,subplot_row=3, linestyle=dict(color=grid_colors['S']))



fig = plotting.plotly_df(fig, edr_data['L1'][['freq']].loc[mean_500ms.index], legend=['frequency'], subplot_row=4,
                         linestyle=dict(color=freq_color))

fig.update_yaxes(title_text="I [A]", row=1, col=1)
fig.update_yaxes(title_text="U [V]", row=2, col=1)
fig.update_yaxes(title_text="P [kW], S [kVA]", row=3, col=1)
fig.update_yaxes(title_text="f [Hz]", row=4, col=1)

fig.update_layout(
    height=600,
    margin=dict(l=0, r=0, t=20, b=0),
    #title='Husking Mill M. Victor - 18.5 kW - Soft starter: U_start=225V, t_ramp5s',
)

fig.show()

#%%
fig.write_image('./figures/husking_mill_with_load.png', scale=3)

#%%
df_res = mean_500ms.index.freq.delta.total_seconds()/3600
print('Average power [kW]: '+ str((mean_500ms['L1'][['P']]+mean_500ms['L2'][['P']]+mean_500ms['L3'][['P']]).mean()))
print('Energy used [kWh]: ' + str((mean_500ms['L1'][['P']]+mean_500ms['L2'][['P']]+mean_500ms['L3'][['P']]).sum()*df_res))

#%% Plot Soft starter runs

mean_500ms = pico_data.resample('300ms', label='right').mean()
mean_500ms = mean_500ms.shift(freq='2000ms')


load_colors = {
    'L1': '#EAD53C',
    'L2': '#EB4A00',
    'L3': '#EB7F17',
    'S': '#E01000',
    'P': '#3E8CE0'
}

grid_colors = {
    'L1': '#A400EB',
    'L2': '#008DF0',
    'L3': '#00EF67',
    'S': '#7424E1',
    'P': '#3B8B4F'
}

freq_color = '#E038A1'

fig = make_subplots(3,1, shared_xaxes=True, vertical_spacing=0.03)

for phase in ['L1', 'L2', 'L3']:

    # Plot load current
    fig = plotting.plotly_df(fig, mean_500ms[phase][['I_eff']], subplot_row=1, legend=[phase + ' ASM'],
                             legendgroup='load', linestyle=dict(color=load_colors[phase]), opacity=0.7)


    # Plot load voltage
    fig = plotting.plotly_df(fig, mean_500ms[phase][['U_eff']], subplot_row=2, legend=[phase + ' ASM'],
                                      legendgroup='load', linestyle=dict(color=load_colors[phase]),
                                      showlegend=False, opacity=0.7)



# Plot load S and P
fig = plotting.plotly_df(fig, (mean_500ms['L1'][['P']]+mean_500ms['L2'][['P']]+mean_500ms['L3'][['P']])/1000,
                                  subplot_row=3,
                                  legend=['P ASM total'],
                         linestyle=dict(color=load_colors['P'])
                                  )
fig = plotting.plotly_df(fig, (mean_500ms['L1'][['S']]+mean_500ms['L2'][['S']]+mean_500ms['L3'][['S']])/1000,
                         legend=['S ASM total'] ,subplot_row=3, linestyle=dict(color=load_colors['S']))


fig.update_yaxes(title_text="I [A]", row=1, col=1)
fig.update_yaxes(title_text="U [V]", row=2, col=1)
fig.update_yaxes(title_text="P [kW], S [kVA]", row=3, col=1)

fig.update_layout(
    height=650,
    margin=dict(l=0, r=0, t=20, b=0)

)
    #title='Husking Mill M. Victor - 18.5 kW - Soft starter: U_start=225V, t_ramp5s',

#%%
fig.write_image('./figures/husking_mill_softstarter.png', scale=3)