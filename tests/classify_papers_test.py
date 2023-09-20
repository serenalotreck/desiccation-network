"""
Spot checks for  classify_papers.py

Author: Serena G. Lotreck
"""
import pytest
import sys

sys.path.append('../citation_network/')
import classify_papers as cp
import spacy
import string
import random


################################# get_unique_papers ###########################


@pytest.fixture
def search_results():
    return [{
        'paperId':
        'paper1',
        'title':
        'this is paper1',
        'abstract':
        'this is paper1s abstract',
        'references': [{
            'paperId': 'paper2',
            'title': 'this is paper 2s title',
            'abstract': 'this is apper2s abstract'
        }, {
            'paperId': 'paper3',
            'title': 'this is paper 3s title',
            'abstract': 'this is paper3s abstract'
        }, {
            'paperId': 'paper4',
            'title': 'this is paper 4s title',
            'abstract': 'this is paper4s abstract'
        }]
    }, {
        'paperId':
        'paper5',
        'title':
        'this ispaper5',
        'abstract':
        'this ispaper5s abstract',
        'references': [{
            'paperId': 'paper6',
            'title': 'this is paper 6s title',
            'abstract': 'this is paper6s abstract'
        }, {
            'paperId': 'paper7',
            'title': 'this is paper 7s title',
            'abstract': 'this is paper7s abstract'
        }]
    }, {
        'paperId':
        'paper8',
        'title':
        'this is paper8',
        'abstract':
        'this is paper 8s abstract',
        'references': [{
            'paperId': 'paper2',
            'title': 'this is paper 2s title',
            'abstract': 'this is apper2s abstract'
        }, {
            'paperId': 'paper7',
            'title': 'this is paper 7s title',
            'abstract': 'this is paper7s abstract'
        }]
    }]


@pytest.fixture
def to_classify():
    return {
        'paper1': {
            'title': 'this is paper1',
            'abstract': 'this is paper1s abstract'
        },
        'paper2': {
            'title': 'this is paper 2s title',
            'abstract': 'this is apper2s abstract'
        },
        'paper3': {
            'title': 'this is paper 3s title',
            'abstract': 'this is paper3s abstract'
        },
        'paper4': {
            'title': 'this is paper 4s title',
            'abstract': 'this is paper4s abstract'
        },
        'paper5': {
            'title': 'this ispaper5',
            'abstract': 'this ispaper5s abstract'
        },
        'paper6': {
            'title': 'this is paper 6s title',
            'abstract': 'this is paper6s abstract'
        },
        'paper7': {
            'title': 'this is paper 7s title',
            'abstract': 'this is paper7s abstract'
        },
        'paper8': {
            'title': 'this is paper8',
            'abstract': 'this is paper 8s abstract'
        }
    }


def test_get_unique_papers(search_results, to_classify):

    result = cp.get_unique_papers(search_results)

    assert result == to_classify


################################## make_ent_doc ###############################


@pytest.fixture
def nlp():
    return spacy.load("en_core_eco_biobert")


@pytest.fixture
def uniq_names_one_doc():
    return [
        'horses', 'cows', 'big cows', 'special cows', 'flowers',
        'multi word entities'
    ]

@pytest.fixture
def uniq_names_multi_doc():
    return [''.join(random.choices(string.ascii_uppercase + string.digits,
        k=9)) for i in range(25)]

def test_make_ent_docs_one_doc(nlp, uniq_names_one_doc):

    result = cp.make_ent_docs(uniq_names_one_doc, nlp)

    # Since making the doc to check it would use the same code as the actual
    # code, we'll just check to make sure the number and identity of the
    # entities is the same

    result_ent_list = [e.text for res in result for e in res.ents]
    result_num_ents = len(result[0].ents)

    assert len(result) == 1
    assert result_ent_list == uniq_names_one_doc
    assert result_num_ents == len(uniq_names_one_doc)

def test_make_ent_docs_multi_doc(nlp, uniq_names_multi_doc):

    # NOTE: This test is very memory intensive, takes about an hour in this
    # form. Another option is to go into classify_papers.py and change all
    # instances of 1000000 to 100; then change the above 250000 to just 25
    result = cp.make_ent_docs(uniq_names_multi_doc, nlp)

    result_ent_list = [e.text for res in result for e in res.ents]
    result_num_ents = sum([len(res.ents) for res in result])

    print(result)
    assert len(result) == 3
    assert result_ent_list == uniq_names_multi_doc
    assert result_num_ents == len(uniq_names_multi_doc)


################################ map_specs_to_kings ###########################


@pytest.fixture
def species_ids():
    return {
        'A. thaliana': 3702,
        'Saccharomyces cerevisiae': 4932,
        'Amphiheterocytum lacustre': 2588929,
    }


@pytest.fixture
def species_dict():
    return {
        'A. thaliana': 'Plant',
        'Saccharomyces cerevisiae': 'Fungi',
        'Amphiheterocytum lacustre': 'Microbe'
    }


def test_map_specs_to_kings(species_ids, species_dict):

    result = cp.map_specs_to_kings(species_ids)

    assert result == species_dict


############################ map_paper_species ##############################


@pytest.fixture
def paper_spec_names():
    return {
        'paper1': ['A. thaliana'],
        'paper2': [
            'Saccharomyces cerevisiae', 'Amphiheterocytum lacustre',
            'Amphiheterocytum lacustre'
        ],
        'paper3': []
    }


@pytest.fixture
def to_classify_with_names():
    return {
        'paper1': {
            'title': 'Drought response in A. thaliana',
            'abstract': 'Arabidopsis thaliana is a cool plant'
        },
        'paper2': {
            'title':
            'Theres no names in this title',
            'abstract':
            'But there are lots of names here! We have '
            'Saccharomyces cerevisiae, Amphiheterocytum lacustre, and '
            'another Amphiheterocytum lacustre.'
        },
        'paper3': {
            'title': 'Definitely no names here.',
            'abstract': 'We study vegetative desiccation tolerance.'
        }
    }


@pytest.fixture
def generic_dict():
    return {'vegetation': 'Plant'}


@pytest.fixture
def classified_with_generic():
    return {'paper1': 'Plant', 'paper2': 'Microbe', 'paper3': 'Plant'}


@pytest.fixture
def classified_without_generic():
    return {'paper1': 'Plant', 'paper2': 'Microbe', 'paper3': 'NOCLASS'}


def test_map_paper_species_with_generic(paper_spec_names, species_dict,
                                        generic_dict, to_classify_with_names,
                                        classified_with_generic):

    result = cp.map_paper_species(paper_spec_names, species_dict, generic_dict,
                                  to_classify_with_names)

    assert result == classified_with_generic


def test_map_paper_species_without_generic(paper_spec_names, species_dict,
                                           to_classify_with_names,
                                           classified_without_generic):

    result = cp.map_paper_species(paper_spec_names, species_dict, '',
                                  to_classify_with_names)

    assert result == classified_without_generic


############################fuzzy_match_kingdoms ############################
@pytest.fixture
def generic_dict():
    return {"vegetative": "Plant", "seeds": "Plant", "plants": "Plant"}


@pytest.fixture
def fuzzy_imperfect_single_doc():
    return {
        'title': 'Leaves of organisms',
        'abstract': 'vegetation is very important'
    }


@pytest.fixture
def fuzzy_imperfect_single_answer():
    return ['Plant']


@pytest.fixture
def fuzzy_perfect_and_imperfect_doc():
    return {
        'title': 'vegetative desiccation tolerance in Arabidopsis seed',
        'abstract': None
    }


@pytest.fixture
def fuzzy_perfect_and_imperfect_answer():
    return ['Plant', 'Plant']


@pytest.fixture
def fuzzy_too_far_doc():
    return {'title': 'Vegetables are tasty', 'abstract': None}


@pytest.fixture
def fuzzy_too_far_answer():
    return []


def test_fuzzy_imperfect_single(fuzzy_imperfect_single_doc,
                                fuzzy_imperfect_single_answer, generic_dict):

    result = cp.fuzzy_match_kingdoms(fuzzy_imperfect_single_doc, generic_dict)

    assert result == fuzzy_imperfect_single_answer


def test_fuzzy_perfect_and_imperfect(fuzzy_perfect_and_imperfect_doc,
                                     fuzzy_perfect_and_imperfect_answer,
                                     generic_dict):

    result = cp.fuzzy_match_kingdoms(fuzzy_perfect_and_imperfect_doc,
                                     generic_dict)

    assert result == fuzzy_perfect_and_imperfect_answer


def test_fuzzy_too_far(fuzzy_too_far_doc, fuzzy_too_far_answer, generic_dict):

    result = cp.fuzzy_match_kingdoms(fuzzy_too_far_doc, generic_dict)

    assert result == fuzzy_too_far_answer
