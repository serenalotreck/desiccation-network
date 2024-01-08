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
