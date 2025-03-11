"""
helper function to write output files and extract relevant information into results.yml format.
"""
import sys
from typing import Any, Dict, List

import yaml
import re
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import math


class get_result_from:
    @staticmethod
    def QPParametrizer(local_result: Dict[str, Any], mol_data_yml: str) -> None:
        """
        mol_data_yml: mol_data.yml, QPParametrizer output.
        local_result: template result.yml from /opt/tmpl/ folders.

        The field in "mol_data.yml" will be copied to result.yaml (local_result) if both conditions are met:
        1. the field exists in "mol_data.yml"
        2. the field exists in "opt/tmpl/QPParametrizer_*/result.yml"
        """

        def get_dipole_value_from_vector(vector_dipole: List):
            return float(np.sqrt(vector_dipole[0] ** 2 + vector_dipole[1] ** 2 + vector_dipole[2] ** 2))

        with open(mol_data_yml, 'r') as file:
            mol_data = yaml.safe_load(file)

        if 'homo energy' in mol_data and 'HOMO' in local_result:
            local_result['HOMO']['value'] = mol_data['homo energy']

        if 'lumo energy' in mol_data and 'LUMO' in local_result:
            local_result['LUMO']['value'] = mol_data['lumo energy']

        if 'dipole' in mol_data and 'dipole' in local_result:
            dipole_value = get_dipole_value_from_vector(mol_data['dipole'])
            local_result['dipole']['value'] = dipole_value
            local_result['dipole']['results']['dipole_vector'] = mol_data['dipole']

        # all excitation energies. Map: Excitation energy <n> => E(S<n+1>)
        for key, value in mol_data.items():
            if key.startswith("Excitation energy "):
                index = key.split()[-1]
                s_key = f"E(S{index})"
                if s_key in local_result:
                    local_result[s_key] = value

        # total energy
        if 'total_energy' in mol_data and 'total_energy' in local_result:
            local_result['total_energy']['value'] = mol_data['total_energy']

    @staticmethod
    def Deposit(local_result: Dict[str, Any], filepath: str) -> None:
        with open(filepath, 'r') as file:
            text = file.read()

        # More relaxed regular expression to match the desired patterns

        box_density_pattern = re.compile(
            r'box density avg over 20 samples:\s*([\d.]+(?:[eE][+-]?\d+)?)\s.*?\s([\d.]+(?:[eE][+-]?\d+)?)')  # output style of DensityAnalysis is error prone and hard to parse.

        volume_pattern = re.compile(r'molecular volume in nm3: ([\d.]+)')
        rdf_peak_pattern = re.compile(r'First peak in RDF: ([\d.]+)')
        neighbors_pattern = re.compile(r'Avergae neighbors of 80d0 around central 80d0: ([\d.]+)')

        # Extracting mass density and number density
        box_density_matches = box_density_pattern.findall(text)
        if box_density_matches:
            # First match is the mass density
            mass_density_match = box_density_matches[0]
            local_result["morphology"]["results"]["mass_density"]["value"] = float(mass_density_match[0])
            local_result["morphology"]["results"]["mass_density"]["std"] = float(mass_density_match[1])

            # Second match is the number density (if available)
            if len(box_density_matches) > 1:
                number_density_match = box_density_matches[1]
                local_result["morphology"]["results"]["number_density"]["value"] = float(number_density_match[0])
                local_result["morphology"]["results"]["number_density"]["std"] = float(number_density_match[1])

        # Extracting molecular volume
        volume_match = volume_pattern.search(text)
        if volume_match:
            local_result["morphology"]["results"]["molecular_volume"]["value"] = float(volume_match.group(1))

        # Extracting first peak in RDF
        rdf_peak_match = rdf_peak_pattern.search(text)
        if rdf_peak_match:
            local_result["morphology"]["results"]["rdf_first_peak"]["value"] = float(rdf_peak_match.group(1))

        # Extracting average neighbors
        neighbors_match = neighbors_pattern.search(text)
        if neighbors_match:
            local_result["morphology"]["results"]["average_neighbors"]["value"] = float(neighbors_match.group(1))

    @staticmethod
    def lightforge(local_result: Dict[str, Any], mobilities_file: str, settings_file: str, hole_or_electron: str) -> None:

        if hole_or_electron not in ['hole', 'electron']:
            sys.exit(f'hole_or_electron may be either "hole" or "electron". It is: {hole_or_electron}. Exiting . . . ')

        # Read data from mobilities_all_fields.dat
        fields = []
        mobilities = []
        stderrs = []

        with open(mobilities_file, 'r') as file:
            for line in file:
                parts = line.split()
                fields.append(float(parts[0]))
                mobilities.append(float(parts[1]))
                stderrs.append(float(parts[2]))

        # Read the number of simulations (samples) from the settings YAML file
        with open(settings_file, 'r') as file:
            settings = yaml.safe_load(file)
            num_samples = settings['experiments'][0]['simulations']

        # Fill in the local_result dictionary

        hole_or_electron_mobility = f'{hole_or_electron}_mobility'

        local_result[hole_or_electron_mobility]["results"]["fields"]["values"] = list(fields)
        local_result[hole_or_electron_mobility]["results"]["mobilities"]["values"] = list(mobilities)

        # Calculate standard error
        stderr_values = [float(std / np.sqrt(num_samples)) for std in stderrs]
        local_result[hole_or_electron_mobility]["results"]["stderr"]["values"] = list(stderr_values)

        # Perform linear regression to find the zero-field mobility
        sqrt_fields = np.sqrt(fields).reshape(-1, 1)
        log_mobilities = np.log(mobilities).reshape(-1, 1)

        model = LinearRegression()
        model.fit(sqrt_fields, log_mobilities)
        log_zero_field_mobility = model.intercept_[0]
        zero_field_mobility = np.exp(log_zero_field_mobility)

        # Set the zero-field mobility in the local_result dictionary
        local_result[hole_or_electron_mobility]["value"] = float(zero_field_mobility)

        # Plotting the data and the regression line
        plt.figure()
        plt.errorbar(sqrt_fields, mobilities, yerr=stderr_values, fmt='k.', label='Data')
        plt.yscale('log')
        plt.xlabel(r'$\sqrt{\mathrm{field}}$ $(\mathrm{V/cm})^{0.5}$')
        plt.ylabel(r'$\mathrm{mobility}$ $(\mathrm{cm^2/Vs})$')

        # Generate points for the regression line
        sqrt_field_range = np.linspace(0, sqrt_fields.max(), 100).reshape(-1, 1)
        log_mobility_pred = model.predict(sqrt_field_range)
        mobility_pred = np.exp(log_mobility_pred)

        plt.plot(sqrt_field_range, mobility_pred, 'r-', label='Regression line')

        # Mark the zero-field mobility point
        plt.plot(0, zero_field_mobility, 'bo', label=f'Zero-field mobility: {zero_field_mobility:.2e}')

        plt.legend()
        plt.savefig(f'{hole_or_electron}_mobility_vs_sqrt_field.png')
        # plt.show()

    @staticmethod
    def QPAnalyzeStokesShift(local_result, results_yml):
        
        with open(results_yml, 'r') as file:
            results_yml_dict = yaml.safe_load(file)

        stokes_shift_results = results_yml_dict['Stokes shift results:']
        if 'Stokes shift in eV::' in stokes_shift_results:
            local_result['StokesShift']['value'] = stokes_shift_results['Stokes shift in eV::']
            local_result['StokesShift']['results']['Stokes shift in eV'] = stokes_shift_results['Stokes shift in eV::']
        if 'Stokes shift in eV::' in stokes_shift_results:
            local_result['StokesShift']['results']['Stokes shift in nm'] = stokes_shift_results['Stokes shift in nm::']
        if 'Excitation energy S0-S1 (S0 opt geometry) in eV:' in stokes_shift_results and 'results' in local_result.get('StokesShift'):
            local_result['StokesShift']['results']['E(S1,S0_opt) in eV'] = stokes_shift_results['Excitation energy S0-S1 (S0 opt geometry) in eV:']
            local_result['StokesShift']['results']['E(S1,S0_opt) in nm'] = stokes_shift_results['Excitation energy S0-S1 (S0 opt geometry) in nm:']
            local_result['StokesShift']['results']['E(S1,S1_opt) in eV'] = stokes_shift_results['Excitation energy S0-S1 (S1 opt geometry) in eV:']
            local_result['StokesShift']['results']['E(S1,S1_opt) in nm'] = stokes_shift_results['Excitation energy S0-S1 (S1 opt geometry) in nm:']