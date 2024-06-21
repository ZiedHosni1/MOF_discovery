# For example, we might want to remove unnecessary waters, metals and ligands to prepare the protein for docking
for metal in p_1fax.metals:
    p_1fax.remove_metal(metal)

for ligand in p_1fax.ligands:
    p_1fax.remove_ligand(ligand.identifier)

p_1fax.remove_all_waters()
p_1fax.remove_chain('L')

# add all hydrogen atoms.
p_3cen.add_hydrogens()

# it is preferrable to have all the atoms in a given residue in a single block of atoms.
p_3cen.sort_atoms_by_residue()

#GOLD docking in API (a list from CCDC)
flip_planar_nitrogen
flip_free_corners
flip_amide_bonds
flip_pyramidal_nitrogen
save_lone_pairs
match_template_conformations
rotate_carboxylic_hydroxyl_groups
use_torsion_angle_distributions
fix_ligand_rotatable_bond
rotatable_bond_override_file
fix_all_protein_rotatable_bonds
solvate_all
use_internal_ligand_energy_offset

#proteinRotatedTorsion
class ProteinRotatedTorsion(object):
    '''Details of a protein amino acid side chain rotated in the docking solution.'''

    def __init__(self, protein_rotated_torsion_sd_tag):
        '''Construct from the contents of a Gold.Protein.RotatedTorsions solution file SD tag.

        :param protein_rotated_torsion_sd_tag: the docked ligand Gold.Protein.RotatedTorsions SD tag string.
        '''
        self._gold_rotated_torsion = DockingLib.GoldRotatedTorsion(protein_rotated_torsion_sd_tag)
        self._type_map = {DockingLib.GoldRotatedTorsion.SIDE_CHAIN: "sidechain",
                          DockingLib.GoldRotatedTorsion.ROTATED_H: "rotated_h",
                          DockingLib.GoldRotatedTorsion.UNKNOWN: "unknown"}

    @property
    def name(self):
        return self._gold_rotated_torsion.name()

    @property
    def chi_number(self):
        '''The flexible sidechain chi number or -1 if this torsion is not part of a RotamerLibrary.'''
        chi_index_str = self._gold_rotated_torsion.chi_number()
        if chi_index_str == "":
            return -1
        return int(chi_index_str)

    @property
    def input_angle(self):
        '''The torsion angle in the protein before docking.'''
        return float(self._gold_rotated_torsion.input_angle())

    @property
    def final_angle(self):
        '''The torsion angle in the final pose.'''
        return float(self._gold_rotated_torsion.final_angle())

    @property
    def atom_indices(self):
        '''The file order index of each atom in the torsion.'''
        return list(self._gold_rotated_torsion.atoms())

    @property
    def type(self):
        '''The torsion type as a string.

        "sidechain" : a torsion in a residue sidechain as defined in a rotamer library.
        "rotated_h" : a residue terminal rotatable hydrogen e.g. in a SER, THR, TYR hydroxyl or LYS NH3.
        "unknown" : type not set, should not usually be encountered.

        :return string representation of the protein rotated torsion type.
        '''

        return self._type_map[self._gold_rotated_torsion.type()]

# Docking results
@nested_class('Docker')
    class Results(object):
        '''Docking results.
        '''

[docs]        class DockedLigand(Entry):
            '''Subclass of :class:`ccdc.entry.Entry` to provide nicer access to the scoring terms of the docking.
            '''

            def __init__(self, entry, settings):
                self._entry = entry._entry
                self.attributes = entry.attributes
                self.settings = settings

            @staticmethod
            def _is_float(t):
                try:
                    x = float(t)
                    return True
                except ValueError:
                    return False

[docs]            def fitness(self, fitness_function=None):
                '''The recorded fitness of a docking.

                :param fitness_function: one of the fitness functions of the :class:`ccdc.docking.Docker.Settings` or ``None``.

                If the docking has exactly one fitness attribute, *i.e.*, no rescoring has been performed, then there is
                no need to specify the fitness_function.
                '''
                possibles = [(k, float(v)) for k, v in self.attributes.items() if
                             'fitness' in k.lower() and self._is_float(v)]
                if len(possibles) == 0:
                    raise RuntimeError('No fitness term in the entry')
                terms = [
                    k.split('.')[1].lower() for k, v in possibles
                ]
                if fitness_function is None:
                    if len(possibles) == 1:
                        return possibles[0][1]
                    else:
                        raise RuntimeError('Fitness terms for %s in entry' % ', '.join(terms))
                else:
                    matched = [(k, v) for k, v in possibles if fitness_function.lower() in k.lower()]
                    if len(matched) == 0:
                        raise RuntimeError('No matching fitness term.  Available are %s' % (', ').join(terms))
                    elif len(matched) == 1:
                        return matched[0][1]
                    else:
                        raise RuntimeError('Multiple matching fitness terms, %s' % ', '.join(k for k, v in matched))


[docs]            def scoring_term(self, *filters):
                '''Individual or dicts of scoring terms from the entry.

                :param fitness_function: any of the fitness functions of :class:`ccdc.docking.Settings`
                :param `*filters`: an iterable of additional constraints to put on the name of the term.
                :returns: a float if the specification is exact or a dictionary of key:float if ambiguous.
                '''
                terms = [(k, float(v)) for k, v in self.attributes.items() if self._is_float(v)]
                terms = [(k, v) for k, v in terms if all(x.lower() in k.lower() for x in filters)]
                if len(terms) == 0:
                    raise RuntimeError('No scoring term matched')
                elif len(terms) == 1:
                    return terms[0][1]
                else:
                    return dict(terms)

#settings for the docker
@nested_class('Docker')
    class Settings(object):
        '''Settings for docker.'''
        _fitness_functions = ['goldscore', 'chemscore', 'asp', 'plp']

        @classmethod
        def _path_in_distribution(self, value):
            if 'GOLD_DIR' in os.environ:
                file_name = os.path.join(os.environ['GOLD_DIR'], 'gold', value)
                if not os.path.exists(file_name):
                    file_name = os.path.join(os.environ['GOLD_DIR'], value)
            elif 'MAINDIR' in os.environ:
                file_name = os.path.join(os.environ['MAINDIR'], '..', 'goldsuite', 'gold_dist', 'gold', value)
            else:
                file_name = value
            return file_name
