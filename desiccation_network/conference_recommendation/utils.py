"""
Utility functions for working with citation networks.

Author: Serena G. Lotreck
"""
from itertools import product
import numpy as np
from collections import defaultdict, Counter
import pycountry
import pandas as pd
from unidecode import unidecode


def calculate_dyadic_citation_freqs(graph, attribute):
    """
    Calculate dyadic citation frequencies for a given network.

    parameters:
        graph, MultiDiGraph: citation network with classifications
        attribute, str: name of the attribute for which to calculate the
            frequencies

    returns:
        dyadic_freqs, dict: keys are ordered pairs of study_system names, values are
            floats for the frequency at which the first study system cited the
            second
    """
    # Get the available study systems
    systems = {attrs[attribute] for node, attrs in graph.nodes(data=True)}

    # Get all ordered pairs and set up for data collection
    system_pairs = {p: 0 for p in product(systems, repeat=2)}
    system_totals = {sys: 0 for sys in systems}

    # For all nodes, add to both dicts
    for node, attrs in graph.nodes(data=True):
        # Get the system of this paper
        self_system = attrs[attribute]
        # Get the total number of citations for this node
        system_totals[self_system] += graph.out_degree(node)
        # Go through citations specifically and get their systems
        for cited_paper in graph.neighbors(node):
            cit_type = graph.nodes[cited_paper][attribute]
            system_pairs[(self_system, cit_type)] += 1

    # Calculate dyadic freqs
    dyadic_freqs = {
        sys_pair: num / system_totals[sys_pair[0]]
        if system_totals[sys_pair[0]] != 0 else np.nan
        for sys_pair, num in system_pairs.items()
    }

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

    study_by_uid = {
        uid: attrs['study_system']
        for uid, attrs in graph.nodes(data=True)
    }

    updated_jsonl = []
    for paper in jsonl:
        to_modify = dict(paper)
        try:
            to_modify['study_system'] = study_by_uid[to_modify[keyname]]
            updated_jsonl.append(to_modify)
        except KeyError:
            continue

    return updated_jsonl


def prune_citation_network(graph,
                           main_results_only=None,
                           remove_dead_ends=False,
                           threshold_in_degree=None,
                           remove_noclass=False):
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
        to_remove = [
            node for node in graph.nodes if node not in main_results_only
        ]
    elif remove_dead_ends:
        to_remove = [
            node for node in graph.nodes if graph.out_degree(node) == 0
        ]
    elif threshold_in_degree is not None:
        to_remove = [
            node for node in graph.nodes
            if graph.in_degree(node) < threshold_in_degree
        ]
    elif remove_noclass:
        to_remove = [
            node for node, attrs in graph.nodes(data=True)
            if attrs['study_system'] == 'NOCLASS'
        ]

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
            if (len(key_rels['relevant'].unique())
                    == 1) and (key_rels['relevant'].unique()[0] == 'Y'):
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
    Turn an alternative name dataframe into a dict indexed by WOS standard names
    self-reported by attendees. Note that this function was created to allow
    generalization without too much manual labor (i.e., names can be pasted
    into alt names spreadhseet as they appear in publications, and don't need
    to be manually formatted to fit WOS standard formatting); however, it was
    designed on a specific set of names with specific properties, and may need
    additional test cases/tuning for new name cases.

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
        # Account for possible first name hyphenation when getting the key name
        reg_first_name = [
            i for part in row.Registration_first_name.split()
            for i in part.split('-')
        ]
        key = f'{row.Registration_surname.lower()}, {"".join([n[0] for n in reg_first_name]).lower()}'
        names = []
        # Add registration name
        names.append((row.Registration_surname.lower(),
                      row.Registration_first_name.lower().strip('.')))
        # Get alternative names with same surname
        for name in row.tolist()[2:-1]:
            if not isinstance(name, str):
                continue
            split_name = name.split(' ')
            # If the name is a simple firstname/lastname swap, skip other steps
            if split_name == [
                    row.Registration_surname, row.Registration_first_name
            ]:
                names.append((split_name[1].lower(), split_name[0].lower()))
                continue
            # If the publication name is just a first name, skip other steps
            if len(split_name) == 1:
                names.append((split_name[0].lower(), ))
                continue
            # Remove surname to get first name
            surname = row.Registration_surname.split(' ')
            surname = [part for name in surname for part in name.split('-')]
            first_name = [
                i for i in split_name
                if unidecode(i) not in [unidecode(p) for p in surname]
            ]
            # If nothing was removed, check for the second first name having become surname
            if len(first_name) == len(split_name):
                # Assumes the final name in list is the surname
                first_name = first_name[:-1]
            # Adjust surname if one part is missing in alt name (edge case that exists in our data)
            alt_surname = [i for i in split_name if i not in first_name]
            first_name = [
                ' '.join([i.strip() for i in nm.split('.')]).strip()
                for nm in first_name
            ]
            full_name = (' '.join(alt_surname).lower(),
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
        name_map, dict: keys are alternative names in all possible WOS standard
            formats, values are DesWorks recorded author names in post-2006 WOS
            standard
    """
    # Process attendees to lowercase
    # for col in attendees.columns:
    #         attendees[col] = attendees[col].str.strip().str.lower()

    ## TODO implement the ability to use the attendees df instead of alt names,
    ## for cases where alt names can't be curated manually

    # Make dictionary where keys are all possible names in all possible WOS
    # formats, and values are their wos standard registration name. This
    # automatically includes maiden names.
    name_map = {}
    for conf_author, alts in alt_names.items():
        # 2006 to present
        auth_full_names = []
        for alt_n in alts:
            # For authors with only a single  name
            if len(alt_n) == 1:
                auth_full_names.append(alt_n[0])
                continue
            last_name = alt_n[0]
            # This assumes that if splitting on spaces/hyphens and stripping periods
            # lands you with only one letter, it's an initial, and otherwise
            # it's a full first name
            first_name_parts = [n.strip('.') for n in alt_n[1].split()]
            first_single_letter = [
                i for i, n in enumerate(first_name_parts) if len(n) == 1
            ]
            if len(first_single_letter) >= 1:  ## Assumes they're sequential
                initials = ''.join(first_name_parts[first_single_letter[0]:])
                first_full_name_parts = first_name_parts[:first_single_letter[
                    0]]
                if first_full_name_parts == []:
                    first_name = initials
                else:
                    first_full_name = ' '.join(first_full_name_parts)
                    first_name = ' '.join([first_full_name, initials])
            else:
                first_name = ' '.join(first_name_parts)
            full_name = ', '.join([last_name, first_name])
            auth_full_names.append(full_name)
        # pre-2006/WOS standard
        auth_initial_names = []
        for alt_n in alts:
            # Skip single names
            if len(alt_n) == 1:
                continue
            last_name = alt_n[0]
            initials = ''.join(
                [n[0] for name in alt_n[1].split() for n in name.split('-')])
            initial_name = last_name + ', ' + initials
            auth_initial_names.append(initial_name)
        # 1964-75
        auth_11_char_names = []
        for alt_n in alts:
            # Skip single names
            if len(alt_n) == 1:
                continue
            # If surname is longer than 8 chars, it is truncated and the first
            # and last name are separated with a dot
            if len(alt_n[0]) > 8:
                last_name = alt_n[0][:8]
                initials = ''.join([
                    n[0] for name in alt_n[1].split() for n in name.split('-')
                ][:3])
                dot_name = last_name + '.' + initials
                auth_11_char_names.append(dot_name)
            # If it's less than 8 characters, we can include more first initials
            # and it's separated with a space
            else:
                remaining_chars = 11 - len(alt_n[0])
                last_name = alt_n[0]
                initials = ''.join([
                    n[0] for name in alt_n[1].split() for n in name.split('-')
                ][:remaining_chars])
                space_name = ' '.join([last_name, initials])
                auth_11_char_names.append(space_name)
        # Combine and add to dict
        all_names = auth_full_names + auth_initial_names + auth_11_char_names
        for alt_n in all_names:
            name_map[alt_n] = conf_author

    # Check all paper authors against our list
    conference_authors = defaultdict(list)
    for paper in dataset:
        uid = paper['UID']
        for author in paper['authors']:
            try:
                # Lowercase and remove any periods
                full_n = author['full_name'].lower().replace('.', '')
                wos_n = author['wos_standard'].lower()
                # Check both full name and WOS name
                if full_n in name_map.keys():
                    reg_auth = name_map[full_n]
                    conference_authors[reg_auth].append(uid)
                elif wos_n in name_map.keys():
                    reg_auth = name_map[wos_n]
                    conference_authors[reg_auth].append(uid)
            except KeyError:
                continue

    # Add back any authors that didn't have papers
    missing_auths = [
        auth for auth in set(name_map.values())
        if auth not in conference_authors.keys()
    ]
    for auth in missing_auths:
        conference_authors[auth] = []

    return conference_authors, name_map


def get_iso_alpha(country):
    """
    Get Alpha-3 name for country. Uses manual mapping for specific WOS country names
    that don't match to the conversion database. Note that this list is specific
    to failures for our own dataset, and may need to be expanded to work with a
    larger dataset.

    parameters:
        country, str: country to convert

    returns:
        iso_name, str: three-letter country code
    """
    # Get all mappings
    country_conversions = {
        country.name: country.alpha_3
        for country in pycountry.countries
    }
    wos_missed_dict = {
        'USA': 'USA',
        'Peoples R China': 'CHN',
        'England': 'GBR',
        'South Korea': 'KOR',
        'Russia': 'RUS',
        'Czech Republic': 'CZE',
        'Iran': 'IRN',
        'Taiwan': 'TWN',
        'Turkey': 'TUR',
        'Scotland': 'GBR',
        'Wales': 'GBR',
        'U Arab Emirates': 'ARE',
        'Vietnam': 'VNM',
        'North Ireland': 'GBR',
        'Dominican Rep': 'DOM',
        'Cote Ivoire': 'CIV',
        'Brunei': 'BRN',
        'Dem Rep Congo': 'COD',
        'Syria': 'SYR',
        'Kosovo':
        'XKX',  # Note: Kosovo is not listed as an ISO standard country. The unofficial 2 and 3-digit codes are used by the European Commission and others until Kosovo is assigned an ISO code.(from https://knowledgecenter.zuora.com/Quick_References/Country%2C_State%2C_and_Province_Codes/A_Country_Names_and_Their_ISO_Codes)
        'BELARUS': 'BLR',
        'Venezuela': 'VEN',
        'Bolivia': 'BOL',
        'North Korea': 'PRK',
        'Palestine': 'PSE',
        'Laos': 'LAO',
        'Papua N Guinea': 'PNG',
        'Usa': 'USA',
        'Fed Rep Ger': 'DEU'  # For older affiliations from West Germany
    }

    # Map country and return
    try:
        iso_name = country_conversions[country.title()]
        return iso_name
    except KeyError:
        try:
            iso_name = wos_missed_dict[country.title()]
            return iso_name
        except KeyError:
            print(
                f'No three-letter code found for country {country}, returning None'
            )
            return


def get_geographic_locations(dataset):
    """
    Get the country name of the most recent affiliation for all authors.

    NOTE: For papers where authors don't have address numbers, checks if the
    addresses are all located in the same country and assigns that country as
    the affiliation location.

    parameters:
        dataset, list of dict: paper dataset with authors and affiliations
    """
    # Drop papers with no year
    papers_with_years = [paper for paper in dataset if 'year' in paper.keys()]

    # Sort papers by year
    papers_chron_order_rev = sorted(dataset,
                                    key=lambda x: x['year'],
                                    reverse=True)

    # Get most recent affiliations
    author_affils = {}
    all_authors = []
    for paper in papers_chron_order_rev:
        addrs = {addr['addr_no']: addr for addr in paper['addresses']}
        for author in paper['authors']:
            try:
                all_authors.append(author['wos_standard'])
                if author['wos_standard'] in author_affils.keys():
                    continue
                else:
                    try:
                        # Check for specific affiliation
                        # Start by checking if the person has multiple
                        # affiliations
                        mult_addrs = [int(i) for i in author['addr_no'].split(' ')]
                        # If there are multiples, take the first one, otherwise
                        # take what there is
                        country = addrs[str(mult_addrs[0])]['country']
                        country_iso = get_iso_alpha(country)
                        if country_iso is not None:
                            author_affils[
                                author['wos_standard'].lower()] = country_iso
                    except KeyError as e:
                        # Check if all affiliations are in the same country if no specific affiliation
                        countries = [
                            addr['country'] for addr in paper['addresses']
                        ]
                        if len(set(countries)) == 1:
                            country = countries[0]
                            country_iso = get_iso_alpha(country)
                            if country_iso is not None:
                                author_affils[author['wos_standard'].lower(
                                )] = country_iso
                        else:
                            continue
            except KeyError:
                continue

    print(
        f'There are {len(author_affils)} author-country pairs, and {len(set(all_authors))} total authors.'
    )

    return author_affils


def calculate_gen_prob_geo_score(author_affils_dict, top_50p, bottom_50p):
    """
    Calculates the general probability score for an author with no geographic
    affiliation.

    parameters:
        author_affils_dict, dict: keys are all authors in dataset, values are
            country affiliation iso alpha three-letter codes
        top_50p, list of str: list of top 50 percentile attendee countries
        bottom_50p, list of str: list of bottom 50 percentile attendee countries

    returns:
        gen_prob_score, float: single number general probability score
    """
    # Get overall counts and convert to weights
    country_counts = pd.DataFrame.from_dict(Counter(
        author_affils_dict.values()),
                                            orient='index',
                                            columns=['count'])
    country_counts[
        'weight'] = country_counts['count'] / country_counts['count'].sum()

    # Get overall probability of belonging to an attendee country
    all_attendee_countries = top_50p + bottom_50p
    attendee_countries_total_weight = country_counts[country_counts.index.isin(
        all_attendee_countries)]['weight'].sum()

    # Get the probability of an attendee country being a low representation country
    low_rep_prob = len(bottom_50p) / len(all_attendee_countries)

    # Make the calculation
    gen_prob_score = (1 - attendee_countries_total_weight) + (
        attendee_countries_total_weight * (low_rep_prob * 0.5))

    return gen_prob_score
