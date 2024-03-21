"""
Test citation network utils.py.

Author: Serena G. Lotreck
"""
import pytest
import networkx as nx
import numpy as np
import pandas as pd
import sys

sys.path.append('../desiccation_network/conference_recommendation')
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


############################## process_alt_names ###############################

@pytest.fixture
def alt_name_input():
    # Tests:
    # Person with second part of surname as initials
    # Person with no alternative names
    # Person with two sets of middle initials
    # Spaces between initials
    # No spaces between initials
    # Person with maiden name and no other alternatives
    # Registration name is initialized but other names are not
    # Initialized first and middle in publications
    # Single name on publication (aka no surname)
    # Different hyphenation of first name plus exclusion of middle name
    # Additional middle/surname plus accented letter differences
    # Dropped last surname
    # Swapped first and last name
    # Additional first name
    names_df = {
        'Registration_surname': ['One Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine IsNine', 'Ten', 'Eleven', 'Twelve', 'Thirteen'],
        'Registration_first_name': ['Person12', 'Person3', 'Person4', 'Person5', 'Person6 M.', 'Person7', 'Person8', 'Person9 isperson9',  'Person10', 'Person11 isPerson11', 'Person12', 'Person13'],
        'Alternative_name_1': ['Person12 A. T. C. One', np.nan, 'Person4 M.I. Four', np.nan, 'Person6 Middle Six', 'P.M. Seven', 'Person8', 'Person9-isperson9 N. IsNine', 'Person10 isPerson10 Tén', 'P. isPerson11', 'Twelve Person12', 'isPerson13 Person13 Thirteen'],
        'Alternative_name_2': [np.nan, np.nan, 'Person4 M. Four', np.nan, np.nan, 'Person7 M.I. Seven', np.nan, 'Person 9 isperson9 Nine-IsNine', np.nan, 'Person11 isPérson11 Eleven', np.nan, 'i.P. Thirteen'],
        'Alternative_name_3': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        'Maiden_name':[np.nan, np.nan, np.nan, 'Alive', np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
    }
    return pd.DataFrame(names_df)

@pytest.fixture
def alt_name_output():
    return {
        'one two, p': [('one two', 'person12'), ('one', 'person12 a t c')],
        'three, p': [('three', 'person3')],
        'four, p': [('four', 'person4'), ('four', 'person4 m i'), ('four', 'person4 m')],
        'five, p': [('five', 'person5'), ('alive', 'person5')],
        'six, pm': [('six', 'person6 m'), ('six', 'person6 middle')],
        'seven, p': [('seven', 'person7'), ('seven', 'p m'), ('seven', 'person7 m i')],
        'eight, p': [('eight', 'person8'), ('person8',)],
        'nine isnine, pi': [('nine is nine', 'person9 isperson9'), ('isnine',  'person9-isperson9 n'), ('nine-isnine', 'person9 isperson9')],
        'ten, p': [('ten', 'person10'), ('tén', 'person10 isperson10')],
        'eleven, pi': [('eleven', 'person11 isperson11'), ('isperson11', 'p'), ('eleven', 'person11 ispérson11')],
        'twelve, p': [('twelve', 'person12'), ('person12', 'twelve')],
        'thirteen, p': [('thirteen', 'person13'), ('thirteen', 'isperson13 person13'), ('thirteen', 'i p')]
    }


def test_process_alt_names(alt_name_input, alt_name_output):
    
    result = utils.process_alt_names(alt_name_input)
    
    
    assert result == alt_name_output


############################ find_author_papers ################################

@pytest.fixture
def attendees_input():
    attendees = {
        'Surname': ['One Two', 'Three', 'Four', 'Five', 'Six', 'Seven'],
        'First_name': ['Person12', 'Person3', 'Person4', 'Person5', 'Person6 M.', 'Person7'],
        'Affiliation': ['University 1', 'University 3', 'University 4', 'University 5', 'University 6', 'University 7'],
        'Country': ['Country 1', 'Country 3', 'Country 4', 'Country 5', 'Country 6', 'Country 7']
    }
    return pd.DataFrame(attendees)

@pytest.fixture
def dataset_input():
    return [
        {'UID': 'paper1', 'authors': [
            {'display_name': 'One Two, Person12',
                'full_name': 'One Two, Person12',
                'wos_standard': 'One Two, P',
                'first_name': 'Person12',
                'last_name': 'One Two'
            },
            {'display_name': 'Three, Person3',
                'full_name': 'Three, Person3',
                'wos_standard': 'Three, P',
                'first_name': 'Person3',
                'last_name': 'Three'
            },
            {'display_name': 'Four, Person4 M.',
                'full_name': 'Four, Person4 M.',
                'wos_standard': 'Four, PM',
                'first_name': 'Person4 M.',
                'last_name': 'Four'
            }
            ]},
        {'UID': 'paper3', 'authors': [
            {'display_name': 'Alive, Person5',
                'full_name': 'Alive, Person5',
                'wos_standard': 'Alive, P',
                'first_name': 'Person5',
                'last_name': 'Alive'
            },
            {'display_name': 'Four, Person4 M.',
                'full_name': 'Four, Person4 M.',
                'wos_standard': 'Four, PM',
                'first_name': 'Person4 M.',
                'last_name': 'Four'
            },
            {'display_name': 'Three, Person3',
                'full_name': 'Three, Person3',
                'wos_standard': 'Three, P',
                'first_name': 'Person3',
                'last_name': 'Three'
            },
            {'display_name': 'Thirteen, Person13',
                'full_name': 'Thirteen, Person13',
                'wos_standard': 'Thirteen, P',
                'first_name': 'Person13',
                'last_name': 'Thirteen'
            }
            ]},
        {'UID': 'paper5', 'authors': [
            {'display_name': 'One, Person12 A. T. C.',
                'full_name': 'One, Person12 A. T. C.',
                'wos_standard': 'One, PATC',
                'first_name': 'Person12 A. T. C.',
                'last_name': 'One'
            },
            {'display_name': 'Three, Person3',
                'full_name': 'Three, Person3',
                'wos_standard': 'Three, P',
                'first_name': 'Person3',
                'last_name': 'Three'
            }
            ]},
        {'UID': 'paper6', 'authors': [
            {'display_name': 'Four, Person4 M.',
                'full_name': 'Four, Person4 M.',
                'wos_standard': 'Four, PM',
                'first_name': 'Person4 M.',
                'last_name': 'Four'
            },
            {'display_name': 'Five, Person5',
                'full_name': 'Five, Person5',
                'wos_standard': 'Five, P',
                'first_name': 'Person5',
                'last_name': 'Five'
            },
            {'display_name': 'Fifteen, Person15',
                'full_name': 'Fifteen, Person15',
                'wos_standard': 'Fifteen, P',
                'first_name': 'Person5',
                'last_name': 'Fifteen'
            }
            ]},
        {'UID': 'paper7', 'authors': [
            {'display_name': 'Seven, P.M.',
                'full_name': 'Seven, P.M.',
                'wos_standard': 'Seven, PM',
                'first_name': 'P.M.',
                'last_name': 'Seven'
            },
            {'display_name': 'One Two, Person12',
                'full_name': 'One Two, Person12',
                'wos_standard': 'One Two, P',
                'first_name': 'Person12',
                'last_name': 'One Two'
            }
            ]},
        {'UID': 'paper8', 'authors': [
            {'display_name': 'Three, Person3',
                'full_name': 'Three, Person3',
                'wos_standard': 'Three, P',
                'first_name': 'Person3',
                'last_name': 'Three'
            },
            {'display_name': 'One Two, Person12',
                'full_name': 'One Two, Person12',
                'wos_standard': 'One Two, P',
                'first_name': 'Person12',
                'last_name': 'One Two'
            }
            ]},
        {'UID': 'paper9', 'authors': [
            {'display_name': 'Three, Person3',
                'full_name': 'Three, Person3',
                'wos_standard': 'Three, P',
                'first_name': 'Person3',
                'last_name': 'Three'
            },
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            ]}
        ]

@pytest.fixture
def conference_authors():
    return {
        'one two, p': ['paper1', 'paper5', 'paper7', 'paper8'],
        'three, p': ['paper1', 'paper3', 'paper5', 'paper8', 'paper9'],
        'four, p': ['paper1', 'paper3', 'paper6'],
        'five, p': ['paper3', 'paper6', 'paper9'],
        'six, pm': [],
        'seven, p': ['paper7']
    }

@pytest.fixture
def processed_alt_names():
    return {
        'one, patc': 'one two, p',
        'one, person12 atc': 'one two, p',
        'one two, p': 'one two, p',
        'one two, person12': 'one two, p',
        'one patc': 'one two, p',
        'one two p': 'one two, p',
        'three, p': 'three, p',
        'three, person3': 'three, p',
        'three p': 'three, p',
        'four, person4': 'four, p',
        'four, p': 'four, p',
        'four p': 'four, p',
        'four, person4 mi': 'four, p',
        'four, pmi': 'four, p',
        'four pmi': 'four, p',
        'four, person4 m': 'four, p',
        'four, pm': 'four, p',
        'four pm': 'four, p',
        'five, person5': 'five, p',
        'five, p': 'five, p',
        'five p': 'five, p',
        'alive, person5': 'five, p',
        'alive, p': 'five, p',
        'alive p': 'five, p',
        'six, person6 m': 'six, pm',
        'six, pm': 'six, pm',
        'six pm': 'six, pm',
        'six, person6 middle': 'six, pm',
        'seven, person7': 'seven, p',
        'seven, p': 'seven, p',
        'seven p': 'seven, p',
        'seven, pm': 'seven, p',
        'seven pm': 'seven, p',
        'seven, person7 mi': 'seven, p',
        'seven, pmi': 'seven, p',
        'seven pmi': 'seven, p'
    }


def test_find_author_papers_conf_auth(attendees_input, dataset_input, alt_name_output, conference_authors):
    
    res_auths, res_alts = utils.find_author_papers(attendees_input, dataset_input, alt_name_output)
    
    assert res_auths == conference_authors

def test_find_author_papers_proc_alt(attendees_input, dataset_input, alt_name_output, processed_alt_names):
    
    res_auths, res_alts = utils.find_author_papers(attendees_input, dataset_input, alt_name_output)
    
    assert res_alts == processed_alt_names