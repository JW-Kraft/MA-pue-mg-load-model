from oemof import solph

from collections import OrderedDict

import pandas as pd


class ResultsAnalysis:
    """
    Class to analysis collected results of RAMP and oemof model for each scenario
    """

    def __init__(self, cache_dir_path, scenario_id):
        self.cache_dir_path = cache_dir_path
        self.scenario_id = scenario_id

        # Create oemof energysystem object -> to load energysystem from cache
        self.energysystem = solph.EnergySystem()
        # Restore energysystem from cache
        self.energysystem.restore(self.cache_dir_path, filename='mg_model_scenario_' + self.scenario_id + '.oemof')

        # Variables for results
        self.results_capacity_df = pd.DataFrame()  # df to save capacity invest of system components
        self.results_ac_flows = pd.DataFrame()  # df to save raw oemof flows in components and busses
        self.energy_balance = pd.DataFrame()  # df to track energy balance of the microgrid

    def extract_oemof_results(self):

        # Get energysystem results
        results = self.energysystem.results['main']
        results = solph.processing.convert_keys_to_strings(results, keep_none_type=True)  # Convert keys to string

        # Extract component results
        results_pv = solph.views.node(results, 'pv_l')
        results_battery = solph.views.node(results, 'battery_l')
        results_battery_inverter = solph.views.node(results, 'battery_inverter_l')
        results_battery_inverter_peak_power = solph.views.node(results, 'peak_battery_inverter_l')

        # PV east- and west-facing is optional!
        results_pv_east = solph.views.node(results, 'pv_east_l')
        results_pv_west = solph.views.node(results, 'pv_west_l')

        # Extract bus results
        results_ac_bus = solph.views.node(results, 'bus_ac_l')
        results_ac_pue_bus = solph.views.node(results, 'bus_ac_pue_l')
        results_ac_household_bus = solph.views.node(results, 'bus_ac_household_l')
        results_peak_ac_bus = solph.views.node(results, 'peak_ac_bus_l')

        # --- Extract capacity invest ---
        # Define capacity results dict
        results_capacity = OrderedDict()

        # north-facing PV invest in kW
        results_capacity['pv_invest_kW'] = results_pv['scalars'][('pv_l', 'bus_ac_l'), 'invest']

        # south-/west-facing PV invest in kW (optional!)
        results_capacity['pv_east_invest_kW'] = results_pv_east['scalars'][('pv_east_l', 'bus_ac_l'), 'invest']
        results_capacity['pv_west_invest_kW'] = results_pv_west['scalars'][('pv_west_l', 'bus_ac_l'), 'invest']

        # battery storage invest in kWh
        results_capacity['battery_invest_kWh'] = results_battery['scalars'][('battery_l', 'None'), 'invest']

        # battery inverter power invest in kW
        results_capacity['battery_inverter_kW'] = results_battery_inverter['scalars'][
            ('battery_inverter_l', 'bus_ac_l'), 'invest']

        # battery inverter peak power invest in kW ?? TODO finalise peak power model
        results_capacity['battery_inverter_peak_power_kW'] = results_battery_inverter_peak_power['scalars'][
            ('peak_battery_inverter_l', 'peak_ac_bus_l'), 'invest']

        # Save capacity invests in dataframe
        self.results_capacity_df = pd.DataFrame(results_capacity, index=[0]).T

        # --- Extract AC flows ---
        # Concat results of ac_bus (all generators connected)
        self.results_ac_flows = pd.concat([results_ac_bus['sequences'], results_ac_pue_bus['sequences'],
                                           results_ac_household_bus['sequences']])

        self.results_ac_flows = pd.concat([self.results_ac_flows, results_peak_ac_bus['sequences']])

        # Remove tuple columns
        self.results_ac_flows.columns = [x[0][0] + ' - ' + x[0][1] for x in self.results_elec_ac_flows.columns]

        # Rename flows
        self.results_ac_flows = self.results_ac_flows.rename(
            columns={
                'bus_ac_l - ac_pue_bus_link_l': 'pue_supplied',
                'bus_ac_l - ac_household_bus_link_l': 'baseload_supplied',
                'pv_l - bus_ac_l': 'pv_main_output',
                'pv_east_l - bus_ac_l': 'pv_east_output',
                'pv_west_l - bus_ac_l': 'pv_west_output',
                'battery_inverter_l - bus_ac_l': 'battery_power'
            }
        )

        # --- Calculate energy balance ---
        """energy_balance = self.results_ac_flows[['T5_supplied', 'baseload_supplied',
                                                'pv_generated']].sum() / 1  # TODO adapt for resolution
        energy_balance['bat_throughput'] = self.results_ac_flows[
                                               'bat_power'].abs().sum() / 1  # TODO adapt for resolution

        energy_balance.head()"""