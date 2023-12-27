#%%
import pandas as pd
import numpy as np
import os

import plotly.express as px
import plotly.io as pio
from plotly.subplots import make_subplots
import plotly.express.colors as colors
import plotly.graph_objects as go

import plotting

pd.options.plotting.backend = "plotly"  # make plotly standard pandas plotting.py engine
pio.renderers.default = "browser"   # show plots in browser window

#%% Read solar data from CSV
low_res_solar_data = pd.read_csv('./pv_resource_model/pv_resource_data/30min_res_pv_north20_mhv.csv',
                                 index_col=[0],
                                 parse_dates=[0]
                                 )

high_res_solar_data = pd.read_csv('./pv_resource_model/pv_resource_data/1min_res_pv_north20_mhv.csv',
                                  index_col=[0],
                                  parse_dates=[0]
                                  )

high_res_solar_data_interpolated = pd.read_csv('./pv_resource_model/pv_resource_data/1min_res_interpolated_pv_north20_mhv.csv',
                                               index_col=[0],
                                               parse_dates=[0]
                                               )
#%%
kwp = 123  # installed kWp PV
low_res_solar_data = low_res_solar_data * kwp
high_res_solar_data_interpolated = high_res_solar_data_interpolated * kwp
high_res_solar_data = high_res_solar_data * kwp

#%%
fig = make_subplots(1,1)
plotting.plotly_df(fig, low_res_solar_data[['north_20', 'east_20', 'west_20']])
fig.show()

#%%
fig = make_subplots(1,1)
fig = plotting.plotly_high_res_df(fig, high_res_solar_data)
fig = plotting.plotly_high_res_df(fig, high_res_solar_data_interpolated)
fig.show_dash(mode='external')

#%% Plot monthly energy yield
daily_solar_energy = low_res_solar_data[['north_20']].resample('D').sum()/2  # divide by two because of 30min data resolution
monthly_solar_energy = low_res_solar_data[['north_20']].resample('M').sum()/2/1000

# Dirty fix for x tick aligment
monthly_solar_energy.index = monthly_solar_energy.index.shift(periods=-15, freq='D')

fig = make_subplots(specs=[[{"secondary_y": True}]])

thickness = 0.3

fig.add_bar(x=monthly_solar_energy.index, y=[thickness]*len(monthly_solar_energy.index),
            secondary_y=True, name='Monthly PV yield', base=monthly_solar_energy['north_20']-thickness)
fig.add_bar(x=daily_solar_energy.index, y=daily_solar_energy['north_20'], secondary_y=False, name='Daily PV yield')

fig.update_yaxes(rangemode="tozero")

fig.update_layout(
    yaxis_title="Daily PV yield [kWh]",
    yaxis2_title="Monthly PV yield [MWh]",
    height=300,
    margin=dict(l=0, r=0, t=20, b=0)
)

fig.show()


fig.write_image('./figures/pv_yield.png', scale=3)

#%% Plot solar heatmap

fig = plotting.plot_timeseries_heatmaps(high_res_solar_data, 'north_20', zmin=0, zmax=1, wide=True)
fig.update_layout(title='kW/kWp - North 20° tilt')
fig['layout']['yaxis']['autorange'] = "reversed"
fig.show()

#%% Plot "load duration curve" of daily energy yield
daily_solar_yield = low_res_solar_data.resample('D').sum()/2

ldc_solar = daily_solar_yield.sort_values('north_20', ascending=False)
ldc_solar.reset_index(inplace=True, drop=True)

fig = ldc_solar.plot()
fig.update_layout(yaxis_title='kWh/kWp')
fig.show()

#%% Verify with NinjaPV data
ninja_east = pd.read_csv('./pv_resource_model/pv_resource_data/MHV_ninja_az_270.csv', index_col=[0], parse_dates=[0])
ninja_west = pd.read_csv('./pv_resource_model/pv_resource_data/MHV_ninja_az_90.csv', index_col=[0], parse_dates=[0])

fig = make_subplots(1,1)
fig = plotting.plotly_df(fig, ninja_east[['electricity']], legend=['east - az 270'])
fig = plotting.plotly_df(fig, ninja_west[['electricity']], legend=['west - az 90'])
fig.show()