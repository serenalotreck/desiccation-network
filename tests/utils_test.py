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
        'abstract':
        'Paper2 is about B',
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
        'UID':
        'paper1',
        'title':
        'paper1 is cool',
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
    # Hyphenated first name in reported name
    names_df = {
        'Registration_surname': [
            'One Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
            'Nine IsNine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
            'Fourteen-IsFourteen'
        ],
        'Registration_first_name': [
            'Person12', 'Person3', 'Person4', 'Person5', 'Person6 M.',
            'Person7', 'Person8', 'Person9 isperson9', 'Person10',
            'Person11 isPerson11', 'Person12', 'Person13',
            'Person14-isPerson14'
        ],
        'Alternative_name_1': [
            'Person12 A. T. C. One', np.nan, 'Person4 M.I. Four', np.nan,
            'Person6 Middle Six', 'P.M. Seven', 'Person8',
            'Person9-isperson9 N. IsNine', 'Person10 isPerson10 Tén',
            'P. isPerson11', 'Twelve Person12', 'isPerson13 Person13 Thirteen',
            'Person14 isPerson14 Fourteen IsFourteen'
        ],
        'Alternative_name_2': [
            np.nan, np.nan, 'Person4 M. Four', np.nan, np.nan,
            'Person7 M.I. Seven', np.nan, 'Person9 isperson9 Nine-IsNine',
            np.nan, 'Person11 isPérson11 Eleven', np.nan, 'i.P. Thirteen',
            np.nan
        ],
        'Alternative_name_3': [
            np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
            np.nan, np.nan, np.nan, np.nan, np.nan
        ],
        'Maiden_name': [
            np.nan, np.nan, np.nan, 'Alive', np.nan, np.nan, np.nan, np.nan,
            np.nan, np.nan, np.nan, np.nan, np.nan
        ]
    }
    return pd.DataFrame(names_df)


@pytest.fixture
def alt_name_output():
    return {
        'one two, p': [('one two', 'person12'), ('one', 'person12 a t c')],
        'three, p': [('three', 'person3')],
        'four, p': [('four', 'person4'), ('four', 'person4 m i'),
                    ('four', 'person4 m')],
        'five, p': [('five', 'person5'), ('alive', 'person5')],
        'six, pm': [('six', 'person6 m'), ('six', 'person6 middle')],
        'seven, p': [('seven', 'person7'), ('seven', 'p m'),
                     ('seven', 'person7 m i')],
        'eight, p': [('eight', 'person8'), ('person8', )],
        'nine isnine, pi': [('nine isnine', 'person9 isperson9'),
                            ('isnine', 'person9-isperson9 n'),
                            ('nine-isnine', 'person9 isperson9')],
        'ten, p': [('ten', 'person10'), ('tén', 'person10 isperson10')],
        'eleven, pi': [('eleven', 'person11 isperson11'), ('isperson11', 'p'),
                       ('eleven', 'person11 ispérson11')],
        'twelve, p': [('twelve', 'person12'), ('person12', 'twelve')],
        'thirteen, p': [('thirteen', 'person13'),
                        ('thirteen', 'isperson13 person13'),
                        ('thirteen', 'i p')],
        'fourteen-isfourteen, pi':
        [('fourteen-isfourteen', 'person14-isperson14'),
         ('fourteen isfourteen', 'person14 isperson14')]
    }


def test_process_alt_names(alt_name_input, alt_name_output):

    result = utils.process_alt_names(alt_name_input)

    assert result == alt_name_output


############################ find_author_papers ################################


@pytest.fixture
def attendees_input():
    attendees = {
        'Surname': ['One Two', 'Three', 'Four', 'Five', 'Six', 'Seven'],
        'First_name':
        ['Person12', 'Person3', 'Person4', 'Person5', 'Person6 M.', 'Person7'],
        'Affiliation': [
            'University 1', 'University 3', 'University 4', 'University 5',
            'University 6', 'University 7'
        ],
        'Country': [
            'Country 1', 'Country 3', 'Country 4', 'Country 5', 'Country 6',
            'Country 7'
        ]
    }
    return pd.DataFrame(attendees)


@pytest.fixture
def dataset_input():
    return [{
        'UID':
        'paper1',
        'authors': [{
            'display_name': 'One Two, Person12',
            'full_name': 'One Two, Person12',
            'wos_standard': 'One Two, P',
            'first_name': 'Person12',
            'last_name': 'One Two'
        }, {
            'display_name': 'Three, Person3',
            'full_name': 'Three, Person3',
            'wos_standard': 'Three, P',
            'first_name': 'Person3',
            'last_name': 'Three'
        }, {
            'display_name': 'Four, Person4 M.',
            'full_name': 'Four, Person4 M.',
            'wos_standard': 'Four, PM',
            'first_name': 'Person4 M.',
            'last_name': 'Four'
        }]
    }, {
        'UID':
        'paper3',
        'authors': [{
            'display_name': 'Alive, Person5',
            'full_name': 'Alive, Person5',
            'wos_standard': 'Alive, P',
            'first_name': 'Person5',
            'last_name': 'Alive'
        }, {
            'display_name': 'Four, Person4 M.',
            'full_name': 'Four, Person4 M.',
            'wos_standard': 'Four, PM',
            'first_name': 'Person4 M.',
            'last_name': 'Four'
        }, {
            'display_name': 'Three, Person3',
            'full_name': 'Three, Person3',
            'wos_standard': 'Three, P',
            'first_name': 'Person3',
            'last_name': 'Three'
        }, {
            'display_name': 'Thirteen, Person13',
            'full_name': 'Thirteen, Person13',
            'wos_standard': 'Thirteen, P',
            'first_name': 'Person13',
            'last_name': 'Thirteen'
        }]
    }, {
        'UID':
        'paper5',
        'authors': [{
            'display_name': 'One, Person12 A. T. C.',
            'full_name': 'One, Person12 A. T. C.',
            'wos_standard': 'One, PATC',
            'first_name': 'Person12 A. T. C.',
            'last_name': 'One'
        }, {
            'display_name': 'Three, Person3',
            'full_name': 'Three, Person3',
            'wos_standard': 'Three, P',
            'first_name': 'Person3',
            'last_name': 'Three'
        }]
    }, {
        'UID':
        'paper6',
        'authors': [{
            'display_name': 'Four, Person4 M.',
            'full_name': 'Four, Person4 M.',
            'wos_standard': 'Four, PM',
            'first_name': 'Person4 M.',
            'last_name': 'Four'
        }, {
            'display_name': 'Five, Person5',
            'full_name': 'Five, Person5',
            'wos_standard': 'Five, P',
            'first_name': 'Person5',
            'last_name': 'Five'
        }, {
            'display_name': 'Fifteen, Person15',
            'full_name': 'Fifteen, Person15',
            'wos_standard': 'Fifteen, P',
            'first_name': 'Person5',
            'last_name': 'Fifteen'
        }]
    }, {
        'UID':
        'paper7',
        'authors': [{
            'display_name': 'Seven, P.M.',
            'full_name': 'Seven, P.M.',
            'wos_standard': 'Seven, PM',
            'first_name': 'P.M.',
            'last_name': 'Seven'
        }, {
            'display_name': 'One Two, Person12',
            'full_name': 'One Two, Person12',
            'wos_standard': 'One Two, P',
            'first_name': 'Person12',
            'last_name': 'One Two'
        }]
    }, {
        'UID':
        'paper8',
        'authors': [{
            'display_name': 'Three, Person3',
            'full_name': 'Three, Person3',
            'wos_standard': 'Three, P',
            'first_name': 'Person3',
            'last_name': 'Three'
        }, {
            'display_name': 'One Two, Person12',
            'full_name': 'One Two, Person12',
            'wos_standard': 'One Two, P',
            'first_name': 'Person12',
            'last_name': 'One Two'
        }]
    }, {
        'UID':
        'paper9',
        'authors': [{
            'display_name': 'Three, Person3',
            'full_name': 'Three, Person3',
            'wos_standard': 'Three, P',
            'first_name': 'Person3',
            'last_name': 'Three'
        }, {
            'display_name': 'Alive, Person4',
            'full_name': 'Alive, Person4',
            'wos_standard': 'Alive, P',
            'first_name': 'Person4',
            'last_name': 'Alive'
        }]
    }]


@pytest.fixture
def conference_authors():
    return {
        'one two, p': ['paper1', 'paper5', 'paper7', 'paper8'],
        'three, p': ['paper1', 'paper3', 'paper5', 'paper8', 'paper9'],
        'four, p': ['paper1', 'paper3', 'paper6'],
        'five, p': ['paper3', 'paper6', 'paper9'],
        'six, pm': [],
        'seven, p': ['paper7'],
        'eight, p': [],
        'nine isnine, pi': [],
        'ten, p': [],
        'eleven, pi': [],
        'twelve, p': [],
        'thirteen, p': ['paper3'],
        'fourteen-isfourteen, pi': []
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
        'seven pmi': 'seven, p',
        'person8': 'eight, p',
        'eight, person8': 'eight, p',
        'eight, p': 'eight, p',
        'eight p': 'eight, p',
        'nine isnine, person9 isperson9': 'nine isnine, pi',
        'nine isnine, pi': 'nine isnine, pi',
        'nine isn.pi': 'nine isnine, pi',
        'isnine, person9-isperson9 n': 'nine isnine, pi',
        'isnine, pin': 'nine isnine, pi',
        'isnine pin': 'nine isnine, pi',
        'nine-isnine, person9 isperson9': 'nine isnine, pi',
        'nine-isnine, pi': 'nine isnine, pi',
        'nine-isn.pi': 'nine isnine, pi',
        'ten, person10': 'ten, p',
        'ten, p': 'ten, p',
        'ten p': 'ten, p',
        'tén, person10 isperson10': 'ten, p',
        'tén, pi': 'ten, p',
        'tén pi': 'ten, p',
        'eleven, person11 isperson11': 'eleven, pi',
        'eleven, pi': 'eleven, pi',
        'eleven pi': 'eleven, pi',
        'isperson11, p': 'eleven, pi',
        'isperson.p': 'eleven, pi',
        'eleven, person11 ispérson11': 'eleven, pi',
        'twelve, person12': 'twelve, p',
        'twelve, p': 'twelve, p',
        'twelve p': 'twelve, p',
        'person12, twelve': 'twelve, p',
        'person12, t': 'twelve, p',
        'person12 t': 'twelve, p',
        'thirteen, person13': 'thirteen, p',
        'thirteen, p': 'thirteen, p',
        'thirteen p': 'thirteen, p',
        'thirteen, isperson13 person13': 'thirteen, p',
        'thirteen, ip': 'thirteen, p',
        'thirteen ip': 'thirteen, p',
        'fourteen-isfourteen, person14-isperson14': 'fourteen-isfourteen, pi',
        'fourteen-isfourteen, pi': 'fourteen-isfourteen, pi',
        'fourteen.pi': 'fourteen-isfourteen, pi',
        'fourteen isfourteen, person14 isperson14': 'fourteen-isfourteen, pi',
        'fourteen isfourteen, pi': 'fourteen-isfourteen, pi',
    }


def test_find_author_papers_conf_auth(attendees_input, dataset_input,
                                      alt_name_output, conference_authors):

    res_auths, res_alts = utils.find_author_papers(attendees_input,
                                                   dataset_input,
                                                   alt_name_output)

    assert res_auths == conference_authors


def test_find_author_papers_proc_alt(attendees_input, dataset_input,
                                     alt_name_output, processed_alt_names):

    res_auths, res_alts = utils.find_author_papers(attendees_input,
                                                   dataset_input,
                                                   alt_name_output)

    assert res_alts == processed_alt_names


########################## get_geographic_locations ###########################


@pytest.fixture
def geo_dataset():
    return [
        # Standard
        {
            'UID':
            'WOS:000346894900059',
            'title':
            'The effects of short- and long-term freezing on Porphyra umbilicalis Kutzing (Bangiales, Rhodophyta) blade viability',
            'year':
            '2014',
            'authors': [{
                'seq_no': '1',
                'role': 'author',
                'reprint': 'Y',
                'addr_no': '1',
                'display_name': 'Green, Lindsay A.',
                'full_name': 'Green, Lindsay A.',
                'wos_standard': 'Green, LA',
                'first_name': 'Lindsay A.',
                'last_name': 'Green',
                'email_addr': 'lindsaygreen@mail.uri.edu'
            }, {
                'seq_no': '2',
                'role': 'author',
                'addr_no': '1',
                'display_name': 'Neefus, Christopher D.',
                'full_name': 'Neefus, Christopher D.',
                'wos_standard': 'Neefus, CD',
                'first_name': 'Christopher D.',
                'last_name': 'Neefus'
            }],
            'addresses': [{
                'addr_no': '1',
                'full_address':
                'Univ New Hampshire, Dept Biol Sci, Durham, NH 03824 USA',
                'city': 'Durham',
                'state': 'NH',
                'country': 'USA',
                'zip': '03824'
            }],
            'references': [],  # Manually removed for visual simplicity
            'abstract':
            '',  # Manually removed for visual simplicity
            'static_keys': [
                'Ecology', 'Marine & Freshwater Biology',
                'Environmental Sciences & Ecology',
                'Marine & Freshwater Biology'
            ],
            'paper_keywords': [
                'Porphyra umbilicalis', 'Freezing', 'Viability', 'Zonation',
                'Preservation', 'Ecophysiology'
            ],
            'dynamic_keys': [
                'Agriculture, Environment & Ecology', 'Marine Biology',
                'Rhodophyta'
            ]
        },
        # No affiliations
        {
            'UID':
            'WOS:A1996WB08200007',
            'title':
            'Plant cellular responses to water deficit',
            'year':
            '1996',
            'authors': [{
                'seq_no': '1',
                'role': 'author',
                'reprint': 'Y',
                'display_name': 'Mullet, JE',
                'full_name': 'Mullet, JE',
                'wos_standard': 'Mullet, JE',
                'first_name': 'JE',
                'last_name': 'Mullet'
            }, {
                'seq_no': '2',
                'role': 'author',
                'display_name': 'Whitsitt, MS',
                'full_name': 'Whitsitt, MS',
                'wos_standard': 'Whitsitt, MS',
                'first_name': 'MS',
                'last_name': 'Whitsitt'
            }],
            'references': [],
            'addresses': [],
            'abstract':
            'Water availability and drought limit crop yields worldwide. The responses of plants to drought vary greatly depending on species and stress severity. These responses include changes in plant growth, accumulation of solutes, changes in carbon and nitrogen metabolism, and alterations in gene expression. In this article, we review cellular and molecular responses to water deficit, and their influence on plant dehydration tolerance.',
            'static_keys': ['Plant Sciences', 'Plant Sciences'],
            'paper_keywords': [],
            'dynamic_keys': [
                'Agriculture, Environment & Ecology', 'Crop Science',
                'Salt Stress'
            ]
        },
        # Mixed xountry addresses with no addr_no
        {
            'UID':
            'WOS:000236647400002',
            'title':
            'Low- and high-temperature vitrification as a new approach to bio stabilization of reproductive and progenitor cells',
            'year':
            '2006',
            'authors': [{
                'seq_no': '1',
                'role': 'author',
                'reprint': 'Y',
                'display_name': 'Katkov, II',
                'full_name': 'Katkov, II',
                'wos_standard': 'Katkov, II',
                'last_name': 'Katkov',
                'suffix': 'II',
                'email_addr': 'prodvincell@hotmail.com'
            }, {
                'seq_no': '2',
                'role': 'author',
                'display_name': 'Isachenko, V',
                'full_name': 'Isachenko, V',
                'wos_standard': 'Isachenko, V',
                'last_name': 'Isachenko',
                'suffix': 'V'
            }, {
                'seq_no': '3',
                'role': 'author',
                'display_name': 'Isachenko, E',
                'full_name': 'Isachenko, E',
                'wos_standard': 'Isachenko, E',
                'first_name': 'E',
                'last_name': 'Isachenko'
            }, {
                'seq_no': '4',
                'role': 'author',
                'display_name': 'Kim, MS',
                'full_name': 'Kim, MS',
                'wos_standard': 'Kim, MS',
                'first_name': 'MS',
                'last_name': 'Kim'
            }, {
                'seq_no': '5',
                'role': 'author',
                'display_name': 'Lulat, AGMI',
                'full_name': 'Lulat, AGMI',
                'wos_standard': 'Lulat, AGMI',
                'first_name': 'AGMI',
                'last_name': 'Lulat'
            }, {
                'seq_no': '6',
                'role': 'author',
                'display_name': 'Mackay, AM',
                'full_name': 'Mackay, AM',
                'wos_standard': 'Mackay, AM',
                'first_name': 'AM',
                'last_name': 'Mackay'
            }, {
                'seq_no': '7',
                'role': 'author',
                'display_name': 'Levine, F',
                'full_name': 'Levine, F',
                'wos_standard': 'Levine, F',
                'first_name': 'F',
                'last_name': 'Levine'
            }],
            'references': [],
            'addresses': [{
                'addr_no': '1',
                'full_address':
                'Univ Calif San Diego, Ctr Canc, San Diego, CA 92121 USA',
                'city': 'San Diego',
                'state': 'CA',
                'country': 'USA',
                'zip': '92121'
            }, {
                'addr_no': '2',
                'full_address':
                'Univ Bonn, Dept Endocrinol & Reprod Med, D-5300 Bonn, Germany',
                'city': 'Bonn',
                'country': 'Germany',
                'zip': 'D-5300'
            }, {
                'addr_no': '3',
                'full_address':
                'Univ Calif San Diego, Dept Bioengn, San Diego, CA 92103 USA',
                'city': 'San Diego',
                'state': 'CA',
                'country': 'USA',
                'zip': '92103'
            }, {
                'addr_no': '4',
                'full_address': 'Stem Sci, Toronto, ON, Canada',
                'city': 'Toronto',
                'state': 'ON',
                'country': 'Canada'
            }, {
                'addr_no': '5',
                'full_address': 'Osiris Therapeut Inc, Baltimore, MD USA',
                'city': 'Baltimore',
                'state': 'MD',
                'country': 'USA'
            }],
            'abstract':
            "",
            'static_keys': [
                'Thermodynamics', 'Engineering, Mechanical', 'Thermodynamics',
                'Engineering'
            ],
            'paper_keywords': [
                'cryogenics', 'cryoprotection', 'process', 'cryoprescrvation',
                'cell', 'sperm'
            ],
            'dynamic_keys': [
                'Clinical & Life Sciences', 'Reproductive Biology',
                'Cryosurgery'
            ]
        },
        # Multiple affiliations
        {
            'UID':
            'WOS:000401445300009',
            'title':
            'Physiological responses of artificial moss biocrusts to dehydration-rehydration process and heat stress on the Loess Plateau, China',
            'year':
            '2017',
            'authors': [{
                'seq_no': '1',
                'role': 'author',
                'reprint': 'Y',
                'addr_no': '1 2 3',
                'display_name': 'Bu Chongfeng',
                'full_name': 'Bu Chongfeng',
                'wos_standard': 'Bu, CF',
                'last_name': 'Bu Chongfeng',
                'email_addr': 'buchongfeng@163.com'
            }, {
                'seq_no': '2',
                'role': 'author',
                'addr_no': '1',
                'display_name': 'Wang Chun',
                'full_name': 'Wang Chun',
                'wos_standard': 'Wang, C',
                'last_name': 'Wang Chun'
            }, {
                'seq_no': '3',
                'role': 'author',
                'addr_no': '4',
                'display_name': 'Yang Yongsheng',
                'full_name': 'Yang Yongsheng',
                'wos_standard': 'Yang, YS',
                'last_name': 'Yang Yongsheng'
            }, {
                'seq_no': '4',
                'role': 'author',
                'addr_no': '5',
                'display_name': 'Zhang Li',
                'full_name': 'Zhang Li',
                'wos_standard': 'Zhang, L',
                'last_name': 'Zhang Li'
            }, {
                'seq_no': '5',
                'role': 'author',
                'addr_no': '6',
                'display_name': 'Bowker, Matthew A.',
                'full_name': 'Bowker, Matthew A.',
                'wos_standard': 'Bowker, MA',
                'first_name': 'Matthew A.',
                'last_name': 'Bowker'
            }],
            'references': [],
            'addresses': [{
                'addr_no': '1',
                'full_address':
                'Northwest A&F Univ, Inst Soil & Water Conservat, Yangling 712100, Peoples R China',
                'city': 'Yangling',
                'country': 'Peoples R China',
                'zip': '712100'
            }, {
                'addr_no': '2',
                'full_address':
                'Chinese Acad Sci, Inst Soil & Water Conservat, Yangling 712100, Peoples R China',
                'city': 'Yangling',
                'country': 'Peoples R China',
                'zip': '712100'
            }, {
                'addr_no': '3',
                'full_address':
                'Minist Water Resources, Yangling 712100, Peoples R China',
                'city': 'Yangling',
                'country': 'Peoples R China',
                'zip': '712100'
            }, {
                'addr_no': '4',
                'full_address':
                'Chinese Acad Sci, Northwest Inst Plateau Biol, Xining 810001, Peoples R China',
                'city': 'Xining',
                'country': 'Peoples R China',
                'zip': '810001'
            }, {
                'addr_no': '5',
                'full_address':
                'Qinghai Remote Sensing Monitoring Ctr Ecoenvironm, Xining 810001, Peoples R China',
                'city': 'Xining',
                'country': 'Peoples R China',
                'zip': '810001'
            }, {
                'addr_no': '6',
                'full_address':
                'No Arizona Univ, Sch Forestry, Flagstaff, AZ 86011 USA',
                'city': 'Flagstaff',
                'state': 'AZ',
                'country': 'USA',
                'zip': '86011'
            }],
            'abstract':
            '',
            'static_keys':
            ['Environmental Sciences', 'Environmental Sciences & Ecology'],
            'paper_keywords': [
                'dehydration-rehydration', 'heat stress',
                'Didymodon vinealis (Brid.) Zand.', 'resistance',
                'Loess Plateau'
            ],
            'dynamic_keys':
            ['Agriculture, Environment & Ecology', 'Forestry', 'Rangelands']
        }
    ]

@pytest.fixture
def geo_locations():
    return {
            'bu, cf': 'CHN',
            'yang, ys': 'CHN',
            'wang, c': 'CHN',
            'zhang, l': 'CHN',
            'bowker, ma': 'USA',
            'green, la': 'USA',
            'neefus, cd': 'USA'
            }

def test_get_geographic_locations(geo_dataset, geo_locations):

    result = utils.get_geographic_locations(geo_dataset)

    assert result == geo_locations


