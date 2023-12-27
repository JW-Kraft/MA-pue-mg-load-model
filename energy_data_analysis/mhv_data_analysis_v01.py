import pandas as pd
import numpy as np

import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots


import plotting

pd.options.plotting.backend = "plotly"  # make plotly standard pandas plotting.py engine
pio.renderers.default = "browser"   # show plots in browser window

#%% Data from AGT Mahavelona MG

# Husking mill smart meter data (15 min resolution)
mdg_mill_1_df = pd.read_csv('./energy_data_analysis/2023-09 Mahavelone Smartmeter Data only PUE/T5_MHV-0133.csv',
                            index_col=0, parse_dates=[0])
# Seems to have negative 3 hour shift to local time
# Sparkmeter possibly adds UTC (or computer local time?) as timestamps in downloaded CSV files
# -> data shows load three hours earlier than in local time

mdg_mill_1_df = mdg_mill_1_df[['voltage_min',
                   'voltage_max',
                   'voltage_avg',
                   'current_min',
                   'current_max',
                   'current_avg',
                   'true_power_avg',
                   'power_factor_avg']]
# Fix timeshift
mdg_mill_1_df = mdg_mill_1_df.shift(freq='3H')

# Fix timeshift 2: 15min shift back to match 1min gen data -> not sure in which direction aggregation is computed

#%% PV and battery data (1 min resolution)
# Full day: 2023-07-31
mdg_pv_P_active_df = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-07-31 PV Active power-data.csv',
                                 index_col=0,
                                 parse_dates=[0]
                                 )
mdg_battery_P_active = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-07-31 battery active power-data.csv',
                                   index_col=0,
                                   parse_dates=[0]
                                   )

mdg_system_P = pd.DataFrame(index=mdg_pv_P_active_df.index)
mdg_system_P['P_active_battery'] = mdg_battery_P_active.sum(axis='columns')

mdg_system_P['P_active_PV'] = mdg_pv_P_active_df.sum(axis='columns')

mdg_system_P['P_active_delivered'] = mdg_system_P.sum(axis='columns')

# Resample gen data to fit demand smart meter data temporal resolution
# Shift gen data 15min back ("to the right") -> seems to have offset
mdg_system_P_15min = mdg_system_P.resample('15Min').mean().shift(freq='15min')  # resample to 15 min

#%% Plots
# Plot mill_1 power and gen data

fig = make_subplots(1,1)

fig = plotting.plotly_df(fig, mdg_system_P_15min, linestyle={'shape': 'vh'}, prefix='15min_')
fig = plotting.plotly_df(fig, mdg_mill_1_df[['true_power_avg']], legend=['Rice_mill_1'], linestyle={'shape': 'vh'}, prefix='15min_')
fig = plotting.plotly_df(fig, mdg_system_P, linestyle={'shape': 'vh'}, opacity=0.4, prefix='1min_', mode='lines', markerstyle={'symbol': 'line-ew', 'line_width': 2})


fig.show()

#%%  Plot with dual y-axis

fig = go.Figure()

fig.add_trace(go.Scatter(x=mdg_mill_1_df.index, y=mdg_mill_1_df['true_power_avg'],
                         name="P husking mill",
                         yaxis='y',
                         opacity=0.6,
                         line=dict(shape='hvh')
                         ))

fig.add_trace(go.Scatter(x=mdg_system_P_15min.index, y=mdg_system_P_15min['P_active_delivered'],
                         name="P system",
                         yaxis="y",
                         opacity=0.6,
                         line=dict(shape='hvh')))
#fig.add_trace(go.Scatter(x=mdg_mill_1_df.index, y=mdg_mill_1_df['frequency'], name="Frequency", yaxis="y2", opacity=0.6))

# Create axis objects
fig.update_layout(xaxis=dict(domain=[0.3, 0.7]),
                  yaxis=dict(
                      title="P in W",
                      titlefont=dict(color="#1f77b4"),
                      tickfont=dict(color="#1f77b4")
                ),

                # create 2nd y axis
                yaxis2=dict(title="f in Hz", overlaying="y", anchor="x", side="right", position=0.15)
                  )
fig.update_layout(
    font=dict(
        size=18
    )
)

fig.show()


