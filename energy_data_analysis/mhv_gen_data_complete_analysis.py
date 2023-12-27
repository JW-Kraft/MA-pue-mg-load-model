#%%
import pandas as pd

#%% Read MVH complete gen sys data (provided by Fabian)
mhv_gen_sys_data = pd.read_csv('./energy_data_analysis/Mahavelona Gen System Data/MHV_gen_sys_complete.csv',
                               parse_dates=[0],
                               index_col=0)

#%% Extract useful data and rename columns

# TODO: complete MHV gen sys data (provided by Fabian) seems to be faulty. Currently not urgent. Possibly easier to pull from Grafana
mhv_gen_sys_data_clean = mhv_gen_sys_data[['Sol1_powerACL1', 'Sol1_powerACL2', 'Sol1_powerACL3',
                                           'Sol2_powerACL1', 'Sol2_powerACL2', 'Sol2_powerACL3']]