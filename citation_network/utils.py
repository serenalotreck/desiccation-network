"""
Utility functions for working with citation networks.

Author: Serena G. Lotreck
"""
from itertools import product


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

    # Get all ordered pairs
    system_pairs = [p for p in product(systems, repeat=2)]

    


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
    Map the classes from a MultiDiGraph to the jsonl format.

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
        to_modify['study_system'] = study_by_uid[to_modify[keyname]]
        updated_jsonl.append(to_modify)

    return updated_jsonl


def map_classes_to_topics(input_doc_df, topic_doc_df, graph, keyname):
    """
    Map the study system classifications from a classified citation network to
    the topic clusters created by BERTopic.

    parameters:
        input_doc_df, df: the df from which the input to the topic model was
            drawn without altering the original order
        topic_doc_df, df: the output of topic_model.get_document_info(docs)
        graph, MultiDiGraph: classified citation network
        keyname, str: 'UID' or 'paperId', default is 'UID'

    returns:
        classified_topic_df, df: topic_doc_df with added column for
            classifications
    """
    # Put the UID's back together with the docs
    topic_doc_df[keyname] = input_doc_df.index.values.tolist()

    # Match study systems to UIDs
    study_by_uid = {uid: attrs['study_system'] for uid, attrs in
            graph.nodes(data=True)}

    # Get the classifications
    study_systems = []
    for doc_idx in input_doc_df.index.values.tolist():
        study_systems.append(study_by_uid[doc_idx])

    # Add to overall df
    classified_topic_df = topic_doc_df
    classified_topic_df['study_system'] = study_systems

    return classified_topic_df
