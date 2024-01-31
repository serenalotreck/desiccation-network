"""
Class for building conference intive recommendation system.

Author: Serena G. Lotreck
"""
import utils
import pandas as pd


class RecommendationSystem():
    """
    Class to perform conference recommendations based on a set of information.
    """
    def __init__(self, paper_dataset, classed_citation_net, topic_model, attendees,
                 alt_names, viz_threshold=None, outpath='', outprefix=''):
        """
        parameters:
            paper_dataset, list of dict: WoS papers with author and affiliation
                data
            class_citation_net, networkx Graph: directed citation network, nodes
                are papers and edges are citations, nodes have study_system
                attribute defined
            topic_model, BERTopic instance: topic model to use
            attendees, df: columns are Surname, First_name, Affiliation, Country
            alt_names, df: columns are columns are Registration_surname,
                Registration_first_name, Alternative_name_1..., Maiden_name
            viz_threshold, float: number between 0 and 1, the percent of authors
                to include for graphs saved for visualization
            outpath, str: path to save outputs
            outprefix, str: prefix to prepend to output filenames
        """
        # Initialize attributes passed to init
        self.paper_dataset = paper_dataset
        self.classed_citation_net = classed_citation_net
        self.topic_model = topic_model
        
        # Process attendees to strip trailing whitespace and to lowercase
        for col in attendees.columns:
            attendees[col] = attendees[col].str.strip().str.lower()
        self.attendees = attendees

        self.alt_names = utils.process_alt_names(alt_names)
        self.conference_authors = utils.find_author_papers(attendees, paper_dataset,
                                                        alt_names)
        self.viz_threshold = viz_threshold
        self.outpath = outpath
        self.outprefix = outprefix

        # Initialize attrubtes that are optionally set by methods later on
        self.author_papers = None
        self.paper_authors = None
        self.co_cite_net = None
        self.co_author_net = None


    def set_author_papers(self):
        """
        Set author_papers attribute
        """
        # Index by author
        author_papers = defaultdict(list)
        for paper in self.paper_dataset:
            uid = paper['UID']
            for author in paper['authors']:
                try:
                    author_papers[author['wos_standard']].append(uid)
                except KeyError:
                    continue
        self.author_papers = author_papers

    def set_paper_authors(self):
        """
        Set paper_authors attribute
        """
        # Index by paper
        paper_authors = defaultdict(list)
        for paper in papers:
            uid = paper['UID']
            for author in paper['authors']:
                try:
                    paper_authors[uid].append(author['wos_standard'])
                except KeyError:
                    continue
        self.apper_authors = paper_authors


    def create_co_author_network(self):
        """
        Creates a weighted, undirected co-authorship network, where the nodes
        are individuals, and the edges are how often they appear as co-authors
        in the dataset.

        Saves out a thresholded version of the graph for visualization.
        """
        # Get all co-author pairs
        co_authorship_weights = defaultdict(int)
        for paper in self.paper_dataset:
            authors = []
            for author in paper['authors']:
                try:    
                    authors.append(author['wos_standard'])
                except KeyError:
                    continue
            all_author_pairs = combinations(authors, 2)
            for author_pair in all_author_pairs:
                if author_pair[0] != author_pair[1]:
                    co_authorship_weights[author_pair] += 1

        # Combine reverse-ordered pair counts for edges
        co_author_joined_weights = defaultdict(int)
        for pair, val in co_authorship_weights.items():
            co_author_joined_weights[tuple(set(pair))] += val
        edges = [(c[0], c[1], {'weight': w}) for c, w in co_author_joined_weights.items()]

        # Build full network
        co_author_graph = nx.Graph()
        _ = co_author_graph.add_edges_from(edges)
        self.co_author_net = co_author_graph

        # Threshold for visualization and save out
        if self.viz_threshold is not None:
            if self.author_papers is None:
                self.set_author_papers()
            paper_nums_df = pd.DataFrame.from_dict({k: len(v) for k,v in self.author_papers.items()}, orient='index', 'columns'=['num_papers']).sort_values(by='num_papers', axis='columns')
            rows_to_remove = paper_nums_df.iloc[:paper_nums_df.shape[0]*(1 - self.viz_threshold), :]
            nodes_to_remove = rows_to_remove.index.tolist()
            _ = co_author_graph.remove_nodes_from(nodes_to_remove)
        co_author_graph.write_graphml(f'{self.outpath}/{self.outprefix}_co_author_network.graphml')


    def create_co_citation_network(self):
        """
        Creates a weighted, undirected co-citation network, where the nodes
        are individuals, and the edges are how often they cite one another.

        Saves out a thresholded version of the graph for visualization.
        """
        self.set_paper_authors()
        
        co_citation_weights = defaultdict(int)
        for edge in graph.edges:
            for author1 in paper_authors[edge[0]]:
                for author2 in paper_authors[edge[1]]:
                    if author1 != author2:
                        author_pair = tuple(set([author1, author2]))
                        co_citation_weights[author_pair] += 1

        # Combine reverse-ordered pair counts for edges
        co_cite_joined_weights = defaultdict(int)
        for pair, val in co_citation_weights.items():
            co_cite_joined_weights[tuple(set(pair))] += val
        edges = [(e[0], e[1], {'weight': w}) for e, w in co_cite_joined_weights.items()]

        # Build full network
        co_citation_graph = nx.Graph()
        _ = co_citation_graph.add_edges_from(edges)
        self.co_cite_net = co_citation_graph

        # Threshold for visualization and save out
        if self.viz_threshold is not None:
            if self.author_papers is None:
                self.set_author_papers()
            paper_nums_df = pd.DataFrame.from_dict({k: len(v) for k,v in self.author_papers.items()}, orient='index', 'columns'=['num_papers']).sort_values(by='num_papers', axis='columns')
            rows_to_remove = paper_nums_df.iloc[:paper_nums_df.shape[0]*(1 - self.viz_threshold), :]
            nodes_to_remove = rows_to_remove.index.tolist()
            _ = co_citation_graph.remove_nodes_from(nodes_to_remove)
        co_citation_graph.write_graphml(f'{self.outpath}/{self.outprefix}_co_citation_network.graphml')