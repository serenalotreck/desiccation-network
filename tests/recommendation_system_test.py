"""
Spot checks for recommendation_system.py

Author: Serena G. Lotreck
"""
import pytest
import sys
sys.path.append('../desiccation_network/conference_recommendation')
from recommendation_system import RecommendationSystem
import pandas as pd
import numpy as np


@pytest.fixture
def paper_dataset():
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


            {'display_name': 'Eight, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }
            {'display_name': 'Alive, Person4',
                'full_name': 'Alive, Person4',
                'wos_standard': 'Alive, P',
                'first_name': 'Person4',
                'last_name': 'Alive'
            }


@pytest.fixture
def alt_names():
    names_df = {
        'Registration_surname': ['One Two', 'Three', 'Four', 'Five', 'Six', 'Seven'],
        'Registration_first_name': ['Person12', 'Person3', 'Person4', 'Person5', 'Person6 M.', 'Person7'],
        'Alternative_name_1': ['Person12 A. T. C. One', np.nan, 'Person4 M.I. Four', np.nan, 'Person6 Middle Six', 'P.M. Seven'],
        'Alternative_name_2': [np.nan, np.nan, 'Person4 M. Four', np.nan, np.nan, 'Person7 M.I. Seven'],
        'Alternative_name_3': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        'Maiden_name':[np.nan, np.nan, np.nan, 'Alive', np.nan, np.nan]
    }
    return pd.DataFrame(names_df)

@pytest.fixture
def basic_rec_instance(paper_dataset, alt_names):
    """
    Set required attrs that we don't use in tests (because they use external
    packages to produce an unpredictable output) to None. 
    """
    rec = RecommendationSystem(
        paper_dataset,
        None,
        None,
        None,
        None,
        None,
        alt_names
        )
    rec.set_paper_authors()
    rec.set_author_papers()
    return rec


############################ set_topics_to_authors #############################
@pytest.fixture
def paper_to_topic():
    """
    Normally set as part of fit_topic_model.
    """
    return {
        'paper1': 0,
        'paper3': 1,
        'paper5': 0,
        'paper6': 2,
        'paper7': 1,
        'paper8': 2,
        'paper9': 1
    }

@pytest.fixture
def topics_to_authors():
    return {
        0: list(set(['one two, p', 'three, p', 'four, pm', 'one, patc'])),
        1: list(set(['seven, pm', 'one two, p', 'three, p', 'alive, p', 'four, pm', 'thirteen, p'])),
        2: list(set(['four, pm', 'five, p', 'fifteen, p', 'three, p', 'one two, p']))
    }

def test_set_topics_to_authors(basic_rec_instance, paper_to_topic, topics_to_authors):
    
    basic_rec_instance.paper_to_topic = paper_to_topic
    
    basic_rec_instance.set_topics_to_authors()
    result = basic_rec_instance.topics_to_authors
    
    assert result == topics_to_authors


########################### calculate_topic_pa_score ###########################

@pytest.fixture
def author():
    return 'one two, p'

@pytest.fixture
def enriched_topic_clusters():
    # For the purposes of this test, authors seven, three, and thirteen are conf
    # authors
    return [0, 1]

@pytest.fixture
def mean_topic_score():
    return 1/3

def test_calculate_topic_pa_score(author, topics_to_authors, enriched_topic_clusters, mean_topic_score):
    
    result = RecommendationSystem.calculate_topic_pa_score(author, topics_to_authors, enriched_topic_clusters)
    
    assert result == mean_topic_score


########################### calculate_co_hier_score ############################

@pytest.fixture
def author_letter():
    return 'D9'

@pytest.fixture
def cluster_distances():
    return {
        'D1': {'0-0': 1, '0-1': 1, '0-2': 2, '1-0': 4, '1-1': 4, '1-2': 4, '2-0': 4},
        'D2': {'0-0': 2, '0-1': 3, '0-2': 3, '1-0': 2, '1-1': 3, '1-2': 3, '2-0': 4},
        'D3': {'0-0': 2, '0-1': 3, '0-2': 3, '1-0': 3, '1-1': 2, '1-2': 3, '2-0': 4},
        'D4': {'0-0': 3, '0-1': 2, '0-2': 3, '1-0': 4, '1-1': 4, '1-2': 4, '2-0': 2},
        'D5': {'0-0': 2, '0-1': 0, '0-2': 2, '1-0': 4, '1-1': 4, '1-2': 4, '2-0': 4},
        'D6': {'0-0': 3, '0-1': 3, '0-2': 2, '1-0': 4, '1-1': 4, '1-2': 4, '2-0': 2},
        'D7': {'0-0': 3, '0-1': 3, '0-2': 2, '1-0': 3, '1-1': 3, '1-2': 2, '2-0': 4},
        'D8': {'0-0': 2, '0-1': 2, '0-2': 0, '1-0': 4, '1-1': 4, '1-2': 4, '2-0': 4},
        'D9': {'0-0': 4, '0-1': 4, '0-2': 4, '1-0': 2, '1-1': 2, '1-2': 8/3, '2-0': 8/3},
        'D10': {'0-0': 4, '0-1': 4, '0-2': 4, '1-0': 2, '1-1': 3, '1-2': 3, '2-0': 2}
    }

@pytest.fixture
def enriched_hier_clusters():
    return ['0-0', '0-2', '1-2', '2-0']

@pytest.fixture
def mean_hier_score():
    return 0.5

def test_calculate_mean_hier_score(author_letter, cluster_distances, enriched_hier_clusters, mean_hier_score):
    
    result = RecommendationSystem.calculate_mean_hier_score(author_letter, cluster_distances, enriched_hier_clusters)
    
    assert result == mean_hier_score
