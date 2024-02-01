"""
Class for building conference intive recommendation system.

Author: Serena G. Lotreck
"""
import utils
import pandas as pd
import networkx as nx
from infomap import Infomap


class RecommendationSystem():
    """
    Class to perform conference recommendations based on a set of information.
    """
    def __init__(self, paper_dataset, classed_citation_net, topic_model, attendees,
                 alt_names, outlier_reduction_params=None, enrich_threshold=None,
                 viz_threshold=None, save_clusters=True, outpath='', outprefix=''):
        """
        parameters:
            paper_dataset, list of dict: WoS papers with author and affiliation
                data
            class_citation_net, networkx Graph: directed citation network, nodes
                are papers and edges are citations, nodes have study_system
                attribute defined
            topic_model, BERTopic instance: topic model to use
            vec_model, CountVectorizer: vectorizer model for topic_model
            rep_model, one of several types: representation model for topic_model
            attendees, df: columns are Surname, First_name, Affiliation, Country
            alt_names, df: columns are columns are Registration_surname,
                Registration_first_name, Alternative_name_1..., Maiden_name
            enrich_threshold, float: proportion of authors in a cluster that
                should be conference attendees to consider a cluster "enriched"
                in conference attendees. For smaller conferences, this should be
                left as None, as few clusters will contain authors and they will
                only be present in smaller numbers
            viz_threshold, float: number between 0 and 1, the percent of authors
                to include for graphs saved for visualization
            outpath, str: path to save outputs
            outprefix, str: prefix to prepend to output filenames
        """
        # Initialize attributes passed to init
        self.paper_dataset = paper_dataset
        self.classed_citation_net = classed_citation_net
        self.topic_model = topic_model
        self.vec_model = vec_model
        self.rep_model = rep_model
        
        # Process attendees to strip trailing whitespace and to lowercase
        for col in attendees.columns:
            attendees[col] = attendees[col].str.strip().str.lower()
        self.attendees = attendees

        self.alt_names = utils.process_alt_names(alt_names)
        self.conference_authors = utils.find_author_papers(attendees, paper_dataset,
                                                        alt_names)
        self.outlier_reduction_params = outlier_reduction_params
        self.enrich_threshold = enrich_threshold
        self.viz_threshold = viz_threshold
        self.save_clusters = save_clusters
        self.outpath = outpath
        self.outprefix = outprefix

        # Initialize attrubtes that are optionally set by methods later on
        self.author_papers = None
        self.paper_authors = None
        self.tm_doc_df = None
        self.id_to_topic = None
        self.paper_to_topic = None
        self.topics_to_authors = None
        self.co_cite_net = None
        self.co_cite_ids_to_authors = None
        self.co_author_net = None
        self.co_author_ids_to_authors = None
        self.cite_ids_to_authors = None
        self.enriched_clusters = None


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

    def set_tm_doc_df(self):
        """
        Preprocess documents for topic modeling and set as attribute
        """
        data_with_class = utils.map_classes_to_jsonl(self.classed_cite_net, self.paper_data, False, 'UID')
        abstracts_and_classes = {'UID': [], 'abstract': [], 'study_system': [], 'year': []}
        for paper in data_with_class:
            abstracts_and_classes['UID'].append(paper['UID'])
            abstracts_and_classes['abstract'].append(paper['abstract'])
            abstracts_and_classes['study_system'].append(paper['study_system'])
            abstracts_and_classes['year'].append(int(paper['year']))
        abstracts = pd.DataFrame.from_dict(abstracts_and_classes, orient='columns').set_index('UID')
        print(f'There are {len(abstracts)} abstracts in the dataset.')
        self.tm_doc_df = abstracts

    def set_topics_to_authors(self):
        """
        Set topics_to_authors attribute
        """
        topics_to_authors = defaultdict(list)
        for paper, topic in self.paper_to_topic.items():
            for author in paper_authors[paper]:
                topics_to_authors[topic].append(author)
        self.topics_to_authors = topics_to_authors

    def create_co_author_network(self):
        """
        Creates a weighted, undirected co-authorship network, where the nodes
        are individuals, and the edges are how often they appear as co-authors
        in the dataset.

        Saves out a thresholded version of the graph for visualization.
        """
        print('\nBuilding co-author network...')
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
        print(f'Saved co-author network as {self.outpath}/{self.outprefix}_co_author_network.graphml')

    def create_co_citation_network(self):
        """
        Creates a weighted, undirected co-citation network, where the nodes
        are individuals, and the edges are how often they cite one another.

        Saves out a thresholded version of the graph for visualization.
        """
        print('\nBuilding co-citation network...')
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
        print(f'Saved co-citation network as {self.outpath}/{self.outprefix}_co_citation_network.graphml')

    def cluster_citation_network(self):
        """
        Perform InfoMap clustering on directed citation network.
        """
        print('\nPerfomring Infomap clustering on citation network...')
        im = Infomap(seed=1234)
        mapping = im.add_networkx_graph(self.classed_citation_net)
        _ = im.run()
        cluster_output = im.get_dataframe(["module_id", "name"])
        self.cite_ids_to_authors = defaultdict(list)
        for uid, cluster_id in cluster_output.set_index("name").to_dict().items():
            for author in self.paper_authors[uid]:
                self.cite_uids_to_authors[cluster_id].append(author)

    def cluster_co_author_network(self):
        """
        Clusters co-author network with Louvain clustering.
        """
        print('\nPerforming Louvain clustering on co-author network...')
        communities = nx.louvain_communities(self.co_author_net, seed=1234)
        self.co_author_ids_to_authors = {i: comm for i, comm in enumerate(communities)}

    def cluster_co_citation_network(self):
        """
        Clusters co-citation network with Louvain clustering
        """
        print('\nPerforming Louvain clustering on co-citation network...')
        communities = nx.louvain_communities(self.co_cite_net, seed=1234)
        self.co_cite_ids_to_authors = {i: comm for i, comm in enumerate(communities)}

    def fit_topic_model(self):
        """
        Fit topic model and set topic cluster IDs, save plot with topic rep
        study system distributions.
        """
        print('\nFitting topic model...')
        self.set_tm_doc_df()
        docs = self.tm_doc_df.abstract.values.tolist()
        topics, probs = self.topic_model.fit_transform(docs)
        if outlier_reduction_params is not None:
            new_topics = self.topic_model.reduce_outliers(docs, topics, **self.outlier_reduction_params)
            self.topic_model.update(docs, topics=new_topics, vectorizer_model=self.vec_model, representation_model=self.rep_model)
        self.id_to_topic = {int(itop[0]): itop[1] for itop in self.topic_model.get_topic_info()['Name'].str.split('_')}
        doc_tops = self.topic_model.get_document_info(docs)
        doc_tops['UID'] = self.tm_doc_df.index
        self.paper_to_topic = doc_tops[['UID', 'Topic']].to_dict()
        self.set_topics_to_authors()
    
    def calculate_community_enrichment(self):
        """
        Calculate conference author enrichment in all types of clusters.
        """
        print('\nCalculating community enrichments for all cluster types...')
        enrichments = {}
        for clust_type, ids_to_authors in {
            'directed_citation': self.cite_ids_to_authors,
            'co_citation': self.co_cite_ids_to_authors,
            'co_author': self.co_author_ids_to_authors,
            'topic': self.topics_to_authors
        }.items():
            if self.save_clusters:
                savename = f'{self.outpath}/{self.outprefix}_{clust_type}_ids_to_authors.json'
                with open(savename, 'w') as myf:
                    json.dump(ids_to_authors, savename)
                print(f'Saved {clust_type} id to authors dict as {savename}')
            clust_enrich = {}
            for clust, authors in ids_to_authors.items():
                num_conf = [auth for auth in authors if auth in self.conference_authors.keys()]
                total_num = len(authors)
                enrich_prop = num_conf/total_num
                clust_enrich[clust] = enrich_prop
            enrichments[clust_type] = clust_enrich
        self.enriched_clusters = enrichments
    
    def calulate_conference_candidates(self):
        """
        Get candidates for conference invitation.
        """
        print('\nBeginning calculations for conference candidates')
        print('---------------------------------------------------------------')
        
        # Get extra networks
        self.create_co_citation_network()
        self.create_co_author_network()
        
        # Perform topic modeling
        self.fit_topic_model()
        
        # Perform other clustering
        self.cluster_citation_network()
        self.cluster_co_citation_network()
        self.cluster_co_author_network()
        
        # Get enrichments
        self.calculate_community_enrichments()
        
        # Apply heuristic calculation
        ## TODO