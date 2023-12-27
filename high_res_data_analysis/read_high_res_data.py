import pandas as pd
import numpy as np
from tqdm import tqdm

import os

def read_edr_data(dir_path, current_corr_factor):
    """
    Read processed EDR 100ms or 1s EDR data
    - reads all individual CSV files in passed folder and combines them in one dataframe
        o currently dict with one df for each phase -> TO DO: change to one multi-index dataframe

    :param dir_path:
    :param current_corr_factor: factor to account for "double loop" of Rogowski coil (= nr. of loops"
    :return:
    """

    dir = os.fsencode(dir_path)

    voltages = {
        'L1': [],
        'L2': [],
        'L3': []
    }
    currents = {
        'L1': [],
        'L2': [],
        'L3': [],
        'N': []
    }

    # Columns to read from EDR files
    I_col = ['Time', 'ms+-', 'PowerP', 'PowerQ', 'Effektivwert', 'Amplitude', 'THD']
    U_col = ['Time', 'ms+-', 'f50', 'Effektivwert', 'Amplitude', 'THD']

    # New column names for final dataframe -> same order and length as in EDR files but without 'Time' and 'ms+-' column
    I_col_names = ['P', 'Q', 'I_eff', 'I_amp', 'I_thd']
    U_col_names = ['freq' ,'U_eff', 'U_amp', 'U_thd']

    print('Read EDR CSV files')
    for file in tqdm(os.listdir(dir)):
        filename = os.fsdecode(file)

        phase = filename[-7:-4]
        if phase == '_L1':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=U_col)
            voltages['L1'].append(df)
        elif phase == '_L2':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=U_col)
            voltages['L2'].append(df)
        elif phase == '_L3':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=U_col)
            voltages['L3'].append(df)
        elif phase == 'L4I':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=I_col)
            currents['L1'].append(df)
        elif phase == 'L5I':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=I_col)
            currents['L2'].append(df)
        elif phase == 'L6I':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=I_col)
            currents['L3'].append(df)
        elif phase == 'L7I':
            df = pd.read_csv(dir_path + filename, sep=';', header=0, usecols=I_col)
            currents['N'].append(df)
        else:
            print(str(filename) + ' has invalid filename format')

    # Dict to build final dataframe with
    phase_dfs = {}

    # Loop through every phase's current data
    print('Loop through every phases current data')
    for phase, data in tqdm(currents.items()):
        # Concat all dataframes of this phase and add to phases_dfs dict -> create entry for phases L1 - L3 and N
        print('Concat files')
        phase_dfs[phase] = pd.concat(data)
        phase_dfs[phase] = phase_dfs[phase].dropna(axis=0)
        print('done')
        # make Time column datetime
        phase_dfs[phase]['Time'] = (pd.to_datetime(phase_dfs[phase]['Time'], format='%d.%m.%Y %H:%M:%S') +
                                    pd.TimedeltaIndex(phase_dfs[phase]['ms+-'], unit='ms'))

        phase_dfs[phase].set_index('Time', drop=True, inplace=True)  # make 'Time' column index
        phase_dfs[phase].drop(columns=['ms+-'], inplace=True)  # drop ms column
        phase_dfs[phase].columns = I_col_names  # Rename column names to user defined names
        phase_dfs[phase].sort_index(inplace=True)  # sort to make sure index (time) is monotonically increasing

        # Modify currents and power to account for "double loop" of Rogowski coil
        phase_dfs[phase]['I_eff'] = phase_dfs[phase]['I_eff']/current_corr_factor
        phase_dfs[phase]['I_amp'] = phase_dfs[phase]['I_amp'] / current_corr_factor

        phase_dfs[phase]['P'] = phase_dfs[phase]['P'] / current_corr_factor
        phase_dfs[phase]['Q'] = phase_dfs[phase]['Q'] / current_corr_factor

        # Calculate apparent power
        phase_dfs[phase]['S'] = np.sqrt(np.square(phase_dfs[phase]['Q']) + np.square(phase_dfs[phase]['P']))
        # Calculate load factor
        phase_dfs[phase]['cos(phi)']  = phase_dfs[phase]['P'] / phase_dfs[phase]['S']

    # Loop through every phase's voltage data
    print('Loop through every phases voltage data')
    for phase, data in tqdm(voltages.items()):
        # Concat all dataframes of this phase
        voltages_df = pd.concat(data)
        voltages_df = voltages_df.dropna()
        # make Time column datetime
        voltages_df['Time'] = (pd.to_datetime(voltages_df['Time'], format='%d.%m.%Y %H:%M:%S') +
                               pd.TimedeltaIndex(voltages_df['ms+-'], unit='ms'))

        voltages_df.set_index('Time', drop=True, inplace=True)  # make 'Time' column index
        voltages_df.drop(columns=['ms+-'], inplace=True)  # drop ms column
        voltages_df.columns = U_col_names  # Rename column names to user defined names
        voltages_df.sort_index(inplace=True)  # sort to make sure index (time) is monotonically increasing

        # Change frequency column from EDR file output (delta from 50Hz in mHz) to Hz
        voltages_df['freq'] = 50 + voltages_df['freq']/1000

        # Join voltages dataframe with currents dataframe in phases_dfs dict for corresponding phase
        phase_dfs[phase] = phase_dfs[phase].join(voltages_df, how='outer')

    # Combine all phases' data in one dataframe and return
    return phase_dfs #pd.concat(phase_dfs, axis=1)

def read_pico_data(file_path, agg_dur='20ms'):
    """
    - Read pico log CSV file
    - calculate instantaneous power for every phase
    - calculate RMS for I and U as well as apparent power (S) with specified agg_dur
    - return 2 multi-index dataframes (first-level col for every phase):
        o 1st: instantaneous raw data
        o 2nd: aggregated data
    :param file_path:
    :return:
    """
    # Read pico log CSV file
    pico_df = pd.read_csv(file_path,
                          index_col=0,
                          parse_dates=[0]
                          )

    # Turn UTC epoch time (s) index into datetime index
    pico_df.set_index(pd.to_datetime(pico_df.index, unit='s'), inplace=True)

    # Create dict of pico data and build multi-column df with U and I for each phase
    pico_data = {
        'L1': pd.DataFrame(
            data={
                'I': pico_df['I1 Ave. (A)'],
                'U': pico_df['U1 Ave. (V)']
            },
            index=pico_df.index
        ),

        'L2': pd.DataFrame(
            data={
                'I': pico_df['I2 Ave. (A)'],
                'U': pico_df['U2 Ave. (V)']
            },
            index=pico_df.index
        ),
        'L3': pd.DataFrame(
            data={
                'I': pico_df['I3 Ave. (A)'],
                'U': pico_df['U3 Ave. (V)']
            },
            index=pico_df.index
        ),
        'N': pd.DataFrame(
            data={
                'I': pico_df['IN Ave. (A)']
            }
        )
    }

    # Build multi-column df from dict
    pico_data = pd.concat(pico_data, axis=1)

    # Calculate instantaneous power for each Phase
    for phase in pico_data.columns.levels[0]:
        if phase != 'N':  # not for phase N
            pico_data.loc[:, (phase, 'P')] = pico_data.loc[:, (phase, 'U')] * pico_data.loc[:, (phase, 'I')]


    # -- Calculate resampled data --
    pico_data_agg = {}
    for phase in pico_data.columns.levels[0]:
        if phase != 'N':
            pico_data_agg[phase] = pico_data.loc[:, phase].resample(agg_dur).agg({
                'I': np.std,
                'U': np.std,
                'P': np.mean
            }).rename(columns={'I': 'I_eff', 'U': 'U_eff'})
            pico_data_agg[phase]['S'] = pico_data_agg[phase]['I_eff'] * pico_data_agg[phase]['U_eff']
            pico_data_agg[phase]['P'] = pico_data_agg[phase]['P'] * -1  # invert -> delivered power is positive
        else:
            pico_data_agg[phase] = pico_data.loc[:, phase].resample(agg_dur).agg({
                'I': np.std,
            })

    pico_data_agg = pd.concat(pico_data_agg, axis=1)

    return pico_data, pico_data_agg
