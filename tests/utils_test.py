"""
Test citation network utils.py.

Author: Serena G. Lotreck
"""
import pytest
import networkx as nx
import numpy as np
import sys

sys.path.append('../citation_network')
import utils

###################### calculate_dyadic_citation_freqs #########################


@pytest.fixture
def input_graph():
    nodes = [
        ('p1', {
            'study_system': 'Plant'
        }),
        ('p2', {
            'study_system': 'Plant'
        }),
        ('p3', {
            'study_system': 'Plant'
        }),
        ('a1', {
            'study_system': 'Animal'
        }),
        ('a2', {
            'study_system': 'Animal'
        }),
        ('a3', {
            'study_system': 'Animal'
        }),
        ('a4', {
            'study_system': 'Animal'
        }),
        ('a5', {
            'study_system': 'Animal'
        }),
        ('m1', {
            'study_system': 'Microbe'
        }),
        ('m2', {
            'study_system': 'Microbe'
        }),
        ('m3', {
            'study_system': 'Microbe'
        }),
        ('f1', {
            'study_system': 'Fungi'
        }),
    ]
    edges = [('p1', 'p2'), ('p1', 'p3'), ('p1', 'a1'), ('a1', 'a4'),
             ('a1', 'a3'), ('a1', 'a2'), ('a2', 'a3'), ('a2', 'p3'),
             ('a2', 'm2'), ('a2', 'm1'), ('m1', 'm2'), ('m2', 'a5'),
             ('m2', 'm3'), ('m2', 'p2')]

    graph = nx.MultiDiGraph()
    _ = graph.add_nodes_from(nodes)
    _ = graph.add_edges_from(edges)

    return graph


@pytest.fixture
def dyadic_output():
    return {
        ('Plant', 'Animal'): 1 / 3,
        ('Plant', 'Microbe'): 0,
        ('Plant', 'Fungi'): 0,
        ('Plant', 'Plant'): 2 / 3,
        ('Animal', 'Plant'): 1 / 7,
        ('Animal', 'Microbe'): 2 / 7,
        ('Animal', 'Fungi'): 0,
        ('Animal', 'Animal'): 4 / 7,
        ('Microbe', 'Plant'): 0.25,
        ('Microbe', 'Animal'): 0.25,
        ('Microbe', 'Fungi'): 0,
        ('Microbe', 'Microbe'): 0.5,
        ('Fungi', 'Animal'): np.nan,
        ('Fungi', 'Plant'): np.nan,
        ('Fungi', 'Microbe'): np.nan,
        ('Fungi', 'Fungi'): np.nan
    }


def test_calculate_dyadic_citation_freqs(input_graph, dyadic_output):

    result = utils.calculate_dyadic_citation_freqs(input_graph)

    assert result == dyadic_output


############################### prune_jsonl ####################################


@pytest.fixture
def input_jsonl():
    return [{
        'UID':
        'paper1',
        'title':
        'paper1 is cool',
        'references': [{
            'UID': 'paper2',
            'title': 'paper2 is cool'
        }, {
            'UID': 'ref1',
            'title': 'ref1 is cool'
        }, {
            'UID': 'ref2',
            'title': 'ref2 is cool'
        }, {
            'UID': 'ref3',
            'title': 'ref3 is cool'
        }]
    }, {
        'UID':
        'paper2',
        'title':
        'paper2 is cool',
        'abstract': 'Paper2 is about B',
        'references': [{
            'UID': 'ref1',
            'title': 'ref1 is cool'
        }, {
            'UID': 'ref2',
            'title': 'ref2 is cool'
        }, {
            'UID': 'ref3',
            'title': 'ref3 is cool'
        }]
    }, {
        'UID':
        'paper3',
        'title':
        'paper3 is cool',
        'abstract':
        'Paper3 is about C',
        'references': [{
            'UID': 'paper1',
            'title': 'paper1 is cool'
        }, {
            'UID': 'paper2',
            'title': 'paper2 is cool'
        }]
    }]


@pytest.fixture
def output_jsonl():
    return [{
        'UID': 'paper1',
        'title': 'paper1 is cool',
        'references': [{
            'UID': 'paper2',
            'title': 'paper2 is cool',
            'abstract': 'Paper2 is about B'
        }]
    }, {
        'UID': 'paper2',
        'title': 'paper2 is cool',
        'abstract': 'Paper2 is about B',
        'references': []
    }, {
        'UID':
        'paper3',
        'title':
        'paper3 is cool',
        'abstract':
        'Paper3 is about C',
        'references': [{
            'UID': 'paper1',
            'title': 'paper1 is cool'
        }, {
            'UID': 'paper2',
            'title': 'paper2 is cool',
            'abstract': 'Paper2 is about B',
        }]
    }]


def test_prune_jsonl(input_jsonl, output_jsonl):

    result = utils.prune_jsonl(input_jsonl)

    print(result)
    assert result == output_jsonl
