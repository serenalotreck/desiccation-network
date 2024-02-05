"""
Class to process tree-structured hierarchical clustering data.

Author: Serena G. Lotreck
"""
from uuid import uuid4
from collections import defaultdict
from statistics import mean


class GenericTreeNode():
    """
    Class to store node of a generic tree.
    """
    def __init__(self, ident):
        """
        Initialize GenericTreeNode instance.
        """
        self.ident = ident
        self.children = None
        self.node_paths = None
        self.node_distances = None

    def parse_children(self, parts, start_int=None):
        """
        Parse a tree formatted as nested lists with leaf node ID's contained in sets

        parameters:
            parts, list of list of set: innermost structure is a set with the
                node IDs for nodes belonging to one leaf cluster. Same as output
                of louvain_partitions
            start_int, int: integer at which to start numbering the nodes at each
                layer of the tree
        """
        # Initial setup
        if start_int is None:
            start_int = 0
        # Base case
        if isinstance(parts, set):
            self.children = [GenericTreeNode(c) for c in parts]
        # Recursive case
        else:
            self.children = []
            for part in parts:
                c_node = GenericTreeNode(start_int)
                start_int += 1
                c_node.parse_children(part)
                self.children.append(c_node)

    @staticmethod
    def get_node_paths(root, current_path=None, paths=None):
        """
        Get paths from root for all nodes.

        parameters:
            root, GenericTreeNode instance: node from which to search
            current_path, list of str: list of node IDs
            paths, dict: keys are author names and values are path lists

        returns:
            paths, dict: keys are author names, values are lists of list, where
                each internal list is a path
        """
        # Setup
        if paths is None:
            paths = defaultdict(list)
        if current_path is None:
            current_path = []
        # Base case
        if root.children is None:
            paths[root.ident].append(current_path)
        # Recursive case
        else:
            current_path.append(root.ident)
            for child in root.children:
                GenericTreeNode.get_node_paths(child, list(current_path),
                                               paths)
        return paths

    @staticmethod
    def calculate_distance(path1, path2):
        """
        Calculate the traversal distance between two nodes, given their paths.

        parameters:
            path1, path2, lists of str and int: names of nodes on each path

        returns:
            dist, int: traversal distance
        """
        # Simple check to see if they're the same
        if path1 == path2:
            common_path_length = len(path1)
        # Go through each path from the root, get index where they differ
        else:
            for i in range(min(len(path1), len(path2))):
                if path1[i] != path2[i]:
                    break
            # That difference is the length of the common path
            common_path_length = i
        # Use it to compute the total difference
        dist = (len(path1) + len(path2) - 2 * (common_path_length))

        return dist

    def get_cluster_membership(self):
        """
        Returns the names in each cluster, using the same IDs that are used by
        get_distances.
        """
        clusters = defaultdict(list)
        for author, paths in self.node_paths.items():
            for path in paths:
                cluster_name = '-'.join([str(i) for i in path[1:]])
                clusters[cluster_name].append(author)
        return clusters

    def get_distances(self):
        """
        Get the traversal distance between each node and all other clusters.
        Assumes the self node is the tree root. Sets the node_distances attribute.
        """
        # Get the node paths
        node_paths = GenericTreeNode.get_node_paths(self)
        self.node_paths = node_paths

        # Get the paths for each unique cluster
        cluster_paths = {}
        for paths in node_paths.values():
            for path in paths:
                clust_id = '-'.join([str(i) for i in path[1:]])
                cluster_paths[clust_id] = path

        # Get the average distances between each node and each cluster
        author_cluster_distances = {}
        for author, author_paths in node_paths.items():
            author_dists = {}
            for cluster, cluster_path in cluster_paths.items():
                all_pair_dists = []
                for path1 in author_paths:
                    pair_dist = GenericTreeNode.calculate_distance(
                        path1, cluster_path)
                    all_pair_dists.append(pair_dist)
                mean_dists = mean(all_pair_dists)
                author_dists[cluster] = mean_dists
            author_cluster_distances[author] = author_dists

        self.node_distances = author_cluster_distances
