"""
Spot checks for GenericTreeNode.

Author: Serena G. Lotreck
"""
import pytest
import sys
sys.path.append('../desiccation_network/conference_recommendation/')
from generic_tree_node import GenericTreeNode


@pytest.fixture
def sample_tree():
    parts = [[{'D1', 'D2', 'D3'},
            {'D4', 'D5', 'D1'},
            {'D6', 'D7', 'D8'}],
            [{'D9', 'D10', 'D2'},
            {'D9', 'D3'},
            {'D7'}],
            [{'D10', 'D6', 'D4', 'D9'}
            ]]
    tree = GenericTreeNode('root')
    tree.parse_children(parts)
    return tree

################################### get_node_paths ############################

@pytest.fixture
def node_paths():
    return {
        'D1': [['root', 0, 0], ['root', 0, 1]],
        'D2': [['root', 0, 0], ['root', 1, 0]],
        'D3': [['root', 0, 0], ['root', 1, 1]],
        'D4': [['root', 0, 1], ['root', 2, 0]],
        'D5': [['root', 0, 1]],
        'D6': [['root', 0, 2], ['root', 2, 0]],
        'D7': [['root', 0, 2], ['root', 1, 2]],
        'D8': [['root', 0, 2]],
        'D9': [['root', 1, 0], ['root', 1, 1], ['root', 2, 0]],
        'D10': [['root', 1, 0], ['root', 2, 0]]
    }


def test_get_node_paths(sample_tree, node_paths):
    
    result = GenericTreeNode.get_node_paths(sample_tree)
    
    assert result == node_paths


############################# calculate_distance ###############################

@pytest.fixture
def same_paths_paths():
    return [['root', 0, 1], ['root', 0, 1]]

@pytest.fixture
def diff_last_paths():
    return [['root', 0, 1], ['root', 0, 2]]

@pytest.fixture
def diff_all_paths():
    return [['root', 0, 1], ['root', 1, 1]]


def test_calculate_distance_same_paths(same_paths_paths):
    
    result = GenericTreeNode.calculate_distance(same_paths_paths[0], same_paths_paths[1])
    
    assert result == 0
    
def test_calculate_distance_diff_last_paths(diff_last_paths):
    
    result = GenericTreeNode.calculate_distance(diff_last_paths[0], diff_last_paths[1])
    
    assert result == 2
    
def test_calculate_distance_diff_all_paths(diff_all_paths):
    
    result = GenericTreeNode.calculate_distance(diff_all_paths[0], diff_all_paths[1])
    
    assert result == 4


################################## get_distances ###############################

@pytest.fixture
def distance_attr():
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

def test_get_distances(sample_tree, distance_attr):
    
    sample_tree.get_distances()
    
    result = sample_tree.node_distances
    
    assert result == distance_attr