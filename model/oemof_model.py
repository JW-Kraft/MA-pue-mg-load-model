import pandas as pd
from collections import OrderedDict
import random

from oemof import solph
from oemof.tools import economics

import plotting
from plotly.subplots import make_subplots


class OemofModel:

    def __init__(self, pue_load_profile,
                 household_baseload,
                 peak_power_profile,
                 system_data,
                 pv_gen_ts,
                 freq,
                 peak_power_model=False,
                 pue_load_exists=True,
                 household_baseload_exists=True,
                 pv_south_exists=True,
                 pv_east_west_exists=False,
                 pv_east_ts=None,
                 pv_west_ts=None
                 ):

        self.peak_power_model = peak_power_model

        # Resample input timeseries
        household_baseload = household_baseload.resample(freq).mean()
        pue_load_profile = pue_load_profile.resample(freq).mean()
        pv_gen_ts = pv_gen_ts.resample(freq).mean()
        peak_power_profile = peak_power_profile.resample(freq).max()

        # Get model timeseries from pue load profile datetime index
        self.timeseries = pd.DataFrame(index=pue_load_profile.index)

        # Get max load = nominal value
        self.pue_load_nominal = pue_load_profile.max()
        # Add load in capacity factors to timeseries
        self.timeseries['pue_load'] = pue_load_profile / pue_load_profile.max()
        self.timeseries['pue_load'] = self.timeseries['pue_load']

        # Load peak power timeseries
        self.timeseries['peak_power'] = peak_power_profile
        self.peak_power_nominal = self.timeseries['peak_power'].max()
        self.timeseries['peak_power'] = self.timeseries['peak_power'] / self.peak_power_nominal

        # Get residential base load timeseries for range in which PUE load is specified
        # self.timeseries['household_baseload'] = household_baseload/household_baseload.max()
        # TEST
        self.timeseries['household_baseload'] = household_baseload
        self.household_baseload_nominal = self.timeseries['household_baseload'].max()
        self.timeseries['household_baseload'] = self.timeseries['household_baseload'] / self.household_baseload_nominal

        self.pue_load_exists = pue_load_exists
        self.household_baseload_exists = household_baseload_exists

        # Get PV timeseries for the range in which load is specified
        try:
            self.timeseries['pv'] = pv_gen_ts[self.timeseries.index]
        except:
            raise Exception('No PV gen ts timesteps found to match load profile')

        # Add PV timeseries for east and west facing panels if east-west system
        self.pv_east_west_exists = pv_east_west_exists
        self.pv_south_exists = pv_south_exists
        if self.pv_east_west_exists:
            # Resample to specified frequency
            pv_east_ts = pv_east_ts.resample(freq).mean()
            pv_west_ts = pv_west_ts.resample(freq).mean()

            # Add to timeseries dataframe
            try:
                self.timeseries['pv_east'] = pv_east_ts[self.timeseries.index]
            except:
                raise Exception('No PV east gen timesteps found to match load profile')

            try:
                self.timeseries['pv_west'] = pv_west_ts[self.timeseries.index]
            except:
                raise Exception('No PV west gen timesteps found to match load profile')

        # set timeseries index frequency (needed for oemof)
        self.timeseries.index.freq = freq

        # Create energy system object
        self.energysystem = solph.EnergySystem(timeindex=self.timeseries.index, infer_last_interval=False)
        # Create solph model object for customs constraints
        self.om = solph.Model(self.energysystem)

        # Get user input data
        self.general_data = system_data['general_data']['dct']
        self.tariff_data = system_data['tariff_data']['dct']

        # Save component data in dict
        self.components_data = {
            'pv': system_data['pv']['dct'],
            'pv_west': system_data['pv_west']['dct'],
            'pv_east': system_data['pv_east']['dct'],
            'battery_capacity': system_data['battery_capacity']['dct'],
            'battery_inverter': system_data['battery_inverter']['dct'],
            'genset': system_data['genset']['dct']
            # 'grid': system_data['grid']['dct'] -> not considered here
        }
        print('components_data read')
        # Calculate components' cost data
        self.components_specific_costs = self.calc_components_costs()

        # calculate value of total load that can be left unsupplied from specified fraction
        # total load for timeframe specified by pue_load
        if not pue_load_exists:
            total_load = household_baseload[pue_load_profile.index]
        elif not household_baseload_exists:
            total_load = pue_load_profile
        else:
            total_load = pue_load_profile + household_baseload[pue_load_profile.index]

        # Energy [kWh] that can be left unsupplied
        # = Total energy demand in kWh multiplied with unsupplied_total_demand fraction
        self.unsupplied_total_demand = total_load.resample('1h').mean().sum() \
                                       * self.general_data['unsupplied_total_demand']

        self.unsupplied_pue_demand = pue_load_profile.resample('1h').mean().sum() \
                                     * self.general_data['unsupplied_pue_demand']

        self.unsupplied_household_demand = pue_load_profile.resample('1h').mean().sum() \
                                           * self.general_data['unsupplied_household_demand']

        # Variables for results
        self.results_oemof = None  # oemof results output
        self.results_components_capacities = None  # individual components optimised capacities
        self.results_components_costs = None  # individual components' cost results
        self.results_system = None  # overall system results (KPIs: LCOE, energy delivered, capital cost, OPEX...)
        self.results_ac_flows = pd.DataFrame()  # AC flows in the system

    def calc_components_costs(self):
        """
        - calculate annuities of all system components [€/MW(h)_capacity/a]
        - save component fixed opex [€/MWh(h)_capacity/a]
        - calculate component capital cost (annuities + fixed_opex)
        - save component variable opex (=marginal cost) [€/MWh_generated]

        :return: dict of components' cost data:
        {component_name: {annuity: ... , fixed_opex: ... , capital_cost: ... , variable_opex: ...}}
        """

        components_costs = {}
        for component, component_data in self.components_data.items():
            annuity = economics.annuity(capex=component_data['specific_capex'],
                                        n=component_data['lifetime'],
                                        wacc=self.general_data['wacc'])

            components_costs[component] = {
                'specific_capex': component_data['specific_capex'],
                'annuity': annuity,
                'fixed_opex': component_data['fixed_opex'],
                'capital_cost': annuity + component_data['fixed_opex'],
                'variable_opex': component_data['variable_opex']
            }

        return components_costs

    def build_energysystem(self):
        #  --- Create buses ---
        # AC grid bus
        bus_ac = solph.buses.Bus(label='bus_ac_l')
        # AC household load bus -> required to allow for separate unsupplied_household_load
        bus_ac_household = solph.buses.Bus(label='bus_ac_household_l')
        # AC pue load bus -> required to allow for separate pue_load
        bus_ac_pue = solph.buses.Bus(label='bus_ac_pue_l')
        # Battery DC-side bus
        bus_bat_dc = solph.buses.Bus(label='bus_bat_dc_l')

        self.energysystem.add(bus_ac, bus_bat_dc, bus_ac_household, bus_ac_pue)

        # --- Links ---
        # Linking AC grid bus with AC household and AC pue bus
        ac_pue_bus_link = solph.components.Link(
            label="ac_pue_bus_link_l",
            inputs={bus_ac: solph.flows.Flow()},
            outputs={bus_ac_pue: solph.flows.Flow()},
            conversion_factors={(bus_ac, bus_ac_pue): 1}
        )

        ac_household_bus_link = solph.components.Link(
            label="ac_household_bus_link_l",
            inputs={bus_ac: solph.flows.Flow()},
            outputs={bus_ac_household: solph.flows.Flow()},
            conversion_factors={(bus_ac, bus_ac_household): 1})

        self.energysystem.add(ac_pue_bus_link, ac_household_bus_link)

        # --- Loads ---
        # sink component for electricity excess
        electricity_excess = solph.components.Sink(label='electricity_excess_l', inputs={bus_ac: solph.flows.Flow()})
        loads_list = [electricity_excess]  # add to list of loads components

        if self.pue_load_exists:
            # create sink object representing the pue load
            pue_load = solph.components.Sink(label='pue_load_l',
                                             inputs={bus_ac_pue: solph.flows.Flow(
                                                 fix=self.timeseries['pue_load'],
                                                 nominal_value=self.pue_load_nominal)})
            loads_list.append(pue_load)

        if self.household_baseload_exists:
            # create sink object representing the household baseload
            household_baseload = solph.components.Sink(label='household_baseload_l',
                                                       inputs={bus_ac_household: solph.flows.Flow(
                                                           fix=self.timeseries['household_baseload'],
                                                           nominal_value=self.household_baseload_nominal)})
            loads_list.append(household_baseload)

        self.energysystem.add(*loads_list)

        # -- PV systems ---
        # create fixed source for PV systems
        if self.pv_south_exists:
            pv = solph.components.Source(label='pv_l',
                                         outputs={bus_ac: solph.flows.Flow(fix=self.timeseries['pv'],
                                                                           variable_costs=0,
                                                                           investment=solph.Investment(
                                                                               ep_costs=
                                                                               self.components_specific_costs['pv'][
                                                                                   'capital_cost'],
                                                                               existing=self.components_data['pv'][
                                                                                   'existing_capacity']
                                                                           ))})
            self.energysystem.add(pv)

        if self.pv_east_west_exists:
            pv_west = solph.components.Source(label='pv_west_l',
                                              outputs={bus_ac: solph.flows.Flow(fix=self.timeseries['pv_west'],
                                                                                variable_costs=0,
                                                                                investment=solph.Investment(
                                                                                    ep_costs=
                                                                                    self.components_specific_costs[
                                                                                        'pv_west']['capital_cost'],
                                                                                    existing=
                                                                                    self.components_data['pv_west'][
                                                                                        'existing_capacity']
                                                                                ))})

            pv_east = solph.components.Source(label='pv_east_l',
                                              outputs={bus_ac: solph.flows.Flow(fix=self.timeseries['pv_east'],
                                                                                variable_costs=0,
                                                                                investment=solph.Investment(
                                                                                    ep_costs=
                                                                                    self.components_specific_costs[
                                                                                        'pv_east']['capital_cost'],
                                                                                    existing=
                                                                                    self.components_data['pv_east'][
                                                                                        'existing_capacity']
                                                                                ))})
            self.energysystem.add(pv_west, pv_east)

        # --- Battery storage ---
        battery = solph.components.GenericStorage(label='battery_l',
                                                  inputs={bus_bat_dc: solph.flows.Flow()},
                                                  outputs={bus_bat_dc: solph.flows.Flow(
                                                      variable_costs=self.components_specific_costs['battery_capacity'][
                                                          'variable_opex']
                                                  )},
                                                  loss_rate=self.components_data['battery_capacity']['loss'],
                                                  initial_storage_level=None,
                                                  balanced=False,
                                                  min_storage_level=self.components_data['battery_capacity']['min_soc'],
                                                  max_storage_level = self.components_data['battery_capacity']['max_soc'],

                                                  # C-rate (per timestep) -> divide by 60 to adapt for 1 min timesteps
                                                  # invest_relation_input_capacity=self.tech['Battery']['c-rate']/60,
                                                  # invest_relation_output_capacity=self.tech['Battery']['c-rate']/60,

                                                  inflow_conversion_factor=1,
                                                  outflow_conversion_factor=self.components_data['battery_capacity'][
                                                      'efficiency'],

                                                  investment=solph.Investment(
                                                      ep_costs=self.components_specific_costs['battery_capacity'][
                                                          'capital_cost'],
                                                      existing=self.components_data['battery_capacity'][
                                                          'existing_capacity']
                                                  ))

        # Converter object representing battery inverter
        battery_inverter = solph.components.Converter(label='battery_inverter_l',
                                                      inputs={bus_bat_dc: solph.flows.Flow(bidirectional=True)},
                                                      outputs={bus_ac:
                                                          solph.flows.Flow(investment=solph.Investment(
                                                              ep_costs=
                                                              self.components_specific_costs['battery_inverter'][
                                                                  'capital_cost'],
                                                              existing=self.components_data['battery_inverter'][
                                                                  'existing_capacity']),
                                                              bidirectional=True)},
                                                      conversion_factors={
                                                          bus_ac: self.components_data['battery_inverter'][
                                                              'efficiency']})

        self.energysystem.add(battery, battery_inverter)

        # --- Model unsupplied load ---
        # dummy bus to connect unsupplied_demand GenericStorage block
        bus_unsupplied_demand = solph.buses.Bus(label='bus_unsupplied_demand')
        self.energysystem.add(bus_unsupplied_demand)

        if self.unsupplied_total_demand != 0:
            # Generic Storage block representing unsupplied total demand
            unsupplied_total_demand = solph.components.GenericStorage(label='unsupplied_total_demand_l',
                                                                      nominal_storage_capacity=self.unsupplied_total_demand,
                                                                      inputs={
                                                                          bus_unsupplied_demand: solph.flows.Flow()},
                                                                      outputs={
                                                                          bus_ac: solph.flows.Flow(variable_costs=0.1)},
                                                                      initial_storage_level=1,
                                                                      balanced=False)
            self.energysystem.add(unsupplied_total_demand)

        if self.unsupplied_pue_demand != 0:
            # Generic Storage block representing unsupplied pue demand
            unsupplied_pue_demand = solph.components.GenericStorage(label='unsupplied_pue_demand_l',
                                                                    nominal_storage_capacity=self.unsupplied_pue_demand,
                                                                    inputs={bus_unsupplied_demand: solph.flows.Flow()},
                                                                    outputs={bus_ac_pue: solph.flows.Flow(
                                                                        variable_costs=0.1)},
                                                                    initial_storage_level=1,
                                                                    balanced=False)
            self.energysystem.add(unsupplied_pue_demand)

        if self.unsupplied_household_demand != 0:
            # Generic Storage block representing unsupplied pue demand
            unsupplied_household_demand = solph.components.GenericStorage(label='unsupplied_household_demand_l',
                                                                          nominal_storage_capacity=self.unsupplied_household_demand,
                                                                          inputs={
                                                                              bus_unsupplied_demand: solph.flows.Flow()},
                                                                          outputs={bus_ac_household: solph.flows.Flow(
                                                                              variable_costs=0.1)},
                                                                          initial_storage_level=1,
                                                                          balanced=False)
            self.energysystem.add(unsupplied_household_demand)

        # --- Genset ---
        if self.components_data['genset']['exists'] != 0:
            # Create fuel bus
            bus_fuel = solph.buses.Bus(label='fuel_l')
            # Create fuel source
            fuel_source = solph.components.Source(label='fuel_l',
                                                  outputs={bus_fuel: solph.flows.Flow(
                                                      nominal_value=10 ** 100,  # Fuel supply is unlimited
                                                      summed_max=1)
                                                  })

            # create converter representing genset
            genset = solph.components.Converter(label='genset_l',
                                                inputs={bus_fuel: solph.flows.Flow(
                                                    variable_costs=self.components_specific_costs['genset'][
                                                        'variable_opex'])},
                                                outputs={bus_ac: solph.flows.Flow(
                                                    investment=solph.Investment(
                                                        ep_costs=self.components_specific_costs['genset'][
                                                            'capital_cost']
                                                    ))
                                                },
                                                conversion_factors={
                                                    bus_ac: self.components_data['genset']['efficiency']}, )
            self.energysystem.add(bus_fuel, fuel_source, genset)

        # ------------- Add peak power model ------------
        if self.peak_power_model:
            # -- Buses ---
            peak_ac_bus = solph.buses.Bus(label='peak_ac_bus_l')
            peak_dc_bus = solph.buses.Bus(label='peak_dc_bus_l')

            # bus representing "storage-side" of peak DC demand
            peak_dc_battery_storage_bus = solph.buses.Bus(label='peak_dc_battery_storage_bus')

            self.energysystem.add(peak_ac_bus, peak_dc_bus, peak_dc_battery_storage_bus)

            # -- Converters ---
            # Battery inverter
            peak_battery_inverter = solph.components.Converter(
                label='peak_battery_inverter_l',
                inputs={peak_dc_bus: solph.flows.Flow(bidirectional=True)},
                outputs={peak_ac_bus: solph.flows.Flow(
                    investment=solph.Investment(
                        ep_costs=1  # Cost can be dummy value -> as long as larger 0 it will be minimized
                    ),
                    bidirectional=True
                )}
            )

            # Converter representing peak power of battery storage -> to be linked to battery storage capacity
            peak_battery_storage = solph.components.Converter(
                label='peak_battery_storage_l',
                inputs={peak_dc_battery_storage_bus: solph.flows.Flow(bidirectional=True)},
                outputs={peak_dc_bus: solph.flows.Flow(
                    investment=solph.Investment(
                        ep_costs=1  # Cost can be dummy value -> as long as larger 0 it will be minimized
                    ),
                    bidirectional=True
                )}
            )

            self.energysystem.add(peak_battery_inverter, peak_battery_storage)

            # --- Sinks ---

            # Electricity peaks demand -> timeseries
            ac_peak_demand = solph.components.Sink(label='ac_peak_demand_l',
                                                   inputs={peak_ac_bus: solph.flows.Flow(
                                                       fix=self.timeseries['peak_power'],
                                                       nominal_value=self.peak_power_nominal)})

            # Sink representing battery inverter electricity base load
            # -> to be linked with dc-ac converter flow in the base model
            peak_battery_inverter_base_load = solph.components.Sink(label='peak_battery_inverter_base_load',
                                                                    inputs={peak_ac_bus: solph.flows.Flow(
                                                                        bidirectional=True)})

            self.energysystem.add(ac_peak_demand, peak_battery_inverter_base_load)

            # --- Sources ---
            # Unlimited "dummy" (slack) source for electricity peak demand
            # -> energy balance is calculated in original model
            peak_dc_source = solph.components.Source(label='peak_dc_source_l',
                                                     outputs={peak_dc_battery_storage_bus:
                                                                  solph.flows.Flow(bidirectional=True)})

            self.energysystem.add(peak_dc_source)

        print('initialise the operational model')
        # initialise the operational model
        self.om = solph.Model(self.energysystem)

        # --- Add custom constraints ---
        # https://oemof-solph.readthedocs.io/en/latest/reference/oemof.solph.constraints.html

        if self.peak_power_model:
            print('add constraints')
            # -- Equate battery inverter power flow with the base load representation in the peak demand model
            solph.constraints.equate_flows(
                self.om,
                [(battery_inverter, bus_ac)],
                [(peak_ac_bus, peak_battery_inverter_base_load)],
                name='battery_inverter_base_load_flow_link'
            )

            # -- Equate battery inverter's nominal power to be at least P_peak/peak_power_factor
            solph.constraints.equate_variables(
                self.om,
                self.om.InvestmentFlowBlock.invest[battery_inverter, bus_ac, 0],  # Nominal power bat inverter
                self.om.InvestmentFlowBlock.invest[peak_battery_inverter, peak_ac_bus, 0],  # Peak power bat inverter
                factor1=self.components_data['battery_inverter']['peak_power_ratio']
            )

            # -- Equate battery storage capacity to be at least 1/(C_rate * Peak_power_ratio)
            solph.constraints.equate_variables(
                self.om,
                self.om.GenericInvestmentStorageBlock.invest[battery, 0],  # Battery capacity (var_1)
                self.om.InvestmentFlowBlock.invest[peak_battery_storage, peak_dc_bus, 0],
                # Peak power bat inverter (var_2)
                factor1=self.components_data['battery_capacity']['c-rate'] * self.components_data['battery_capacity'][
                    'peak_power_ratio']  # var_1 * factor1 = var_2
            )

    def solve_energysystem(self):

        print('solve model')
        # if tee_switch is true solver messages will be displayed
        self.om.solve(solver='cbc')

        print('extract results')
        self.energysystem.results['main'] = solph.processing.results(self.om)
        self.energysystem.dump('./mg_model/oemof_results/', filename='mg_model.oemof')

    def extract_results(self, results, from_dump=False):
        """
        Process results from oemof solph
        :param results
        :param from_dump:
        :return:
        """

        results = solph.processing.convert_keys_to_strings(results, keep_none_type=True)

        # Extract component results
        results_pv = solph.views.node(results, 'pv_l')
        results_battery = solph.views.node(results, 'battery_l')
        results_battery_inverter = solph.views.node(results, 'battery_inverter_l')
        results_battery_inverter_peak_power = solph.views.node(results, 'peak_battery_inverter_l')

        if self.pv_east_west_exists:
            results_pv_east = solph.views.node(results, 'pv_east_l')
            results_pv_west = solph.views.node(results, 'pv_west_l')

        if self.components_data['genset']['exists'] != 0:
            results_genset = solph.views.node(results, 'genset_l')

        # Extract bus results
        results_ac_bus = solph.views.node(results, 'bus_ac_l')
        results_ac_pue_bus = solph.views.node(results, 'bus_ac_pue_l')
        results_ac_household_bus = solph.views.node(results, 'bus_ac_household_l')
        results_peak_ac_bus = solph.views.node(results, 'peak_ac_bus_l')

        # Collect components' capacities results
        results_components_capacities_dict = {
            'pv': {
                'capacity_invest': results_pv['scalars'][('pv_l', 'bus_ac_l'), 'invest'],
                'capacity_total': results_pv['scalars'][('pv_l', 'bus_ac_l'), 'total'],
            },
            'battery_capacity': {
                'capacity_invest': results_battery['scalars'][('battery_l', 'None'), 'invest'],
                'capacity_total': results_battery['scalars'][('battery_l', 'None'), 'total'],
            },
            'battery_inverter': {
                'capacity_invest': results_battery_inverter['scalars'][('battery_inverter_l', 'bus_ac_l'), 'invest'],
                'capacity_total': results_battery_inverter['scalars'][('battery_inverter_l', 'bus_ac_l'), 'total'],
            }
        }

        # east-west pv results if it is modelled
        if self.pv_east_west_exists:
            results_components_capacities_dict['pv_east'] = {
                'capacity_invest': results_pv_east['scalars'][('pv_east_l', 'bus_ac_l'), 'invest'],
                'capacity_total': results_pv_east['scalars'][('pv_east_l', 'bus_ac_l'), 'total'],
            }

            results_components_capacities_dict['pv_west'] = {
                'capacity_invest': results_pv_west['scalars'][('pv_west_l', 'bus_ac_l'), 'invest'],
                'capacity_total': results_pv_west['scalars'][('pv_west_l', 'bus_ac_l'), 'total'],
            }

        # Calculate economic results for each component
        results_components_costs_dict = {}
        for component, component_capacities in results_components_capacities_dict.items():
            results_components_costs_dict[component] = {
                'capex': self.components_specific_costs[component]['specific_capex'] * component_capacities[
                    'capacity_total'],
                'annuity': self.components_specific_costs[component]['annuity'] * component_capacities[
                    'capacity_total'],
                'fixed_opex': self.components_specific_costs[component]['fixed_opex'] * component_capacities[
                    'capacity_total'],
                'variable_opex': self.components_specific_costs[component]['variable_opex'] * 0
                # not considered for now TODO
            }

        # Transfer dicts to DataFrames
        self.results_components_capacities = pd.DataFrame(results_components_capacities_dict)
        self.results_components_costs = pd.DataFrame(results_components_costs_dict)

        self.results_components_costs.loc['total_annual_cost'] = (
            self.results_components_costs.loc[['annuity', 'fixed_opex', 'variable_opex']].sum(axis=0))

        # Sum components cost for total system cost
        self.results_components_costs['total'] = self.results_components_costs.sum(axis=1)

        # Extract resulting flows
        # Extract electricity component timeseries
        self.results_ac_flows = pd.concat([results_ac_bus['sequences'], results_ac_pue_bus['sequences'],
                                           results_ac_household_bus['sequences']], axis=1)

        # Add peak_power bus flows if peak_power_model exists
        if self.peak_power_model:
            self.results_ac_flows = pd.concat([self.results_ac_flows, results_peak_ac_bus['sequences']])

        self.results_ac_flows.columns = [x[0][0] + ' - ' + x[0][1] for x in
                                         self.results_ac_flows.columns]  # Remove tuple columns

        # Calculate and save system results (KPIs)
        # Sums of energy flows
        # For resolution other than 1h
        # Get modeled duration in hours
        model_dur = round((self.results_ac_flows.index.max() - self.results_ac_flows.index.min()).total_seconds()/3600)


        self.results_system = {
            'household_energy_delivered': self.results_ac_flows['bus_ac_l - ac_household_bus_link_l'].mean()*model_dur,
            'pue_energy_delivered': self.results_ac_flows['bus_ac_l - ac_pue_bus_link_l'].mean()*model_dur,
            'excess_energy': self.results_ac_flows['bus_ac_l - electricity_excess_l'].mean()*model_dur,
            'pv_potential_generation': self.results_ac_flows['pv_l - bus_ac_l'].mean()*model_dur,
            'battery_throughput': self.results_ac_flows['battery_inverter_l - bus_ac_l'].abs().mean()*model_dur / 2,
        }

        # Get maximum of peak power of battery inverter
        if self.peak_power_model:
            self.results_system['battery_inverter_peak_power_flow'] = self.results_ac_flows['peak_battery_inverter_l - peak_ac_bus_l'].max()

        self.results_system['total_energy_delivered'] = (self.results_system['household_energy_delivered'] +
                                                         self.results_system['pue_energy_delivered'])

        # Capacity factor = used (delivered energy) / potentially available energy
        self.results_system['capacity_factor'] = (self.results_system['total_energy_delivered'] /
                                                  self.results_system['pv_potential_generation'])

        self.results_system['LCOE'] = (self.results_components_costs['total']['total_annual_cost'] /
                                       self.results_system['total_energy_delivered']) * model_dur/8760
