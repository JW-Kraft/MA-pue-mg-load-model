#%%
import soda
import matplotlib.pyplot as plt
import pandas as pd

import plotting
from plotly.subplots import make_subplots

#%% Create object of SolarSite
# Mahavelona, MDG
lat = -19.1703
lon = 46.523
site = soda.SolarSite(lat,lon)

year = "2018"
leap_year = False
interval = "30"
utc = False

# Get data from NSRDB
df = site.get_nsrdb_data(year,leap_year,interval,utc)

#%% plot nsrdb data
fig = make_subplots(1,1)
fig = plotting.plotly_df(fig, df)
fig.show()

#%% Generate synthetic high-resolution power output - Setup
clearsky = False
capacity = 1
DC_AC_ratio = 1.23  # 123 kWp solar arrays, 100 kW solar inverters (2x 50 kW SMA Tripower Core)

inv_eff = 98.1  # SMA Tripower Core
losses = 0
array_type = 0

resolution = "1min"
high_res_solar_data = pd.DataFrame()
low_res_solar_data = pd.DataFrame()
daterange = pd.date_range(start="2018-01-01", end="2018-12-31", freq='D')

#%% North facing

tilts = [10, 20]  # only 20° tilt -> = MHV setup
azimuth = 0  # 0 = north-facing

for tilt in tilts:
    pwr_north = site.generate_solar_power_from_nsrdb(clearsky, capacity, DC_AC_ratio, tilt, azimuth, inv_eff, losses, array_type)

    i = 0
    data = pd.DataFrame()
    for date in daterange:
        data = pd.concat([data, site.generate_high_resolution_power_data(resolution, date.strftime("%Y-%m-%d"))])
        print('day '+ str(i))
        print(date)
        i = i + 1

    low_res_solar_data['north_'+str(tilt)] = pwr_north
    high_res_solar_data['north_'+str(tilt)] = data['HighRes']


# Run for multiple east-west configurations

tilts = [10, 20, 30, 40, 50]

pv_pwr_west = pd.DataFrame(index=pwr_north.index)
pv_pwr_east = pd.DataFrame(index=pwr_north.index)


for tilt in tilts:

    # Calculate low_res pv_pwr output
    # east -> azimuth=90
    data = pd.DataFrame()  # Define empty dataframe for high res data
    i = 0
    pv_pwr_east['tilt_'+str(tilt)] = site.generate_solar_power_from_nsrdb(clearsky, capacity, DC_AC_ratio, tilt, 90, inv_eff, losses, array_type)

    for date in daterange:
        data = pd.concat([data, site.generate_high_resolution_power_data(resolution, date.strftime("%Y-%m-%d"))])
        print('east tilt:'+ str(tilt) + ' - day ' + str(i))
        i = i + 1

    # collect in dataframes
    low_res_solar_data['east_'+str(tilt)] = pv_pwr_east['tilt_'+str(tilt)]
    high_res_solar_data['east_'+str(tilt)] = data['HighRes']

    print('done east tilt '+str(tilt))

    # west -> azimuth=270
    data = pd.DataFrame()  # Define empty dataframe for high res data
    i = 0
    pv_pwr_west['tilt_'+str(tilt)] = site.generate_solar_power_from_nsrdb(clearsky, capacity, DC_AC_ratio, tilt, 270, inv_eff, losses, array_type)
    for date in daterange:
        data = pd.concat([data, site.generate_high_resolution_power_data(resolution, date.strftime("%Y-%m-%d"))])
        print('west tilt:'+ str(tilt) + ' - day ' + str(i))
        i = i + 1

    # collect in dataframes
    low_res_solar_data['west_' + str(tilt)] = pv_pwr_west['tilt_' + str(tilt)]
    high_res_solar_data['west_' + str(tilt)] = data['HighRes']

    print('done west tilt ' + str(tilt))

#%%
# Save results in CSV
low_res_solar_data.to_csv('./pv_resource_model/pv_resource_data/30min_res_pv_mhv.csv')
high_res_solar_data.to_csv('./pv_resource_model/pv_resource_data/1min_res_pv_mhv.csv')

# Generate 1min solar data with simple interpolation
high_res_solar_data_interpolated = low_res_solar_data.resample('1min').interpolate()
high_res_solar_data_interpolated.to_csv('./pv_resource_model/pv_resource_data/1min_res_interpolated_pv_mhv.csv')

