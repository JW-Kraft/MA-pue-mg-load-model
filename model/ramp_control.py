import pandas as pd
import ramp
import numpy as np
import random
import math


class RampControl:
    def __init__(self):

        self.ramp_use_cases = {}

    def add_use_case(self, name, pue_dict, day, month):
        """
        Function to process user input data and generate RAMP use case from it
        NEW version -> update 2023-10-24 for new input file format
        :param name:
        :param pue_dict:
        :param day:
        :param month:
        :param preferred:
        :return:
        """

        # Create dict containing users
        users_dict = {}
        appliances_list = []
        # Loop through appliances in pue_dict
        for appliance, data in pue_dict.items():
            appliances_list.append(appliance)
            # Get preferred usage_windows from input_data
            day_pref = data['weekly_preferences'][day].iloc[0:24]

            window_1 = None
            window_2 = None
            window_3 = None
            windows_nr = 0

            # Define window 1
            # Do random window calculation outside of RAMP to allow for individual manipulation window start and end
            if not math.isnan(day_pref['window_1_start']):
                # Rand window calculation in RAMP: random.randint(_window[0] - _random_var, _window[0] + _random_var
                # !! Different here: window_X_start_var is absolut value in hours!
                rand_len = (day_pref['window_1_end'] - day_pref['window_1_start']) * 60  # window length in min
                rand_start = random.randint(day_pref['window_1_start']*60-day_pref['window_1_start_var']*60,
                                            day_pref['window_1_start']*60+day_pref['window_1_start_var']*60)

                rand_end = random.randint(day_pref['window_1_end']*60-day_pref['window_1_end_var']*60,
                                          day_pref['window_1_end']*60-day_pref['window_1_end_var']*60)
                window_1 = [rand_start, rand_end]
                windows_nr = windows_nr+1

            # Define window 2
            if not math.isnan(day_pref['window_2_start']):
                # Rand window calculation in RAMP: random.randint(_window[0] - _random_var, _window[0] + _random_var
                rand_len = (day_pref['window_2_end'] - day_pref['window_2_start']) * 60  # window length in min
                rand_start = random.randint(day_pref['window_2_start']*60-day_pref['window_2_start_var']*60,
                                            day_pref['window_2_start']*60+day_pref['window_2_start_var']*60)

                rand_end = random.randint(day_pref['window_2_end']*60-day_pref['window_2_end_var']*60,
                                          day_pref['window_2_end']*60+day_pref['window_2_end_var']*60)
                window_2 = [rand_start, rand_end]
                windows_nr = windows_nr + 1

            # Define window 3
            if not math.isnan(day_pref['window_3_start']):
                # Rand window calculation in RAMP: random.randint(_window[0] - _random_var, _window[0] + _random_var
                rand_len = (day_pref['window_3_end'] - day_pref['window_3_start']) * 60  # window length in min
                rand_start = random.randint(day_pref['window_3_start']*60-day_pref['window_3_start_var']*60,
                                            day_pref['window_3_start']*60+day_pref['window_3_start_var']*60)

                rand_end = random.randint(day_pref['window_3_end']*60-day_pref['window_3_end_var']*60,
                                          day_pref['window_3_end']*60+day_pref['window_3_end_var']*60)
                window_3 = [rand_start, rand_end]
                windows_nr = windows_nr + 1

            # Check if user does not exist yet
            if data['User'] not in users_dict.keys():
                users_dict[data['User']] = ramp.User(user_name=data['User'], num_users=1)   # Create user instance

            # Get this days func_time (in min)
            func_time = data['weekly_preferences'][day].loc['Usage time'] * 60

            # Get func_time fraction that is subject to random variability
            time_fraction_random_variability = data['weekly_preferences'][day].loc['Usage time variability']

            # Consider monthly variation of usage time
            func_time = func_time * data['monthly_variation']['Usage time variation'].loc[month]

            # add appliance to this user
            users_dict[data['User']].add_appliance(
                name=appliance,
                number=data['Number'],
                power=data['Nominal power'],

                fixed_cycle=1,  # one duty cycle
                p_11=data['P1'],
                t_11=data['t1'],  # start-up time is always 1
                p_12=data['P1'],
                t_12=data['t2'],  # steady state duration = total duration - start-up time
                r_c1=data['Duration variability'],

                func_time=func_time,  # total time of use per day
                time_fraction_random_variability=time_fraction_random_variability,

                num_windows=windows_nr,
                window_1=window_1,
                window_2=window_2,
                window_3=window_3,

                random_var_w=0   # Random window variability is specified beforehand!
            )

        use_case = ramp.UseCase(
            users=list(users_dict.values())
        )

        self.ramp_use_cases[name] = use_case

        return appliances_list

    def add_use_case_old(self, name, pue_dict, day, month, preferred=True):
        """
        Function to process user input data and generate RAMP use case from it
        OLD version -> update 2023-10-24 for new input file format
        :param name:
        :param pue_dict:
        :param day:
        :param month:
        :param preferred:
        :return:
        """

        # Create dict containing users
        users_dict = {}
        appliances_list = []
        # Loop through appliances in pue_dict
        for appliance, data in pue_dict.items():
            appliances_list.append(appliance)
            # Get preferred usage_windows from input_data
            day_pref = data['weekly_preferences'][day].iloc[0:24].tolist()

            window_1 = None
            window_2 = None
            window_3 = None

            window_counter = 0

            start = None
            end = None
            for hour, pref in enumerate(day_pref):  # loop through hour of the day
                if hour == 23 and start:   # if last hour of day and a start is defined
                    end = 24    # window always ends

                if pref == 1 and start == None:   # start of new window found
                    start = hour    # set start
                    window_counter = window_counter + 1  # add to window counter
                elif pref != 1 and start != None:   # end of new window found
                    end = hour + 1  # set end

                if start and end:   # if start and end hour are found
                    # add window
                    if window_counter == 1:
                        window_1 = [start*60, end*60]
                    elif window_counter == 2:
                        window_2 = [start*60, end*60]
                    elif window_counter == 3:
                        window_3 = [start*60, end*60]
                    elif window_counter > 3:
                        raise UserWarning('More than 3 windows specified!')
                    # Reset start and end to None
                    start = None
                    end = None

            # Check if user does not exist yet
            if data['User'] not in users_dict.keys():
                users_dict[data['User']] = ramp.User(user_name=data['User'], num_users=1)   # Create user instance

            # Get this days func_time (in min)
            if preferred:
                func_time = data['weekly_preferences'][day].loc['Preferred usage time'] * 60
            else:
                func_time = data['weekly_preferences'][day].loc['Possible usage time'] * 60
            # Get func_time fraction that is subject to random variability
            time_fraction_random_variability = data['weekly_preferences'][day].loc['Usage time variability']

            # Get random variability of usage windows
            random_var_w = data['weekly_preferences'][day].loc['Usage windows variability']

            # Consider monthly variation of usage time
            func_time = func_time * data['monthly_variation']['Usage time variation'].loc[month]

            # add appliance to this user
            users_dict[data['User']].add_appliance(
                name=appliance,
                number=data['Number'],
                power=data['Nominal power'],

                fixed_cycle=1,  # one duty cycle
                p_11=data['Start-up power'],
                t_11=1,  # start-up time is always 1
                p_12=data['Steady state power'],
                t_12=data['Duty cycle duration']-1,  # steady state duration = total duration - start-up time
                r_c1=data['Duration variability'],

                func_time=func_time,  # total time of use per day
                time_fraction_random_variability=time_fraction_random_variability,

                window_1=window_1,
                window_2=window_2,
                window_3=window_3,

                random_var_w=random_var_w    # TEST variability of windows NOT IN % !!!
            )

        use_case = ramp.UseCase(
            users=list(users_dict.values())
        )

        self.ramp_use_cases[name] = use_case

        return appliances_list

    def run_use_cases(self, appliances_list ,timeseries):

        # define dict for resulting load profiles
        load_profiles = {app: [] for app in appliances_list}

        for name, use_case in self.ramp_use_cases.items():

            # Calculate peak time range of this use case
            peak_time_range = ramp.calc_peak_time_range(use_case.users)

            # Loop through all users
            for user in use_case.users:
                # Loop through user's appliances
                for appliance in user.App_list:
                    # Generate appliance load profile
                    # if this appliance has at least one usage window in this use_case (=this day)
                    if appliance.num_windows > 0:
                        appliance.generate_load_profile(
                            prof_i=0,
                            peak_time_range=peak_time_range,
                            day_type=0,  # is always week day -> day types defined through different use cases
                            power=10  # does not matter since we only use duty cycles
                        )
                        load_profiles[appliance.name].extend(appliance.daily_use)
                    else:   # otherwise add zeroes -> no operation on this day
                        load_profiles[appliance.name].extend([0]*1440)

        load_profiles_df = pd.DataFrame(load_profiles, index=timeseries)

        return load_profiles_df

    def calculate_peak_power_timeseries(self, load_profiles, pue_dict, seconds_timeseries):
        """
        Calculates timerseries of switch-on power peaks based in RAMP-modelled PUE load profiles
        :param load_profiles:
        :param pue_dict:
        :param seconds_timeseries:
        :return: df containing peak power timeseries with seconds resolution,
        timeseries resampled to min with max peak power within that minute
        """

        start_up_times = load_profiles.copy()

        # Set all values that equal 0.001 to 0 -> fix for RAMP marking usage windows with 0.001
        start_up_times[start_up_times == 0.001] = 0

        # Set all values to 0 which previous value was not 0 -> only leave "start-up events"
        start_up_times[start_up_times.shift() != 0] = 0

        # Turn df into numpy array
        start_up_times = start_up_times

        # Create new df for peak power profiles
        peak_power_profiles = pd.DataFrame(columns=start_up_times.columns)

        # Loop through each appliances start up times
        for appliance, ts in start_up_times.items():
            start_up_peak = pue_dict[appliance]['Start-up peak']
            start_up_duration = pue_dict[appliance]['Start-up duration']

            # turn ts pandas Series to np array
            np_ts = ts.to_numpy()

            # Loop through every timestep
            i = 0
            peak_power_array = [0] * len(np_ts)  # preallocate array
            for elem in np_ts:
                if elem == 0:  # if no switch on event
                    peak_power_array[i] = [0] * 60  # add list with 0 for every second
                else:  # switch on event
                    # Define list of zeros for this minute
                    minute = [0] * 60
                    rand_start = random.randint(0, 60 - start_up_duration)  # draw random start time index

                    # place start up power for length of start-up duration
                    minute[rand_start:rand_start + start_up_duration] = [start_up_peak] * start_up_duration
                    peak_power_array[i] = minute.copy()  # save in list
                i = i + 1
            # flatten np array and add to peak power_profiles
            peak_power_profiles[appliance] = np.array(peak_power_array).flatten()

        # Set index of peak_power profiles timeseries to seconds
        peak_power_profiles.set_index(seconds_timeseries, inplace=True)
        peak_power_profiles['Total_peak_power'] = peak_power_profiles.sum(axis='columns')

        # resample to minutes with the maximum of the summed peak power for every minute
        peak_power_minute_max = pd.DataFrame(peak_power_profiles['Total_peak_power'].resample('min').max()).rename_axis()

        return peak_power_profiles, peak_power_minute_max

