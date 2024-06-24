import os
from ccdc.io import CrystalReader, CrystalWriter
from ccdc.utilities import _private_importer

# Import necessary modules from CCDC library
with _private_importer() as pi:
    pi.import_ccdc_module('UtilitiesLib')
    pi.import_ccdc_module('MathsLib')
    pi.import_ccdc_module('ChemistryLib')


# Define a packing function
def packing(self, box_dimensions=((0, 0, 0), (1, 1, 1)), inclusion='CentroidIncluded'):
    csv = ChemistryLib.CrystalStructureView_instantiate(self._csv)
    psv = ChemistryLib.CrystalStructurePackingView(csv)
    if psv.packable():
        csv.set_inclusion_condition(self._decode_inclusion(inclusion))
        box = MathsLib.Box(box_dimensions[0], box_dimensions[1])
        psv.set_packing_box(box)
        psv.set_packing(True)
    else:
        raise RuntimeError('The crystal is not packable.')
    mol = ChemistryLib.Molecule3d_instantiate()
    for i in range(csv.nmolecules()):
        mol.add(csv.molecule(i))
    return Molecule(self.identifier, _molecule=mol)

# Define the path to your CIF input and output files
input_cif_file_path = 'C:\\Users\\juice\\PycharmProjects\\MOF_discovery_Zyiao_2\\packing\\FAWCEN03.cif'
output_cif_file_path = 'packed_structure.cif'

# Ensure the CIF input file exists
if not os.path.isfile(input_cif_file_path):
    raise FileNotFoundError(f"The CIF file at {input_cif_file_path} does not exist.")

# Load your crystal structure from the CIF file
with CrystalReader(input_cif_file_path) as reader:
    crystal = reader[0]

# Perform the packing operation
packed_crystal = packing(crystal)

# Save the packed structure to a CIF file
with CrystalWriter(output_cif_file_path) as writer:
    writer.write(packed_crystal)

print(f"Packed structure saved to {output_cif_file_path}")

