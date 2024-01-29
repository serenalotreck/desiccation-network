"""
Spot checks for descriptive_stats.py

Author: Serena G. Lotreck
"""
import pytest
import sys

sys.path.append('../citation_network')
import descriptive_stats as ds

############################## flatten_papers ##################################


@pytest.fixture
def input_jsonl():
    return [{
        'UID':
        'paper1',
        'title':
        'paper1 is cool',
        'year':
        '2007',
        'references': [{
            'UID': 'paper2',
            'title': 'paper2 is cool'
        }, {
            'UID': 'ref1',
            'title': 'ref1 is cool',
            'year': '1998'
        }, {
            'UID': 'ref2',
            'title': 'ref2 is cool',
            'abstract': 'ref2 is extra cool'
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
        'year':
        '1986',
        'references': [{
            'UID': 'ref1',
            'title': 'ref1 is cool',
            'year': '1998'
        }, {
            'UID': 'ref2',
            'title': 'ref2 is cool',
            'abstract': 'ref2 is extra cool'
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
def output_dict():
    return {
        'paper1': {
            'title': 'paper1 is cool',
            'year': '2007',
        },
        'paper2': {
            'title': 'paper2 is cool',
            'abstract': 'Paper2 is about B',
            'year': '1986'
        },
        'paper3': {
            'title': 'paper3 is cool',
            'abstract': 'Paper3 is about C'
        }  #, # Uncomment to include references in test
        # 'ref1': {'title': 'ref1 is cool', 'year': '1998'},
        # 'ref2': {'title': 'ref2 is cool', 'abstract': 'ref2 is extra cool'},
        # 'ref3': {'title': 'ref3 is cool'}
    }


def test_flatten_papers(input_jsonl, output_dict):

    result = ds.flatten_papers(input_jsonl, 'UID')

    assert result == output_dict


############################### get_overall_years ##############################


@pytest.fixture
def flattened_papers():
    return {
        'paper1': {
            'title': 'paper1 is cool',
            'year': '2007'
        },
        'paper2': {
            'title': 'paper2 is cool',
            'abstract': 'Paper2 is about B',
            'year': '1986'
        },
        'paper3': {
            'title': 'paper3 is cool',
            'abstract': 'Paper3 is about C',
            'year': '2021'
        },
        'paper4': {
            'title': 'paper4 is cool',
            'year': '2019'
        },
        'paper5': {
            'title': 'paper5 is cool',
            'abstract': 'Paper5 is about B',
            'year': '2005'
        },
        'paper6': {
            'title': 'paper6 is cool',
            'abstract': 'Paper6 is about C'
        },
        'paper7': {
            'title': 'paper7 is cool',
            'year': '2010'
        },
        'paper8': {
            'title': 'paper8 is cool',
            'abstract': 'Paper8 is about B',
            'year': '1997'
        },
        'paper9': {
            'title': 'paper9 is cool',
            'abstract': 'Paper9 is about C',
            'year': '2023'
        },
        'paper10': {
            'title': 'paper10 is cool',
            'year': '2001'
        },
        'paper11': {
            'title': 'paper11 is cool',
            'abstract': 'Paper11 is about B',
            'year': '1999'
        },
        'paper12': {
            'title': 'paper12 is cool',
            'abstract': 'Paper12 is about C',
            'year': '2017'
        },
        'paper13': {
            'title': 'paper13 is cool',
            'year': '2017'
        },
        'paper14': {
            'title': 'paper14 is cool',
            'abstract': 'Paper14 is about B',
            'year': '2021'
        },
        'paper15': {
            'title': 'paper15 is cool',
            'abstract': 'Paper15 is about C',
            'year': '2022'
        },
        'paper16': {
            'title': 'paper16 is cool',
            'year': '2023'
        },
        'paper17': {
            'title': 'paper17 is cool',
            'abstract': 'Paper17 is about B',
            'year': '1978'
        },
        'paper18': {
            'title': 'paper18 is cool',
            'abstract': 'Paper18 is about C',
            'year': '2015'
        }
    }


@pytest.fixture
def paper_years():
    return [
        2007, 1986, 2021, 2019, 2005, 2010, 1997, 2023, 2001, 1999, 2017, 2017,
        2021, 2022, 2023, 1978, 2015
    ]


def test_get_overall_years(flattened_papers, paper_years):

    result = ds.get_overall_years(flattened_papers)

    assert result == paper_years


######################### get_overall_cumulative_years #########################


@pytest.fixture
def cumulative_years():
    return {
        1978: 1 / 1000,
        1986: 2 / 1000,
        1997: 3 / 1000,
        1999: 4 / 1000,
        2001: 5 / 1000,
        2005: 6 / 1000,
        2007: 7 / 1000,
        2010: 8 / 1000,
        2015: 9 / 1000,
        2017: 11 / 1000,
        2019: 12 / 1000,
        2021: 14 / 1000,
        2022: 15 / 1000,
        2023: 17 / 1000
    }


def test_get_overall_cumulative_years(paper_years, cumulative_years):

    result = ds.get_overall_cumulative_years(paper_years)

    assert result == cumulative_years


############################# get_per_class_years ##############################


@pytest.fixture
def paper_classifications():
    return {
        'paper1': 'Plant',
        'paper2': 'Plant',
        'paper3': 'Plant',
        'paper4': 'Plant',
        'paper5': 'Microbe',
        'paper6': 'Microbe',
        'paper7': 'Plant',
        'paper8': 'Animal',
        'paper9': 'Plant',
        'paper10': 'Animal',
        'paper11': 'Fungi',
        'paper12': 'Plant',
        'paper13': 'Microbe',
        'paper14': 'Animal',
        'paper15': 'Plant',
        'paper16': 'Plant',
        'paper17': 'Fungi',
        'paper18': 'Microbe'
    }


@pytest.fixture
def years_per_class():
    return {
        'Plant': [2007, 1986, 2021, 2019, 2010, 2023, 2017, 2022, 2023],
        'Microbe': [2005, 2017, 2015],
        'Animal': [1997, 2001, 2021],
        'Fungi': [1999, 1978]
    }


def test_get_per_class_years(flattened_papers, paper_classifications,
                             years_per_class):

    result = ds.get_per_class_years(flattened_papers, paper_classifications)

    assert result == years_per_class


######################## get_per_class_cumulative_years ########################


@pytest.fixture
def cumulative_years_per_class():
    return {
        'Plant': {
            1986: 1 / 1000,
            2007: 2 / 1000,
            2010: 3 / 1000,
            2017: 4 / 1000,
            2019: 5 / 1000,
            2021: 6 / 1000,
            2022: 7 / 1000,
            2023: 9 / 1000
        },
        'Microbe': {
            2005: 1 / 1000,
            2015: 2 / 1000,
            2017: 3 / 1000
        },
        'Animal': {
            1997: 1 / 1000,
            2001: 2 / 1000,
            2021: 3 / 1000
        },
        'Fungi': {
            1978: 1 / 1000,
            1999: 2 / 1000
        }
    }


def test_get_per_class_cumulative_years(years_per_class,
                                        cumulative_years_per_class):

    result = ds.get_per_class_cumulative_years(years_per_class)

    assert result == cumulative_years_per_class
