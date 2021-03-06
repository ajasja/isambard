"""Defines various containers for AMPAL objects."""

from collections import Counter
import itertools

from ampal.base_ampal import BaseAmpal, Polymer, find_atoms_within_distance
from ampal.ligands import LigandGroup, Ligand
from ampal.analyse_protein import sequence_molecular_weight, sequence_molar_extinction_280, \
    sequence_isoelectric_point
from buff import find_intra_ampal, find_inter_ampal, score_interactions
from external_programs.scwrl import pack_sidechains
from external_programs.naccess import run_naccess, extract_residue_accessibility
from settings import global_settings


class AmpalContainer(object):
    """Custom list type class that holds multiple model states.

    Notes
    -----
    In this case, a state is defined as a set of coordinates that
    represents a protein model and an associated score or set of scores.

    Parameters
    ----------
    ampal_objects : [AMPAL], optional
        A list of AMPAL objects with which to initialise the
        AMPAL container. This can be an `Assembly`, `Polymer`
        or `Monomer`.
    id : str, optional
        Identifier for the AMPAL container.

    Attributes
    ----------
    id : str
        Identifier for the AMPAL container.
    """

    def __init__(self, ampal_objects=None, id=None):
        self.id = 'AMPAL Container' if not id else id
        if ampal_objects:
            self._ampal_objects = ampal_objects
        else:
            self._ampal_objects = []

    def __add__(self, other):
        """Merges two `AmpalContainers`.

        Notes
        -----
        Generates new `AmpalContainer`.
        """
        if isinstance(other, AmpalContainer):
            merged_ac = self._ampal_objects[:] + other._ampal_objects[:]
        else:
            raise TypeError(
                'Only AmpalContainer objects may be merged with an '
                'AmpalContainer using unary operator "+".')
        return AmpalContainer(ampal_objects=merged_ac)

    def __repr__(self):
        return "<AmpalContainer ({}) containing {} AMPAL Objects>".format(
            self.id, len(self._ampal_objects))

    def __len__(self):
        return len(self._ampal_objects)

    def __getitem__(self, item):
        if isinstance(item, str):
            id_dict = {p.id.split('_')[-1]: p for p in self._ampal_objects}
            return id_dict[item]
        elif isinstance(item, int):
            return self._ampal_objects[item]
        else:
            return AmpalContainer(self._ampal_objects[item])

    def append(self, item):
        """Adds an AMPAL object to the `AmpalContainer`."""
        self._ampal_objects.append(item)
        return

    def extend(self, ampal_container):
        """Extends an `AmpalContainer` with another `AmpalContainer`."""
        if isinstance(ampal_container, AmpalContainer):
            self._ampal_objects.extend(ampal_container)
        else:
            raise TypeError(
                'Only AmpalContainer objects may be merged with '
                'an AmpalContainer.')
        return

    @property
    def pdb(self):
        """Compiles the PDB strings for each state into a single file."""
        header_title = '{:<80}\n'.format('HEADER    {}'.format(self.id))
        data_type = '{:<80}\n'.format('EXPDTA    ISAMBARD Model')
        pdb_strs = []
        for ampal in self:
            if isinstance(ampal, Assembly):
                pdb_str = ampal.make_pdb(header=False, footer=False)
            else:
                pdb_str = ampal.make_pdb()
            pdb_strs.append(pdb_str)
        merged_strs = 'ENDMDL\n'.join(pdb_strs) + 'ENDMDL\n'
        merged_pdb = ''.join([header_title, data_type, merged_strs])
        return merged_pdb

    def sort_by_tag(self, tag):
        """Sorts the `AmpalContainer` by a tag on the component objects.

        Parameters
        ----------
        tag : str
            Key of tag used for sorting.
        """
        return AmpalContainer(sorted(self, key=lambda x: x.tags[tag]))


class Assembly(BaseAmpal):
    """A container that holds `Polymer` type objects.

    Notes
    -----
    Has a simple hierarchy: `Assembly` contains one or more `Polymer`,
    which in turn contains one or more `Monomer`.

    Parameters
    ----------
    molecules : Polymer or [Polymer], optional
        `Polymer` or list containing `Polymer` objects to be assembled.
    assembly_id : str, optional
        An ID that the user can use to identify the `Assembly`. This
        is used when generating a pdb file using `Assembly().pdb`.

    Raises
    ------
    TypeError
        `Assembly` objects can only be initialised empty, using a `Polymer`
        or a list of `Polymers`.
    """

    def __init__(self, molecules=None, assembly_id=''):
        if molecules:
            if isinstance(molecules, Polymer):
                self._molecules = [molecules]
            elif isinstance(molecules, list) and isinstance(molecules[0], Polymer):
                self._molecules = list(molecules)
            else:
                raise TypeError(
                    'Assembly objects can only be initialised empty, using '
                    'a Polymer or a list of Polymers.')
        else:
            self._molecules = []
        self.id = str(assembly_id)
        self.tags = {}

    def __add__(self, other):
        """Merges together two `Assemblies`.

        Raises
        ------
        TypeError
            Raised if other is any type other than `Assembly`.
        """
        if isinstance(other, Assembly):
            merged_assembly = self._molecules[:] + other._molecules[:]
        else:
            raise TypeError(
                'Only Assembly objects may be merged with an Assembly using '
                'unary operator "+".')
        return Assembly(molecules=merged_assembly, assembly_id=self.id)

    def __len__(self):
        return len(self._molecules)

    def __getitem__(self, item):
        if isinstance(item, str):
            id_dict = {str(p.id): p for p in self._molecules}
            return id_dict[item]
        elif isinstance(item, int):
            return self._molecules[item]
        else:
            return Assembly(self._molecules[item], assembly_id=self.id)

    def __repr__(self):
        repr_strs = []
        mol_types = Counter([x.molecule_type for x in self._molecules])
        if 'protein' in mol_types:
            repr_strs.append('{} {}'.format(
                mol_types['protein'],
                'Polypeptide' if len(self._molecules) == 1 else 'Polypeptides'))
        if 'nucleic_acid' in mol_types:
            repr_strs.append('{} {}'.format(
                mol_types['nucleic_acid'],
                'Polynucleotide' if len(self._molecules) == 1 else 'Polynucleotides'))
        ligand_count = 0
        if 'ligands' in mol_types:
            repr_strs.append('{} {}'.format(
                mol_types['ligands'],
                'Ligand Group' if len(self._molecules) == 1 else 'Ligand Groups'))
        for mol in self._molecules:
            if mol.molecule_type == 'ligands':
                ligand_count += len(mol)
            else:
                ligand_count += 0 if not mol.ligands else len(mol.ligands)
        if ligand_count:
            repr_strs.append('{} {}'.format(
                ligand_count, 'Ligand' if ligand_count == 1 else 'Ligands'))
        if 'pseudo_group' in mol_types:
            repr_strs.append('{} {}'.format(
                mol_types['pseudo_group'],
                'Pseudo Group' if len(self._molecules) == 1 else 'Pseudo Groups'))
        id_str = '' if not self.id else '({}) '.format(self.id)
        return '<Assembly {}containing {}>'.format(id_str, ', '.join(repr_strs))

    def append(self, item):
        """Adds a `Polymer` to the `Assembly`.

        Raises
        ------
        TypeError
            Raised if other is any type other than `Polymer`.
        """
        if isinstance(item, Polymer):
            self._molecules.append(item)
        else:
            raise TypeError(
                'Only Polymer objects can be appended to an Assembly.')
        return

    def extend(self, assembly):
        """Extends the `Assembly` with the contents of another `Assembly`.

        Raises
        ------
        TypeError
            Raised if other is any type other than `Assembly`.
        """
        if isinstance(assembly, Assembly):
            self._molecules.extend(assembly)
        else:
            raise TypeError(
                'Only Assembly objects may be merged with an Assembly.')
        return

    def get_monomers(self, ligands=True, pseudo_group=False):
        """Retrieves all the `Monomers` from the `Assembly` object.

        Parameters
        ----------
        ligands : bool, optional
            If `true`, will include ligand `Monomers`.
        pseudo_group : bool, optional
            If `True`, will include pseudo atoms.
        """
        base_filters = dict(ligands=ligands, pseudo_group=pseudo_group)
        restricted_mol_types = [x[0] for x in base_filters.items() if not x[1]]
        in_groups = [x for x in self.filter_mol_types(restricted_mol_types)]
        monomers = itertools.chain(
            *(p.get_monomers(ligands=ligands) for p in in_groups))
        return monomers

    def get_ligands(self, solvent=True):
        """Retrieves all ligands from the `Assembly`.

        Parameters
        ----------
        solvent : bool, optional
            If `True`, solvent molecules will be included.
        """
        if solvent:
            ligand_list = [x for x in self.get_monomers()
                           if isinstance(x, Ligand)]
        else:
            ligand_list = [x for x in self.get_monomers() if isinstance(
                x, Ligand) and not x.is_solvent]
        return LigandGroup(monomers=ligand_list)

    def get_atoms(self, ligands=True, pseudo_group=False, inc_alt_states=False):
        """ Flat list of all the `Atoms` in the `Assembly`.

        Parameters
        ----------
        ligands : bool, optional
            Include ligand `Atoms`.
        pseudo_group : bool, optional
            Include pseudo_group `Atoms`.
        inc_alt_states : bool, optional
            Include alternate sidechain conformations.

        Returns
        -------
        atoms : itertools.chain
            All the `Atoms` as a iterator.
        """
        atoms = itertools.chain(
            *(list(m.get_atoms(inc_alt_states=inc_alt_states))
                for m in self.get_monomers(ligands=ligands,
                                           pseudo_group=pseudo_group)))
        return atoms

    def is_within(self, cutoff_dist, point, ligands=True):
        """Returns all atoms in AMPAL object within `cut-off` distance from the `point`."""
        return find_atoms_within_distance(self.get_atoms(ligands=ligands), cutoff_dist, point)

    def relabel_all(self):
        """Relabels all Polymers, Monomers and Atoms with default labeling."""
        self.relabel_polymers()
        self.relabel_monomers()
        self.relabel_atoms()
        return

    def relabel_polymers(self, labels=None):
        """Relabels the component Polymers either in alphabetical order or using a list of labels.

        Parameters
        ----------
        labels : list, optional
            A list of new labels.

        Raises
        ------
        ValueError
            Raised if the number of labels does not match the number of component Polymer objects.
        """
        if labels:
            if len(self._molecules) == len(labels):
                for polymer, label in zip(self._molecules, labels):
                    polymer.id = label
            else:
                raise ValueError('Number of polymers ({}) and number of labels ({}) must be equal.'.format(
                    len(self._molecules), len(labels)))
        else:
            for i, polymer in enumerate(self._molecules):
                polymer.id = chr(i + 65)
        return

    def relabel_monomers(self):
        """Relabels all Monomers in the component Polymers in numerical order."""
        for polymer in self._molecules:
            polymer.relabel_monomers()
        return

    def relabel_atoms(self, start=1):
        """Relabels all Atoms in numerical order, offset by the start parameter.

        Parameters
        ----------
        start : int, optional
            Defines an offset for the labelling.
        """
        counter = start
        for atom in self.get_atoms(ligands=True):
            atom.id = counter
            counter += 1
        return

    @property
    def pdb(self):
        """Runs make_pdb in default mode."""
        return self.make_pdb()

    def make_pdb(self, ligands=True, alt_states=False, pseudo_group=False, header=True, footer=True):
        """Generates a PDB string for the Assembly.

        Parameters
        ----------
        ligands : bool, optional
            If `True`, will include ligands in the output.
        alt_states : bool, optional
            If `True`, will include alternate conformations in the output.
        pseudo_group : bool, optional
            If `True`, will include pseudo atoms in the output.
        header : bool, optional
            If `True` will write a header for output.
        footer : bool, optional
            If `True` will write a footer for output.

        Returns
        -------
        pdb_str : str
            String of the pdb for the Assembly. Generated by collating
            Polymer().pdb calls for the component Polymers.
        """
        base_filters = dict(ligands=ligands, pseudo_group=pseudo_group)
        restricted_mol_types = [x[0] for x in base_filters.items() if not x[1]]
        in_groups = [x for x in self.filter_mol_types(restricted_mol_types)]

        pdb_header = 'HEADER {:<80}\n'.format(
            'ISAMBARD Model {}'.format(self.id)) if header else ''
        pdb_body = ''.join([x.make_pdb(
            alt_states=alt_states, inc_ligands=ligands) + '{:<80}\n'.format('TER') for x in in_groups])
        pdb_footer = '{:<80}\n'.format('END') if footer else ''
        pdb_str = ''.join([pdb_header, pdb_body, pdb_footer])
        return pdb_str

    # Protein specific methods
    @property
    def backbone(self):
        """Generates a new `Assembly` containing only the backbone atoms.

        Notes
        -----
        Metadata is not currently preserved from the parent object.
        Sequence data is retained, but only the main chain atoms are
        retained.

        Returns
        -------
        bb_assembly : ampal.Protein
            `Assembly` containing only the backbone atoms of the original
            `Assembly`.
        """
        bb_molecules = [
            p.backbone for p in self._molecules if hasattr(p, 'backbone')]
        bb_assembly = Assembly(bb_molecules, assembly_id=self.id)
        return bb_assembly

    @property
    def primitives(self):
        """Generates a new `Assembly` containing the primitives of each Polymer.

        Notes
        -----
        Metadata is not currently preserved from the parent object.

        Returns
        -------
        prim_assembly : ampal.Protein
            `Assembly` containing only the primitives of the `Polymers`
            in the original `Assembly`.
        """
        prim_molecules = [
            p.primitive for p in self._molecules if hasattr(p, 'primitive')]
        prim_assembly = Assembly(molecules=prim_molecules, assembly_id=self.id)
        return prim_assembly

    @property
    def helices(self):
        """Generates new `Assembly` containing just α-helices.

        Notes
        -----
        Metadata is not currently preserved from the parent object.

        Returns
        -------
        hel_assembly : ampal.Protein
            `Assembly` containing only the α-helices of the original `Assembly`.
        """
        hel_molecules = list(itertools.chain(
            *[p.helices._molecules
              for p in self._molecules if hasattr(p, 'helices')]))
        hel_assembly = Assembly(molecules=hel_molecules, assembly_id=self.id)
        return hel_assembly

    @property
    def strands(self):
        """Generates a new `Assembly` containing only the β-strands.

        Notes
        -----
        Metadata is not currently preserved from the parent object.

        Returns
        -------
        strand_assembly : ampal.Protein
            `Assembly` containing only the β-strands of the original `Assembly`.
        """
        strand_molecules = list(itertools.chain(
            *[p.strands._molecules for p in self._molecules if hasattr(p, 'strands')]))
        strand_assembly = Assembly(
            molecules=strand_molecules, assembly_id=self.id)
        return strand_assembly

    @property
    def sequences(self):
        """Returns the sequence of each `Polymer` in the `Assembly` as a list.

        Returns
        -------
        sequences : [str]
            List of sequences.
        """
        seqs = [x.sequence for x in self._molecules if hasattr(x, 'sequence')]
        return seqs

    @property
    def molecular_weight(self):
        """Returns the molecular weight of the `Assembly` in Daltons."""
        return sequence_molecular_weight(''.join(self.sequences))

    @property
    def molar_extinction_280(self):
        """Returns the extinction co-efficient of the `Assembly` at 280 nm."""
        return sequence_molar_extinction_280(''.join(self.sequences))

    @property
    def isoelectric_point(self):
        """Returns the isoelectric point of the `Assembly`."""
        return sequence_isoelectric_point(''.join(self.sequences))

    @property
    def fasta(self):
        """Generates a FASTA string for the `Assembly`.

        Notes
        -----
        Explanation of FASTA format: https://en.wikipedia.org/wiki/FASTA_format
        Recommendation that all lines of text be shorter than 80
        characters is adhered to. Format of PDBID|CHAIN|SEQUENCE is 
        consistent with files downloaded from the PDB. Uppercase 
        PDBID used for consistency with files downloaded from the PDB.
        Useful for feeding into cdhit and then running sequence clustering.

        Returns
        -------
        fasta_str : str
            String of the fasta file for the `Assembly`.
        """
        fasta_str = ''
        max_line_length = 79
        for p in self._molecules:
            if hasattr(p, 'sequence'):
                fasta_str += '>{0}:{1}|PDBID|CHAIN|SEQUENCE\n'.format(
                    self.id.upper(), p.id)
                seq = p.sequence
                split_seq = [seq[i: i + max_line_length]
                             for i in range(0, len(seq), max_line_length)]
                for seq_part in split_seq:
                    fasta_str += '{0}\n'.format(seq_part)
        return fasta_str

    def get_interaction_energy(self, assign_ff=True, ff=None, mol2=False,
                               force_ff_assign=False):
        """Calculates the interaction energy of the AMPAL object.

        Parameters
        ----------
        assign_ff: bool, optional
            If true the force field will be updated if required.
        ff: BuffForceField, optional
            The force field to be used for scoring.
        mol2: bool, optional
            If true, mol2 style labels will also be used.
        force_ff_assign: bool, optional
            If true, the force field will be completely reassigned, 
            ignoring the cached parameters.

        Returns
        -------
        buff_score: buff.BUFFScore
            A BUFFScore object with information about each of the
            interactions and the `Atoms` involved.

        Raises
        ------
        AttributeError
            Raise if a component molecule does not have an `update_ff`
            method.
        """
        if not ff:
            ff = global_settings['buff']['force_field']
        if assign_ff:
            for molecule in self._molecules:
                if hasattr(molecule, 'update_ff'):
                    molecule.update_ff(
                        ff, mol2=mol2, force_ff_assign=force_ff_assign)
                else:
                    raise AttributeError(
                        'The following molecule does not have a update_ff'
                        'method:\n{}\nIf this is a custom molecule type it'
                        'should inherit from BaseAmpal:'.format(molecule))
        interactions = find_inter_ampal(self, ff.distance_cutoff)
        buff_score = score_interactions(interactions, ff)
        return buff_score

    buff_interaction_energy = property(get_interaction_energy)

    def get_internal_energy(self, assign_ff=True, ff=None, mol2=False, force_ff_assign=False):
        """Calculates the internal energy of the AMPAL object.

        Notes
        -----

        THIS METHOD REDEFINES THE `BaseAmpal` VERSION. This is so that
        the force field is updated if any of its molecules need updating.
        This method is assigned to the `buff_internal_energy` property,
        using the default arguments.

        Parameters
        ----------
        assign_ff: bool, optional
            If true the force field will be updated if required.
        ff: buff.BuffForceField, optional
            The force field to be used for scoring.
        mol2: bool, optional
            If true, mol2 style labels will also be used.
        force_ff_assign: bool, optional
            If true, the force field will be completely reassigned,
            ignoring the cached parameters.

        Returns
        -------
        buff_score: buff.BUFFScore
            A BUFFScore object with information about each of the 
            interactions and the atoms involved.

        Raises
        ------
        AttributeError
            Raise if a component molecule does not have an `update_ff`
            method.
        """
        if not ff:
            ff = global_settings['buff']['force_field']
        if assign_ff:
            for molecule in self._molecules:
                if hasattr(molecule, 'update_ff'):
                    molecule.update_ff(
                        ff, mol2=mol2, force_ff_assign=force_ff_assign)
                else:
                    raise AttributeError(
                        'The following molecule does not have a update_ff'
                        'method:\n{}\nIf this is a custom molecule type it'
                        'should inherit from BaseAmpal:'.format(molecule))
        interactions = find_intra_ampal(self, ff.distance_cutoff)
        buff_score = score_interactions(interactions, ff)
        return buff_score

    buff_internal_energy = property(get_internal_energy)

    def pack_new_sequences(self, sequences):
        """Packs a new sequence onto each Polymer in the Assembly using Scwrl4.

        Notes
        -----
        The Scwrl packing score is saved in `Assembly.tags['scwrl_score']`
        for reference.

        Scwrl must be available to call. Check by running
        `isambard.external_programs.scwrl.test_scwrl`. If Scwrl is not
        available, please follow instruction here to add it:
        https://github.com/woolfson-group/isambard#external-programs

        For more information on Scwrl see [1].

        References
        ----------
        .. [1] Krivov GG, Shapovalov MV, and Dunbrack Jr RL (2009) "Improved
           prediction of protein side-chain conformations with SCWRL4.",
           Proteins.

        Parameters
        ----------
        sequences : [str]
            A list of strings containing the amino acid sequence of each
            corresponding `Polymer`. These must be the same length as the
            `Polymer`.

        Raises
        ------
        ValueError
            Raised if the sequence length does not match the number of
            monomers in the `Polymer`.
        """
        from ampal.pdb_parser import convert_pdb_to_ampal
        assembly_bb = self.backbone
        total_seq_len = sum([len(x) for x in sequences])
        total_aa_len = sum([len(x) for x in assembly_bb])
        if total_seq_len != total_aa_len:
            raise ValueError('Total sequence length ({}) does not match '
                             'total Polymer length ({}).'.format(
                                 total_seq_len, total_aa_len))
        scwrl_out = pack_sidechains(self.backbone.pdb, ''.join(sequences))
        if scwrl_out is None:
            return
        else:
            packed_structure, scwrl_score = scwrl_out
        new_assembly = convert_pdb_to_ampal(packed_structure, path=False)
        self._molecules = new_assembly._molecules[:]
        self.assign_force_field(global_settings[u'buff'][u'force_field'])
        self.tags['scwrl_score'] = scwrl_score
        return

    def repack_all(self):
        """Repacks the side chains of all Polymers in the Assembly."""
        non_na_sequences = [s for s in self.sequences if ' ' not in s]
        self.pack_new_sequences(non_na_sequences)
        return

    def tag_secondary_structure(self, force=False):
        """Tags each `Monomer` in the `Assembly` with it's secondary structure.

        Notes
        -----
        DSSP must be available to call. Check by running
        `isambard.external_programs.dssp.test_dssp`. If DSSP is not
        available, please follow instruction here to add it:
        https://github.com/woolfson-group/isambard#external-programs

        For more information on DSSP see [1].

        References
        ----------
        .. [1] Kabsch W, Sander C (1983) "Dictionary of protein 
           secondary structure: pattern recognition of hydrogen-bonded
           and geometrical features", Biopolymers, 22, 2577-637.

        Parameters
        ----------
        force : bool, optional
            If True the tag will be run even if `Monomers` are already tagged
        """
        for polymer in self._molecules:
            if polymer.molecule_type == 'protein':
                polymer.tag_secondary_structure(force=force)
        return

    def tag_dssp_solvent_accessibility(self, force=False):
        """Tags each `Monomer` in the Assembly with its solvent accessibility.

        Notes
        -----
        For more about DSSP's solvent accessibilty metric, see:
            http://swift.cmbi.ru.nl/gv/dssp/HTML/descrip.html#ACC

        DSSP must be available to call. Check by running
        `isambard.external_programs.dssp.test_dssp`. If DSSP is not
        available, please follow instruction here to add it:
        https://github.com/woolfson-group/isambard#external-programs

        For more information on DSSP see [1].

        References
        ----------
        .. [1] Kabsch W, Sander C (1983) "Dictionary of protein 
           secondary structure: pattern recognition of hydrogen-bonded
           and geometrical features", Biopolymers, 22, 2577-637.

        Parameters
        ----------
        force : bool, optional
            If True the tag will be run even if Monomers are already tagged
        """
        for polymer in self._molecules:
            polymer.tag_dssp_solvent_accessibility(force=force)
        return

    def tag_torsion_angles(self, force=False):
        """Tags each `Monomer` in the `Assembly` with its torsion angles.

        Parameters
        ----------
        force : bool, optional
            If `True`, the tag will be run even if `Monomers` are already
            tagged.
        """
        for polymer in self._molecules:
            if polymer.molecule_type == 'protein':
                polymer.tag_torsion_angles(force=force)
        return

    def tag_ca_geometry(self, force=False, reference_axis=None,
                        reference_axis_name='ref_axis'):
        """Tags each `Monomer` in the `Assembly` with its helical geometry.

        Parameters
        ----------
        force : bool, optional
            If True the tag will be run even if `Monomers` are already tagged.
        reference_axis : list(numpy.array or tuple or list), optional
            Coordinates to feed to geometry functions that depend on
            having a reference axis.
        reference_axis_name : str, optional
            Used to name the keys in tags at `Chain` and `Residue` level.
        """
        for polymer in self._molecules:
            if polymer.molecule_type == 'protein':
                polymer.tag_ca_geometry(
                    force=force, reference_axis=reference_axis,
                    reference_axis_name=reference_axis_name)
        return

    def tag_atoms_unique_ids(self, force=False):
        """ Tags each Atom in the Assembly with its unique_id.

        Notes
        -----
        The unique_id for each atom is a tuple (a double). `unique_id[0]`
        is the unique_id for its parent `Monomer` (see `Monomer.unique_id`
        for more information). `unique_id[1]` is the atom_type in the
        `Assembly` as a string, e.g. 'CA', 'CD2'.

        Parameters
        ----------
        force : bool, optional
                If True the tag will be run even if Atoms are already tagged.
                If False, only runs if at least one Atom is not tagged.

        """
        tagged = ['unique_id' in x.tags.keys() for x in self.get_atoms()]
        if (not all(tagged)) or force:
            for m in self.get_monomers():
                for atom_type, atom in m.atoms.items():
                    atom.tags['unique_id'] = (m.unique_id, atom_type)
        return

    def filter_mol_types(self, mol_types):
        return [x for x in self._molecules if x.molecule_type not in mol_types]

    def tag_residue_solvent_accessibility(self, tag_type=False, tag_total=False,
                                          force=False, include_hetatms=False):
        """Tags each Monomer with its Relative Residue Solvent Accessibility.

        Notes
        -----
        Relative Relative Solvent Accessibility is identified by NACCESS.

        Parameters
        ----------
        force : bool, optional
            If `True`, the tag will be run even if `Monomers` are already
            tagged.
        tag_type : str, optional
            Specifies the name of the tag. Defaults to 
            `residue_solvent_accessibility`. Useful for specifying more
            than one tag, e.g. if the `Polymer` is part of an `Assembly`
        tag_total : bool, optional
            If `True` then the total RSA of the `Assembly` will be tagged
            in the `total accessibility` tag.
        include_hetatms: bool, optional
            If `True`, naccess will run with the -h flag. This means it 
            will correctly run on structures with MSE, although the
            accessibility will be set to -99.9 for these residues.
            Probably best to check if your structure has these before
            using it.
        """
        tagged = [tag_type in x.tags.keys()
                  for x in self.get_monomers(ligands=False)]
        if (not all(tagged)) or force:

            naccess_rsa_list, total = extract_residue_accessibility(
                run_naccess(self.pdb, mode='rsa', path=False,
                            include_hetatms=include_hetatms),
                path=False, get_total=tag_total)
            for monomer, naccess_rsa in zip(
                    self.get_monomers(ligands=False), naccess_rsa_list):
                monomer.tags[tag_type] = naccess_rsa

            if tag_total:
                self.tags['total_assembly_accessibility'] = total

        return


__author__ = "Christopher W. Wood, Gail J. Bartlett"
