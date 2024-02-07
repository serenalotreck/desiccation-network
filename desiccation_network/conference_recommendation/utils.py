"""
Utility functions for working with citation networks.

Author: Serena G. Lotreck
"""
from itertools import product
import numpy as np


def calculate_dyadic_citation_freqs(graph):
    """
    Calculate dyadic citation frequencies for a given network.

    parameters:
        graph, MultiDiGraph: citation network with classifications

    returns:
        dyadic_freqs, dict: keys are ordered pairs of study_system names, values are
            floats for the frequency at which the first study system cited the
            second
    """
    # Get the available study systems
    systems = {attrs['study_system'] for node, attrs in graph.nodes(data=True)}

    # Get all ordered pairs and set up for data collection
    system_pairs = {p: 0 for p in product(systems, repeat=2)}
    system_totals = {sys: 0 for sys in systems}

    # For all nodes, add to both dicts
    for node, attrs in graph.nodes(data=True):
        # Get the system of this paper
        self_system = attrs['study_system']
        # Get the total number of citations for this node
        system_totals[self_system] += graph.out_degree(node)
        # Go through citations specifically and get their systems
        for cited_paper in graph.neighbors(node):
            cit_type = graph.nodes[cited_paper]['study_system']
            system_pairs[(self_system, cit_type)] += 1

    # Calculate dyadic freqs
    dyadic_freqs = {sys_pair: num/system_totals[sys_pair[0]]  if system_totals[sys_pair[0]] != 0 else
            np.nan for sys_pair, num
            in system_pairs.items()}

    return dyadic_freqs


def flatten_jsonl(jsonl):
    """
    Flatten a jsonl to bring references level with main results.

    parameters:
        jsonl, list of dict: jsonl to flatten

    returns:
        flattened_jsonl, list of dict: flattened jsonl
    """
    flattened_jsonl = []
    for paper in jsonl:
        flattened_jsonl.append(paper)
        for ref in paper['references']:
            flattened_jsonl.append(ref)

    return flattened_jsonl


def map_classes_to_jsonl(graph, jsonl, flatten, keyname):
    """
    Map the classes from a MultiDiGraph to the jsonl format. If there are extra
    abstracts in the jsonl that don't exist in the graph, they are removed from
    the dataset.

    parameters:
        graph, MultiDiGraph: graph with classifications
        jsonl, list of dict: jsonl to which to add classifications
        flatten, bool: whether or not the jsonl needs to or should be flattened
            before mapping
        keyname, str: 'UID' or 'paperId', default is 'UID'

    returns:
        updated_jsonl, list of dict: jsonl with "study_system" key added
    """
    if flatten:
        jsonl = flatten_jsonl(jsonl)

    study_by_uid = {uid: attrs['study_system'] for uid, attrs in
            graph.nodes(data=True)}

    updated_jsonl = []
    for paper in jsonl:
        to_modify = dict(paper)
        try:
            to_modify['study_system'] = study_by_uid[to_modify[keyname]]
            updated_jsonl.append(to_modify)
        except KeyError:
            continue

    return updated_jsonl


def prune_citation_network(graph, main_results_only=None,
        remove_dead_ends=False, threshold_in_degree=None, remove_noclass=False):
    """
    Prune a citation network according to some criteria. Options:
        main_results_only: only keep nodes and links that are among the main
            search results
        remove_dead_ends: only keep papers that have citations (out-degree > 0)
        threshold_in_degree: only keep papers that are cited by a threshold
            number of papers
        remove_noclass: removes nodes with no classification

    parameters:
        graph, MultiDiGraph: graph to prune
        main_results, list of str or None: list of main result UIDs. Pass to perform
            main_results_only filtering
        remove_dead_ends, bool: whether or not to remove dead ends from the
            graph
        threshold_in_degree, int or None: pass an integer threshold for the
            number of times a paper should be cited to keep in the network
        remove_noclass, bool: whether or not to remove nodes without a
            classification

    returns:
        graph, MultiDiGraph: pruned graph
    """
    if main_results_only is not None:
        to_remove = [node for node in graph.nodes if node not in
                main_results_only]
    elif remove_dead_ends:
        to_remove = [node for node in graph.nodes if graph.out_degree(node) ==
                0]
    elif threshold_in_degree is not None:
        to_remove = [node for node in graph.nodes if graph.in_degree(node) <
                threshold_in_degree]
    elif remove_noclass:
        to_remove = [node for node, attrs in graph.nodes(data=True) if
                attrs['study_system'] == 'NOCLASS']

    _ = graph.remove_nodes_from(to_remove)
    return graph


def prune_jsonl(jsonl):
    """
    Removes all references that are not also in the main results. Also adds
    abstracts to the reference instances.

    parameters:
        jsonl, list of dict: nested papers

    returns:
        final_jsonl, list of dict: pruned jsonl
    """
    # Get all main results UIDs
    uids = []
    for paper in jsonl:
        try:
            uids.append(paper['UID'])
        except KeyError:
            continue

    # Index abstracts by UID
    abstracts = {}
    for paper in jsonl:
        try:
            uid = paper['UID']
        except KeyError:
            continue
        try:
            abstract = paper['abstract']
            abstracts[uid] = abstract
        except KeyError:
            continue

    final_jsonl = []
    for paper in jsonl:
        pruned_paper = {}
        for k, v in paper.items():
            if k != 'references':
                pruned_paper[k] = v
            else:
                updated_refs = []
                for ref in paper['references']:
                    try:
                        if ref['UID'] in uids:
                            try:
                                ref['abstract'] = abstracts[ref['UID']]
                            except KeyError:
                                pass
                            updated_refs.append(ref)
                    except KeyError:
                        continue
                pruned_paper['references'] = updated_refs
        final_jsonl.append(pruned_paper)

    return final_jsonl


def filter_papers(papers, key_df, kind, stringency='most'):
    """
    Filter papers by keyword.

    parameters:
        papers, list of dict: papers to filter
        key_df, pandas df: index are keywords, column is 'relevant' containing Y or N strings
        kind, str: either 'static_keywords' or 'dynamic_keys' ## TODO change to static_keys for udpated dataset
        stringency, str: 'most', 'middle', or 'least', default is 'most'

    returns:
        filtered_papers, list of dict: list of papers with irrelevant papers removed
    """
    filtered_papers = []
    for paper in papers:
        # Get the relevances of all keywords
        keys = paper[kind]
        key_rels = key_df.loc[keys, :]
        # Filter based on requested stringency
        if stringency == 'most':
            if (len(key_rels['relevant'].unique()) == 1) and (key_rels['relevant'].unique()[0] == 'Y'):
                filtered_papers.append(paper)
        elif stringency == 'middle':
            nums = Counter(key_rels['relevant'].values.tolist())
            if nums['Y'] > nums['N']:
                filtered_papers.append(paper)
        elif stringency == 'least':
            if 'Y' in key_rels.relevant.values.tolist():
                filtered_papers.append(paper)

    return filtered_papers


def process_alt_names(alt_names):
    """
    Turn an alternative name dataframe into a dict indexed by WOS standard names self-reported by attendees.

    parameters:
        alt_names, df: columns are columns are Registration_surname, Registration_first_name,
            Alternative_name_1..., Maiden_name

    returns:
        alt_names_dict, dict: keys are "surname, initials", values are lists of tuple with (last name, first name)
            alternative names
    """
    alt_names_dict = {}
    for row in alt_names.iterrows():
        row = row[1]
        key = f'{row.Registration_surname.lower()}, {"".join([n[0] for n in row.Registration_first_name.split()]).lower()}'
        names = []
        # Get alternative names with same surname
        for name in row.tolist()[2:-1]:
            if not isinstance(name, str):
                continue
            split_name = name.split(' ')
            # Remove surname to get first name
            ## TODO deal with the specific edge cases where this fails for our attendees in manual pre-processing
            surname = row.Registration_surname.split(' ')
            first_name = [i for i in split_name if i not in surname]
            full_name = (' '.join(surname).lower(),
                         ' '.join(first_name).lower())
            names.append(full_name)
        if isinstance(row.Maiden_name, str):
            name = (row.Maiden_name.lower(),
                    row.Registration_first_name.lower())
            names.append(name)
        alt_names_dict[key] = names

    return alt_names_dict


def find_author_papers(attendees, dataset, alt_names):
    """
    Find papers that were authored by conference attendees.

    parameters:
        attendees, df: columns are Surname, First_name, Affiliation, Country
        dataset, list of dict: WoS papers with author and affiliation data
        alt_names, dict: formatted as per process_alt_names output

    returns:
        conference_authors, dict: keys are DesWorks recorded author names in
            WOS standard, values are WOS UIDs
        processed_alt_names, dict: keys are DesWorks recorded author names in
            WOS standard, values are lists of alternative names also in WOS
            standard
    """
    ## TODO edge cases
    # 1. Names with internal punctuation (e.g. O'Neill, Farooq-E-Azam)
    # 2. Check that Chinese names are correctly recovered with this approach, if not, add case
    # 3. Papers between 64-75 for authors with last names more than 8 characters

    # Maiden names
    maiden_names = {name[0]: wos_name for wos_name, name_list in
            alt_names.items() for name in name_list}

    # Check for conference authors
    conference_authors = {
        f'{surname.lower()}, {"".join([n[0] for n in first_name.split()]).lower()}':
        []
        for surname, first_name in zip(attendees['Surname'],
                                       attendees['First_name'])
    }
    processed_alt_names = {
        f'{surname.lower()}, {"".join([n[0] for n in first_name.split()]).lower()}':
        []
        for surname, first_name in zip(attendees['Surname'],
                                       attendees['First_name'])
    }

    for paper in dataset:
        # Check only surname first
        surnames = []
        for a in paper['authors']:
            try:
                surnames.append(a['last_name'].lower())
            except KeyError:
                # Dot 11-character names don't have a last name and we want
                # to include them. Other authors with no last name are
                # mostly organizations or repeats, can skip them
                try:
                    if len(a['wos_standard'].split('.')) == 2:
                        surnames.append(a['wos_standard'].split('.')
                                        [0].lower())  ## TODO #3
                except KeyError:
                    continue
        for name in surnames:
            # If surname is present, confirm with wos standard (including first name) name
            if (name in attendees.Surname.tolist()) or (
                    name in maiden_names.keys()):
                # Change maiden name to registered name if relevant
                if name in maiden_names.keys(): ## TODO make sure this works as expected
                    name = maiden_names[name].split(', ')[0]
                # Get the rows with this surname, possible multiple have same surname
                possible_authors = attendees[
                    attendees['Surname'] == name][[
                        'Surname', 'First_name'
                    ]]
                # Process first names to initials
                possible_first_names = possible_authors.First_name.tolist()
                possible_initials = [
                    "".join([n[0] for n in fn.split()])
                    for fn in possible_first_names
                ]
                # Get first name as initial name format
                pre_2006s_and_WOS_standard = [
                    f'{name}, {initials}' for initials in possible_initials
                ]
                # Get alternative names for these possible authors
                possible_first_names += [
                    name[1] for prename in pre_2006s_and_WOS_standard
                    for name in alt_names[prename]
                ]
                possible_initials += [
                    "".join([n[0] for n in name[1].split()])
                    for prename in pre_2006s_and_WOS_standard
                    for name in alt_names[prename]
                ]
                pre_2006s_and_WOS_standard += [
                    f'{name}, {initials}' for initials in possible_initials
                ]
                # Figure out which conference author it is and add possible
                # names to processed alt names
                potential_conference_corresponding = [a for a in
                        processed_alt_names.keys() if name in a]
                corresponding_conf = [a for a in
                        potential_conference_corresponding if a in
                        pre_2006s_and_WOS_standard]
                assert len(corresponding_conf) == 1
                processed_alt_names[corresponding_conf[0]].extend(pre_2006s_and_WOS_standard)
                # Get possible oldest name format
                char_11s_space = [
                    f'{name[:8]}, {initials}'
                    for initials in possible_initials
                ]
                char_11s_period = [
                    f'{name[:8]}.{initials}'
                    for initials in possible_initials
                ]
                # Get full name
                full_names = [
                    f'{name}, {first_name}'
                    for first_name in possible_first_names
                ]
                # Combine for all possibilities
                to_check = char_11s_space + char_11s_period + pre_2006s_and_WOS_standard + full_names
                # Now check all names against paper authors
                for author in paper['authors']:
                    full_authors_found = []
                    if (author['full_name'].lower() in to_check) or (
                            author['wos_standard'].lower() in to_check):
                        if len(possible_authors) == 1:
                            try:
                                conference_authors[
                                    author['wos_standard'].lower()].append(
                                        paper['UID'])
                            except KeyError:
                                ## TODO I think this works for my particular observed cases, but does not generalize, need to generalize
                                key = pre_2006s_and_WOS_standard[
                                    0] if pre_2006s_and_WOS_standard[0].split(
                                        ', '
                                    )[0][0] == author['wos_standard'].lower(
                                    ).split(', ')[1][
                                        0] else pre_2006s_and_WOS_standard[
                                            1]
                                conference_authors[key].append(
                                    paper['UID'])
                        else:
                            full_authors_found.append(
                                author['wos_standard'].lower())
                if len(full_authors_found) != 0:
                    for author_name in full_authors_found:
                        conference_authors[author_name].append(
                            paper['UID'])
    processed_alt_names = {k: list(set(v)) for k, v in
            processed_alt_names.items()}

    return conference_authors, processed_alt_names


def get_geographic_locations(dataset):
    """
    Get the country name of the most recent affiliation for all authors.

    parameters:
        dataset, list of dict: paper dataset with authors and affiliations
    """
    # Drop papers with no year
    papers_with_years = [paper for paper in dataset if 'year' in paper.keys()]
    # Sort papers by year
    papers_chron_order_rev = sorted(paper_dataset, key=lambda x: x['year'],
                                reverse=True)
    # Get most recent affiliations
    author_affils = {}
    for paper in papers_chron_order_rev:
        for author in paper['authors']:
            if author['wos_standard'] in author_affils.keys():
                continue
            else:
                pass
