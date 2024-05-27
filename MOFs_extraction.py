import csv
from ccdc.io import EntryReader, Subsets

# List of properties to extract
properties = [
    "calculated_density",
    "ccdc_number",
    "chemical_name_as_html",
    "predicted_properties",
    "semiconductor_properties",
    "journal_list",
    "cell_angles",
    "cell_lengths",
    "cell_volume",
    "z_prime",
    "spacegroup_symbol",
    "packing_coefficient",
    "void_volume",
    "molecular_shape_descriptor",
    "hydrogen_bonds",
    "peptide_sequence",
    "phase_transition",
    "previous_identifier",
    "publications",
    "r_factor",
    "solubility_data",
    "solvent",
    "source",
    "synonyms_as_html",
    "to_string",
    "journals",
    "bfdh_form",
    "organic_semi_conductor_properties",
    "analogue",
    "component_inchis",
    "disordered_molecule",
    "molecule",
    "temperature",
    "formatted_melting_point_range",
    "formatted_melting_point_text",
    "identifier",
    "chemical_name",
    "formula",
    "color",
    "melting_point",
    "polymorph",
    "disorder_details",
    "radiation_source",
    "deposition_date",
    "remarks",
    "pressure",
    "is_powder_study",
    "cross_references",
    "journal",
    "publication",
    "three_d_structure",
    "disorder",
    "is_organometallic",
    "is_polymeric",
    "bioactivity",
    "synonyms",
    "component_inchis",
    "crystal",
    "database_name",
    "habit",
    "heat_capacity",
    "heat_capacity_notes",
    "heat_of_fusion",
    "heat_of_fusion_notes",
    "solubility",
    "solubility_notes",
    "solvents",
    "intermolecular",
    "observations",
    "max_distance",
    "min_angle",
    "usual_distance_lower_quantile",
    "usual_distance_upper_quantile",
    "usual_angle_lower_quantile",
    "has_three_d_structure",
    "cross_references",
]


def extract_property(entry, prop):
    try:
        value = getattr(entry, prop, "")
        if callable(value):
            value = value()
        return value
    except (AttributeError, RuntimeError):
        return ""


def extract_mof_properties(n):
    # Initialize CSD connection and read MOF subset
    mof_reader = EntryReader(subset=Subsets.MOF)

    # Open a CSV file to write the data with UTF-8 encoding
    with open('mof_properties.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['refcode'] + properties
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Iterate through the MOF entries and extract properties
        for i, entry in enumerate(mof_reader):
            if i >= n:
                break
            row = {'refcode': entry.identifier}
            row['calculated_density'] = extract_property(entry.crystal, 'calculated_density')
            row['ccdc_number'] = extract_property(entry, 'ccdc_number')
            row['chemical_name_as_html'] = extract_property(entry, 'chemical_name_as_html')
            row['predicted_properties'] = extract_property(entry, 'predicted_properties')
            row['semiconductor_properties'] = extract_property(entry, 'semiconductor_properties')
            row['journal_list'] = extract_property(entry, 'journal_list')
            row['cell_angles'] = extract_property(entry.crystal, 'cell_angles')
            row['cell_lengths'] = extract_property(entry.crystal, 'cell_lengths')
            row['cell_volume'] = extract_property(entry.crystal, 'cell_volume')
            row['z_prime'] = extract_property(entry.crystal, 'z_prime')
            row['spacegroup_symbol'] = extract_property(entry.crystal, 'spacegroup_symbol')
            row['packing_coefficient'] = extract_property(entry.crystal, 'packing_coefficient')
            row['void_volume'] = extract_property(entry.crystal, 'void_volume')
            row['molecular_shape_descriptor'] = extract_property(entry, 'molecular_shape_descriptor')
            row['hydrogen_bonds'] = extract_property(entry.crystal, 'hydrogen_bonds')
            row['peptide_sequence'] = extract_property(entry, 'peptide_sequence')
            row['phase_transition'] = extract_property(entry, 'phase_transition')
            row['previous_identifier'] = extract_property(entry, 'previous_identifier')
            row['publications'] = extract_property(entry, 'publications')
            row['r_factor'] = extract_property(entry, 'r_factor')
            row['solubility_data'] = extract_property(entry, 'solubility_data')
            row['solvent'] = extract_property(entry, 'solvent')
            row['source'] = extract_property(entry, 'source')
            row['synonyms_as_html'] = extract_property(entry, 'synonyms_as_html')
            row['to_string'] = str(entry)  # Using str(entry) as an equivalent for to_string
            row['journals'] = extract_property(entry, 'journals')
            row['bfdh_form'] = extract_property(entry, 'bfdh_form')
            row['organic_semi_conductor_properties'] = extract_property(entry, 'organic_semi_conductor_properties')
            row['analogue'] = extract_property(entry, 'analogue')
            row['component_inchis'] = extract_property(entry, 'component_inchis')
            row['disordered_molecule'] = extract_property(entry.crystal, 'disordered_molecule')
            row['molecule'] = extract_property(entry, 'molecule')
            row['temperature'] = extract_property(entry, 'temperature')
            row['formatted_melting_point_range'] = extract_property(entry, 'formatted_melting_point_range')
            row['formatted_melting_point_text'] = extract_property(entry, 'formatted_melting_point_text')
            row['identifier'] = extract_property(entry, 'identifier')
            row['chemical_name'] = extract_property(entry, 'chemical_name')
            row['formula'] = extract_property(entry.crystal, 'formula')
            row['color'] = extract_property(entry, 'color')
            row['melting_point'] = extract_property(entry, 'melting_point')
            row['polymorph'] = extract_property(entry, 'polymorph')
            row['disorder_details'] = extract_property(entry, 'disorder_details')
            row['radiation_source'] = extract_property(entry, 'radiation_source')
            row['deposition_date'] = extract_property(entry, 'deposition_date')
            row['remarks'] = extract_property(entry, 'remarks')
            row['pressure'] = extract_property(entry, 'pressure')
            row['is_powder_study'] = extract_property(entry, 'is_powder_study')
            row['cross_references'] = extract_property(entry, 'cross_references')
            row['journal'] = extract_property(entry, 'journal')
            row['publication'] = extract_property(entry, 'publication')
            row['three_d_structure'] = extract_property(entry, 'three_d_structure')
            row['disorder'] = extract_property(entry.crystal, 'disorder')
            row['is_organometallic'] = extract_property(entry, 'is_organometallic')
            row['is_polymeric'] = extract_property(entry, 'is_polymeric')
            row['bioactivity'] = extract_property(entry, 'bioactivity')
            row['synonyms'] = extract_property(entry, 'synonyms')
            row['component_inchis'] = extract_property(entry, 'component_inchis')
            row['crystal'] = extract_property(entry, 'crystal')
            row['database_name'] = extract_property(entry, 'database_name')
            row['habit'] = extract_property(entry, 'habit')
            row['heat_capacity'] = extract_property(entry, 'heat_capacity')
            row['heat_capacity_notes'] = extract_property(entry, 'heat_capacity_notes')
            row['heat_of_fusion'] = extract_property(entry, 'heat_of_fusion')
            row['heat_of_fusion_notes'] = extract_property(entry, 'heat_of_fusion_notes')
            row['solubility'] = extract_property(entry, 'solubility')
            row['solubility_notes'] = extract_property(entry, 'solubility_notes')
            row['solvents'] = extract_property(entry, 'solvents')
            row['intermolecular'] = extract_property(entry, 'intermolecular')
            row['observations'] = extract_property(entry, 'observations')
            row['max_distance'] = extract_property(entry, 'max_distance')
            row['min_angle'] = extract_property(entry, 'min_angle')
            row['usual_distance_lower_quantile'] = extract_property(entry, 'usual_distance_lower_quantile')
            row['usual_distance_upper_quantile'] = extract_property(entry, 'usual_distance_upper_quantile')
            row['usual_angle_lower_quantile'] = extract_property(entry, 'usual_angle_lower_quantile')
            row['has_three_d_structure'] = extract_property(entry, 'has_three_d_structure')
            row['cross_references'] = extract_property(entry, 'cross_references')

            writer.writerow(row)

    print(f"MOF properties extraction completed for {n} entries and saved to mof_properties.csv.")


# Example usage: extract properties for 100 MOF entries
extract_mof_properties(20)
