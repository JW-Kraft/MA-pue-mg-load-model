#%%
import pandas as pd
import numpy as np
import os

import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express.colors as colors

import plotting

pd.options.plotting.backend = "plotly"  # make plotly standard pandas plotting.py engine
pio.renderers.default = "browser"   # show plots in browser window

#%% Plotly figure parameters

dpi = 300
dpi_per_cm = dpi/2.54

a4_full_width = 15*dpi_per_cm
a4_half_width = 7*dpi_per_cm

scale_a4_full_width = a4_full_width / (700 / dpi)
scale_a4_half_width = a4_half_width / (700 / dpi)

a4_full_height = int(25 * dpi_per_cm)  # 25 cm as in thesis template
a4_half_height = int(12.5 * dpi_per_cm)
a4_third_height = int(25/3 * dpi_per_cm)
a4_quarter_height = int(25/4 * dpi_per_cm)

#%%
# PV and battery data (1 min resolution)
# Read and combine segmented Grafana data
# 2023-08-14 to 2023-09-03
pv_P_act = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-08-14 to 2023-09-03/2023-08-14 PV_active_P 3_weeks.csv',
                       index_col=0,
                       parse_dates=[0]
                       )
pv_P_react = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-08-14 to 2023-09-03/2023-08-14 PV_reactive_P 3_weeks.csv',
                       index_col=0,
                       parse_dates=[0]
                       )

bat_P_act = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-08-14 to 2023-09-03/2023-08-14 bat_active_P 3_weeks.csv',
                       index_col=0,
                       parse_dates=[0]
                       )

bat_P_react = pd.read_csv('./energy_data_analysis//Mahavelona Gen System Data/2023-08-14 to 2023-09-03/2023-08-14 bat_reactive_P 3_weeks.csv',
                       index_col=0,
                       parse_dates=[0]
                       )

bat_SOC = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-08-14 to 2023-09-03/2023-08-14 bat_SOC 3_weeks.csv',
                       index_col=0,
                       parse_dates=[0]
                       )

# Add 2023-09-04 to 2023-09-09 and 2023-09-10 to 2023-09-17
pv_P_act = pd.concat([pv_P_act,
                     pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-09-04 to 2023-09-09/2023-09-04 PV_active_P 1_week.csv',
                       index_col=0,
                       parse_dates=[0]
                       ),
                      pd.read_csv(
                          './energy_data_analysis/Mahavelona Gen System Data/2023-09-10 to 2023-09-17/2023-09-10 active P 1_week.csv',
                          index_col=0,
                          parse_dates=[0]
                          )
                      ]
                     )

pv_P_react = pd.concat([pv_P_react,
                     pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-09-04 to 2023-09-09/2023-09-04 PV_reactive_P 1_week.csv',
                       index_col=0,
                       parse_dates=[0]
                       ),
                      pd.read_csv(
                          './energy_data_analysis/Mahavelona Gen System Data/2023-09-10 to 2023-09-17/2023-09-10 reactive P 1_week.csv',
                          index_col=0,
                          parse_dates=[0]
                          )
                      ]
                     )

bat_P_act = pd.concat([bat_P_act,
                     pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-09-04 to 2023-09-09/2023-09-04 battery_active_P 1_week.csv',
                       index_col=0,
                       parse_dates=[0]
                       ),
                      pd.read_csv(
                          './energy_data_analysis/Mahavelona Gen System Data/2023-09-10 to 2023-09-17/2023-09-10 bat_active_P 1_week.csv',
                          index_col=0,
                          parse_dates=[0]
                          )
                      ]
                     )

bat_P_react = pd.concat([bat_P_react,
                     pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-09-04 to 2023-09-09/2023-09-04 battery_reactive_P 1_week.csv',
                       index_col=0,
                       parse_dates=[0]
                       ),
                      pd.read_csv(
                          './energy_data_analysis/Mahavelona Gen System Data/2023-09-10 to 2023-09-17/2023-09-10 bat_reactive_P 1_week.csv',
                          index_col=0,
                          parse_dates=[0]
                          )
                      ]
                     )

mhv_bat_SOC = pd.concat([bat_SOC,
                     pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/2023-09-04 to 2023-09-09/2023-09-04 battery_SOC 1_week.csv',
                       index_col=0,
                       parse_dates=[0]
                       ),
                      pd.read_csv(
                          './energy_data_analysis/Mahavelona Gen System Data/2023-09-10 to 2023-09-17/2023-09-10 battery_SOC 1_week.csv',
                          index_col=0,
                          parse_dates=[0]
                          )
                      ]
                     )

# Combine in one df and sum phases
# --- Active power ---
mhv_P_act = pd.DataFrame(index=pv_P_act.index)
mhv_P_act['Bat_P_act'] = bat_P_act.sum(axis='columns')
mhv_P_act['PV_P_act'] = pv_P_act.sum(axis='columns')

# Calculate microgrid load from sum of PV power and battery power
mhv_P_act['Load_P_act'] = mhv_P_act.sum(axis='columns')

# Resample gen data to fit demand smart meter data temporal resolution
# Shift gen data 15min back ("to the right") -> seems to have offset
mhv_P_act_15min = mhv_P_act.resample('15Min').mean().shift(freq='15min')  # resample to 15 min


# --- Reactive power ---
mhv_P_react = pd.DataFrame(index=pv_P_react.index)
mhv_P_react['Bat_P_react'] = bat_P_react.sum(axis='columns')
mhv_P_react['PV_P_react'] = pv_P_react.sum(axis='columns')

# Calculate microgrid load from sum of PV power and battery power
mhv_P_react['Load_P_react'] = mhv_P_react.sum(axis='columns')

# Resample gen data to fit demand smart meter data temporal resolution
# Shift gen data 15min back ("to the right") -> seems to have offset
mhv_P_react_15min = mhv_P_react.resample('15Min').mean().shift(freq='15min')  # resample to 15 min

# --- Battery SOC ---
# rename column
mhv_bat_SOC.columns = ['Bat_SOC']
# turn percentage into float
mhv_bat_SOC['Bat_SOC'] = mhv_bat_SOC['Bat_SOC'].str.rstrip('%').astype('float')/100

# Resample gen data to fit demand smart meter data temporal resolution
# Shift gen data 15min back ("to the right") -> seems to have offset
mhv_bat_SOC_15min = mhv_bat_SOC.resample('15Min').mean().shift(freq='15min')  # resample to 15 min

# Get solar radiation data for site
mhv_solar_data = pd.DataFrame()
mhv_solar_data['north_20'] = pd.read_csv(
    './energy_data_analysis/Mahavelona Gen System Data/solar_data/1min_res_pv_mhv_north_20.csv',
    index_col=0,
    parse_dates=[0])[['HighRes']]

mhv_pv_power = pd.DataFrame()
mhv_pv_power['north_20'] = mhv_solar_data['north_20'] * 115000

solar_slice = mhv_solar_data['north_20'].iloc[0 : len(mhv_P_act.index)]
solar_slice.index = mhv_P_act.index
mhv_P_act['PV_potential'] = solar_slice * 112  # 115 kWP in Mahavelona

#%% Read smartmeter load data

dir_path = './energy_data_analysis/2023-09 Mahavelona Smartmeter Data complete/'
dir = os.fsencode(dir_path)

mhv_customer_load_dict = {}
mhv_pue_load_dict = {}
mhv_all_except_T5_dict = {}
mhv_all_dict = {
    'T5': {},
    'T4': {},
    'T3': {},
    'T2': {}
}

for file in os.listdir(dir):
    filename = os.fsdecode(file)
    customer_id = filename[:-4]  # customer_id is filename without first three characters and .csv ending

    # read csv file in df
    df = pd.read_csv(dir_path + filename, index_col=0, parse_dates=True, usecols=['datetime', 'true_power_avg'])
    df = df.shift(freq='3H')

    # Make 2-level dict with all customers
    mhv_all_dict[filename[0:2]][customer_id] = df

    if filename[0:2] == 'T5' or filename[0:2] == 'T4':  # If PUE load (T5=husking mill, T4=welder)
        # save df in dict of customer load data
        mhv_pue_load_dict[customer_id] = df
    else:
        mhv_customer_load_dict[customer_id] = df

    if filename[0:2] != 'T5':
        mhv_all_except_T5_dict[customer_id] = df


#%% combine load data in one df
t2_load_power = pd.DataFrame()
t3_load_power = pd.DataFrame()
for key, customer in mhv_all_dict['T2'].items():
    t2_load_power[key] = customer[['true_power_avg']]

for key, customer in mhv_all_dict['T3'].items():
    t3_load_power[key] = customer[['true_power_avg']]

#%% Sum total consumer smartmeter data

pue_load_power = pd.DataFrame()
for key, customer in mhv_pue_load_dict.items():
    pue_load_power[key] = customer[['true_power_avg']]

t2_load_power['t2_total_power'] = t2_load_power.sum(axis='columns')
t3_load_power['t3_total_power'] = t3_load_power.sum(axis='columns')
pue_load_power['pue_total_power'] = pue_load_power.sum(axis='columns')


total_load_power = t2_load_power[['t2_total_power']] + t3_load_power[['t3_total_power']]
total_load_power['pue_total_power'] = pue_load_power['pue_total_power']

total_load_power['total_power'] = total_load_power.sum(axis='columns')

#%% --- Plot mhv load data: total, household and pue combined
fig = make_subplots(1,1, shared_xaxes=True)

fig.layout['xaxis_tickformat'] = '%H:%M - %a %d %b %Y'

fig = plotting.plotly_df(fig, mhv_P_act, subplot_row=1, linestyle={'shape': 'vh'})
fig = plotting.plotly_df(fig, total_load_power, subplot_row=1, linestyle={'shape': 'vh'})

fig.update_layout(
    font=dict(
        size=18
    )
)

fig.show()

#%% Plot PUE load development
pue_summed_load = pue_load_power[['T5_MHV-0133']]
pue_summed_load['T4'] = pue_load_power.drop(columns=['T5_MHV-0133', 'pue_total_power']).sum(axis='columns')

pue_summed_load.rename(columns={'T5_MHV-0133': 'T5'}, inplace=True)

pue_summed_load['T4_avg'] = pue_summed_load['T4'].rolling('7D', center=True).mean()
pue_summed_load['T5_avg'] = pue_summed_load['T5'].rolling('7D', center=True).mean()

fig = make_subplots(1, 1)
fig = plotting.plotly_df(fig, pue_summed_load[['T5', 'T4']], opacity=0.95, legend=['T4', 'T5'], color_palette=colors.qualitative.Pastel1)
fig = plotting.plotly_df(fig, pue_summed_load[['T5_avg', 'T4_avg']], opacity=1, color_palette=colors.qualitative.Vivid)

fig.show()

#%% Plot T2-T4 load development
household_load = pd.DataFrame()
household_load['T2'] = t2_load_power['t2_total_power']
household_load['T3'] = t3_load_power['t3_total_power']
household_load['T4'] = pue_load_power.drop(columns=['T5_MHV-0133', 'pue_total_power']).sum(axis='columns')

household_load_avg = pd.DataFrame()
household_load_avg['T2 rolling average'] = household_load['T2'].rolling('7D', center=True).mean()
household_load_avg['T3 rolling average'] = household_load['T3'].rolling('7D', center=True).mean()
household_load_avg['T4 rolling average'] = household_load['T4'].rolling('7D', center=True).mean()

fig = make_subplots(1, 1)
fig = plotting.plotly_df(fig, household_load[['T2', 'T3', 'T4']]/1000, opacity=0.95, color_palette=colors.qualitative.Pastel1)
fig = plotting.plotly_df(fig, household_load_avg/1000, opacity=1, color_palette=colors.qualitative.Vivid)

fig.update_layout(
    font=dict(
            size=12
        ),
    yaxis_title="P [kW]",
    margin=dict(l=0, r=0, t=20, b=0),
    height=300,
)

fig.show()

fig.write_image('./figures/avg_load.png', scale=3)
#%%
avg_week = pd.DataFrame()  # Calculate average week for PUE and household loads

# Get weekday name instead of number for plot
pue_load_power['weekday'] = pue_load_power.index.strftime('%a - %H:%M')
avg_week['index'] = pue_load_power['weekday'].groupby(pue_load_power.index.strftime('%u - %H:%M')).first()

avg_week['PUE'] = pue_load_power['pue_total_power'].groupby(pue_load_power.index.strftime('%u - %H:%M')).mean()
avg_week['T5'] = pue_load_power['T5_MHV-0133'].groupby(pue_load_power.index.strftime('%u - %H:%M')).mean()
avg_week['daily average'] = avg_week['T5'].groupby(avg_week['T5'].index.strftime('%u - %H:%M'))

avg_week['T4'] = pue_load_power.drop(columns=['T5_MHV-0133', 'pue_total_power']).sum(axis='columns').groupby(pue_load_power.index.strftime('%u - %H:%M')).mean()

avg_week['T2'] = t2_load_power['t2_total_power'].groupby(t2_load_power.index.strftime('%u - %H:%M')).mean()
avg_week['T3'] = t3_load_power['t3_total_power'].groupby(t3_load_power.index.strftime('%u - %H:%M')).mean()

avg_week['solar_potential'] = mhv_pv_power.groupby(mhv_pv_power.index.strftime('%u - %H:%M')).mean()
avg_week['P_battery'] = mhv_P_act['Bat_P_act'].groupby(mhv_P_act.index.strftime('%u - %H:%M')).mean()

# Make weekday names index
avg_week.set_index(['index'], drop=True, inplace=True)

#%%
max_week = pd.DataFrame()

max_week['index'] = pue_load_power['weekday'].groupby(pue_load_power.index.strftime('%u - %H:%M')).first()
max_week['PUE'] = pue_load_power['pue_total_power'].groupby(pue_load_power.index.strftime('%u - %H:%M')).max()
max_week['T5'] = pue_load_power['T5_MHV-0133'].groupby(pue_load_power.index.strftime('%u - %H:%M')).max()

max_week['T4'] = pue_load_power.drop(columns=['T5_MHV-0133', 'pue_total_power']).sum(axis='columns').groupby(pue_load_power.index.strftime('%u - %H:%M')).max()
max_week['T2'] = t2_load_power['t2_total_power'].groupby(t2_load_power.index.strftime('%u - %H:%M')).max()
max_week['T3'] = t3_load_power['t3_total_power'].groupby(t3_load_power.index.strftime('%u - %H:%M')).max()

max_week['solar_potential'] = mhv_pv_power.groupby(mhv_pv_power.index.strftime('%u - %H:%M')).min()
max_week['P_battery'] = mhv_P_act['Bat_P_act'].groupby(mhv_P_act.index.strftime('%u - %H:%M')).max()

max_week.set_index(['index'], drop=True, inplace=True)


#%% T5 analysis for thesis

t5_daily = pue_summed_load['T5'].groupby(pue_summed_load['T5'].index.strftime('%u')).mean()
pue_summed_load['weekday'] = pue_summed_load.index.strftime('%a')
t5_daily.index = pue_summed_load['weekday'].groupby(pue_summed_load.index.strftime('%u')).first()
t5_daily = t5_daily.repeat(24*4)

avg_week['T5 daily average'] = t5_daily.values
#%%
# Plot stacked graph of avg week  household and PUE demand
fig = make_subplots(1,1, shared_xaxes=True)

fig = plotting.plotly_df(fig, avg_week[['T5', 'T5 daily average']]/1000, linestyle={'shape': 'vh'})
#fig = plotting.plotly_df(fig, avg_week[['solar_potential']]/1000, linestyle={'shape': 'vh'})

fig.update_layout(
    font=dict(
            size=12
        ),
    yaxis_title="P [kW]",
    margin=dict(l=0, r=0, t=20, b=0),
    height=250,
)

fig.show()

#%%

fig.write_image('./figures/test_3.png', scale=3)

#%% Export one year load profile of average household demand
household_mean_load_year = avg_week['household'].tolist() * 53

# Save in dataframe with datetimeindex of 2018
household_mean_load_year = pd.DataFrame(household_mean_load_year[0:8761*4],
                                        index=pd.date_range("2018-01-01", periods=4*8761, freq="15min"),
                                        columns=['household_load'])
household_mean_load_year = household_mean_load_year/1000  # W to kW

household_mean_load_year = household_mean_load_year.resample('1min').interpolate()

household_mean_load_year.to_csv("./data/1min_household_load_profile.csv")

#%% Export one year load profile of average household demand
mean_baseload_year = (avg_week['household']+avg_week['T4']).tolist() * 53

# Save in dataframe with datetimeindex of 2018
mean_baseload_year = pd.DataFrame(mean_baseload_year[0:8761*4],
                                        index=pd.date_range("2018-01-01", periods=4*8761, freq="15min"),
                                        columns=['household_load'])
mean_baseload_year = mean_baseload_year/1000  # W to kW

mean_baseload_year = mean_baseload_year.resample('1min').interpolate()

mean_baseload_year.to_csv("./energy_data_analysis/model_input_data/1min_t1-t4_baseload_profile.csv")

#%% Heatmap of household demand

heatmap = plotting.plot_timeseries_heatmaps(household_load_power, column='household_total_power', zmin=0, zmax=6000, wide=True)
heatmap['layout']['yaxis']['autorange'] = 'reversed'
heatmap.show()

#%%  Household load with 7 day rolling mean
household_load_power['total_load_rolling_avg'] = household_load_power['household_total_power'].rolling('7D', center=True).mean()

fig = make_subplots(1,1)
fig = plotting.plotly_df(fig, household_load_power[['household_total_power', 'total_load_rolling_avg']])

fig.show()

#%% Heatmap of working hours

working_hours_df = pd.read_excel('./energy_data_analysis/mhv_pue_working_hours.xlsx', index_col=0)

# reverse column order and transpose
working_hours_df = working_hours_df.T

fig = go.Figure(
        data=go.Heatmap(
            z = working_hours_df.values.tolist(),
            x = working_hours_df.columns.tolist(),
            y = working_hours_df.index.tolist(),
            showscale=False
        )
    )

fig.update_layout(
    xaxis_tickformat = '%a - %H:%M',
    xaxis=dict(
        tickmode='linear',
        tick0=0,
        dtick=1000*60*60*6
    ),
    yaxis=dict(
        tickmode='linear',
        tick0=1,
        dtick=1,
        autorange='reversed'
    ),
    font=dict(size=14),
    margin=dict(l=0, r=0, t=20, b=0),
    height=400

)


#%%
fig.write_image('./figures/wh_heatmap.png', scale=3)



