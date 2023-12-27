# %%
import pandas as pd
import os
import json
import time

from model.data_input import InputData
from model.ramp_control import RampControl

import plotly.io as pio
from plotly.subplots import make_subplots

import plotting

pd.options.plotting.backend = "plotly"
pio.renderers.default = "browser"

# %%  ---- Preparation ----
# Request user to define program run name
# Repeat until valid run name was entered
while True:
    run_name = input("Enter run name:")
    # Create new directory in data_cache
    new_path = "./data_cache/" + str(run_name)
    if not os.path.exists(new_path):  # check if this dir already exists
        os.makedirs(new_path)
        break
    else:
        print(run_name + ' exists already. Pick other name.')

# Read input data for this run
input_data = InputData()
input_data.get_all_tables("./model_input_data/model_input_1_scen_1min_res_test.xlsx")

# Create dict to store scenario information for cache
scenarios_information = {}

# ---- LOAD PROFILE MODELING ----
# Define load profile modeling parameters
# Get table of ramp scenarios as df
scenarios = input_data.tables_dict['scenarios']['df']


# Timeseries to generate load profiles for
days_nr = 365
timeseries = pd.date_range("2018-01-01", periods=days_nr * 24 * 60, freq="Min")  # 2018 starts on Monday
days_timeseries = pd.date_range("2018-01-01", periods=days_nr, freq="D")
# Timeseries of seconds (for peak current model)
seconds_timeseries = pd.date_range("2018-01-01", periods=days_nr * 24 * 60 * 60, freq="S")

# --- Iterate RAMP scenarios ---
for index, row in scenarios.iterrows():

    print("Running load profile model for scenario " + row['scenario_id'])

    # Read this scenario's input data
    pue_input = input_data.read_pue_input(
        file="./model_input_data/ramp_model_input/" + row['ramp_input_file_name'])

    # Create instance of RampControl
    ramp_run = RampControl()

    # Create RAMP UseCase for every day
    print("Initialise RAMP use cases for scenario " + row['scenario_id'])
    start = time.perf_counter()
    for day in days_timeseries:
        appliances_list = ramp_run.add_use_case(
            name=day,
            pue_dict=pue_input,
            day=day.day_name(),
            month=day.month
        )
    print('done after: ' + str(time.perf_counter() - start) + ' seconds')

    # Generate load profiles of every appliance for every day
    print("Generating 1min load profiles with RAMP for scenario " + row['scenario_id'])
    start = time.perf_counter()
    load_profiles = ramp_run.run_use_cases(appliances_list, timeseries)
    print('done after: '+ str(time.perf_counter()-start) + ' seconds')

    # Generate start-up peak power profiles
    print("Generating peak power profiles for scenario " + row['scenario_id'])

    start = time.perf_counter()
    peak_power_profiles, peak_power_minute_max = ramp_run.calculate_peak_power_timeseries(load_profiles, pue_input,
                                                                                          seconds_timeseries)
    print('done after: ' + str(time.perf_counter() - start) + ' seconds')

    # Calculate total load profile
    load_profiles['total'] = load_profiles.sum(axis='columns')

    # Add peak power minute max profile to load_profile df
    load_profiles['peak_power_profile'] = peak_power_minute_max

    # Save load profiles and peak power profile as CSV
    print('Saving generated load profiles for scenario '+ row['scenario_id'])
    file_path = "./data_cache/" + run_name + "/load_profile_scenario_" + row['scenario_id'] + ".csv"
    load_profiles.to_csv(file_path)  # save load profiles (including peak power profile) as CSV

    # save filepath in scenario_information dict
    scenarios_information[row['scenario_id']] = {
        'modelled_load_profiles': file_path,
        'ramp_input_file_name': row['ramp_input_file_name'],
        'oemof_input_file_name': row['oemof_input_file_name'],
        'description': row['description']
    }

# Save scenario_information dict as json in this run's cache folder
with open("./data_cache/" + run_name + "/scenarios_information.json", "w+") as file:
    json.dump(scenarios_information, file)
    print('Modeled load profiles and scenarios information saved.')