"""
Class for building conference intive recommendation system.

Author: Serena G. Lotreck
"""
import utils
import pandas as pd
import networkx as nx
from infomap import Infomap
from collections import defaultdict, Counter
from itertools import combinations
import numpy as np
from networkx.algorithms.community.louvain import louvain_communities, louvain_partitions
from statistics import mean
from generic_tree_node import GenericTreeNode
import jsonlines
import pycountry
import json


class RecommendationSystem():
    """
    Class to perform conference recommendations based on a set of information.
    """
    def __init__(self,
                 paper_dataset,
                 classed_citation_net,
                 topic_model,
                 vec_model,
                 rep_model,
                 attendees,
                 alt_names,
                 outlier_reduction_params=None,
                 enrich_threshold=None,
                 prod_threshold=None,
                 save_clusters=True,
                 outpath='',
                 outprefix=''):
        """
        parameters:
            paper_dataset, list of dict: WoS papers with author and affiliation
                data
            class_citation_net, networkx Graph: directed citation network, nodes
                are papers and edges are citations, nodes have study_system
                attribute defined
            topic_model, BERTopic instance: topic model to use
            vec_model, CountVectorizer: vectorizer model for topic_model
            rep_model, one of the representation model options in BERTopic:
                representation model for topic_model
            attendees, df: columns are Surname, First_name, Affiliation, Country
            alt_names, df: columns are columns are Registration_surname,
                Registration_first_name, Alternative_name_1..., Maiden_name
            enrich_threshold, int: Percentile cutoff between 0 and 100. Uses the
                distribution of enrichment values to edtermine a threshold for
                the proportion of authors in a cluster that should be conference
                attendees to consider a cluster "enriched" in conference attendees.
            prod_threshold, float: number between 0 and 1, the percent of authors
                to consider as candidates based on number of publications
            outpath, str: path to save outputs
            outprefix, str: prefix to prepend to output filenames
        """
        # Initialize attributes passed to init
        self.paper_dataset = paper_dataset
        self.set_author_country_affils_dict()
        self.classed_citation_net = classed_citation_net
        self.topic_model = topic_model
        self.vec_model = vec_model
        self.rep_model = rep_model

        # Process attendees to strip trailing whitespace and to lowercase
        alt_names = utils.process_alt_names(alt_names)
        self.conference_authors, alt_names = utils.find_author_papers(
            attendees, paper_dataset, alt_names)
        self.set_attendee_country_affils_list(attendees)
        self.all_possible_conf_names = list(alt_names.keys())
        self.all_possible_conf_names.extend([
            name for name in self.conference_authors.keys()
            if name not in self.all_possible_conf_names
        ])
        self.outlier_reduction_params = outlier_reduction_params
        self.enrich_threshold = enrich_threshold
        self.prod_threshold = prod_threshold
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
        self.co_cite_clusters_to_authors = None
        self.co_cite_cluster_distances = None
        self.co_cite_partitions = None
        self.co_author_net = None
        self.co_author_cluster_distances = None
        self.co_author_clusters_to_authors = None
        self.co_author_partitions = None
        self.cite_ids_to_authors = None
        self.cite_partitions = None
        self.enriched_clusters = None

    def set_author_country_affils_dict(self):
        """
        Set countries for all authors.
        """
        self.author_affils_dict = utils.get_geographic_locations(
            self.paper_dataset)

    def set_attendee_country_affils_list(self, attendees):
        """
        Set countries reported in registration by past attendees.
        """
        country_conversions = {
            country.name: country.alpha_3
            for country in pycountry.countries
        }
        attendee_countries = attendees['Country']
        attendee_countries = attendee_countries.replace({
            'The Netherlands': 'Netherlands',
            'USA': 'United States'
        })  # Assumes these are the only problem children
        self.attendee_affils_list = [
            country_conversions[count] for count in attendee_countries
        ]

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
                    author_papers[author['wos_standard'].lower()].append(uid)
                except KeyError:
                    continue
        author_papers = {k: list(set(v)) for k, v in author_papers.items()}
        self.author_papers = author_papers

    def set_paper_authors(self):
        """
        Set paper_authors attribute
        """
        # Index by paper
        paper_authors = defaultdict(list)
        for paper in self.paper_dataset:
            uid = paper['UID']
            for author in paper['authors']:
                try:
                    paper_authors[uid].append(author['wos_standard'].lower())
                except KeyError:
                    continue
        paper_authors = {k: list(set(v)) for k, v in paper_authors.items()}
        self.paper_authors = paper_authors

    def set_tm_doc_df(self):
        """
        Preprocess documents for topic modeling and set as attribute
        """
        data_with_class = utils.map_classes_to_jsonl(self.classed_citation_net,
                                                     self.paper_dataset, False,
                                                     'UID')
        abstracts_and_classes = {
            'UID': [],
            'abstract': [],
            'study_system': [],
            'year': []
        }
        for paper in data_with_class:
            abstracts_and_classes['UID'].append(paper['UID'])
            abstracts_and_classes['abstract'].append(paper['abstract'])
            abstracts_and_classes['study_system'].append(paper['study_system'])
            abstracts_and_classes['year'].append(int(paper['year']))
        abstracts = pd.DataFrame.from_dict(abstracts_and_classes,
                                           orient='columns').set_index('UID')
        print(f'There are {len(abstracts)} abstracts in the dataset.')
        self.tm_doc_df = abstracts

    def set_topics_to_authors(self):
        """
        Set topics_to_authors attribute
        """
        topics_to_authors = defaultdict(list)
        for paper, topic in self.paper_to_topic.items():
            for author in self.paper_authors[paper]:
                topics_to_authors[topic].append(author)
        topics_to_authors = {
            k: list(set(v))
            for k, v in topics_to_authors.items()
        }
        self.topics_to_authors = topics_to_authors

    def set_geographic_locations(self):
        """
        Set author_locations attribute with most recent affiliation location.
        """
        self.author_locations = utils.get_geographic_locations(
            self.paper_dataset)

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
                    authors.append(author['wos_standard'].lower())
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
        edges = [(c[0], c[1], {
            'weight': w
        }) for c, w in co_author_joined_weights.items()]
        nodes = [(ep, {
            'is_conference_attendee': 'yes'
        }) if ep in self.all_possible_conf_names else
                 (ep, {
                     'is_conference_attendee': 'no'
                 }) for edge in edges for ep in edge[:2]]

        # Build full network
        co_author_graph = nx.Graph()
        _ = co_author_graph.add_nodes_from(nodes)
        _ = co_author_graph.add_edges_from(edges)

        # Threshold for visualization and save out
        if self.prod_threshold is not None:
            if self.author_papers is None:
                self.set_author_papers()
            paper_nums_df = pd.DataFrame.from_dict(
                {k: len(v)
                 for k, v in self.author_papers.items()},
                orient='index',
                columns=['num_papers']).sort_values(by='num_papers',
                                                    axis='index')
            idx_to_remove = round(paper_nums_df.shape[0] *
                                  (1 - self.prod_threshold))
            rows_to_remove = paper_nums_df.iloc[:idx_to_remove, :]
            nodes_to_remove = rows_to_remove.index.tolist()
            _ = co_author_graph.remove_nodes_from(nodes_to_remove)
        self.co_author_net = co_author_graph

    def create_co_citation_network(self):
        """
        Creates a weighted, undirected co-citation network, where the nodes
        are individuals, and the edges are how often they cite one another.

        Saves out a thresholded version of the graph for visualization.
        """
        print('\nBuilding co-citation network...')
        self.set_paper_authors()

        co_citation_weights = defaultdict(int)
        for edge in self.classed_citation_net.edges:
            for author1 in self.paper_authors[edge[0]]:
                for author2 in self.paper_authors[edge[1]]:
                    if author1 != author2:
                        author_pair = tuple(set([author1, author2]))
                        co_citation_weights[author_pair] += 1

        # Combine reverse-ordered pair counts for edges
        co_cite_joined_weights = defaultdict(int)
        for pair, val in co_citation_weights.items():
            co_cite_joined_weights[tuple(set(pair))] += val
        edges = [(e[0], e[1], {
            'weight': w
        }) for e, w in co_cite_joined_weights.items()]
        nodes = [(ep, {
            'is_conference_attendee': 'yes'
        }) if ep in self.all_possible_conf_names else
                 (ep, {
                     'is_conference_attendee': 'no'
                 }) for edge in edges for ep in edge[:2]]

        # Build full network
        co_citation_graph = nx.Graph()
        _ = co_citation_graph.add_nodes_from(nodes)
        _ = co_citation_graph.add_edges_from(edges)

        # Threshold for visualization and save out
        if self.prod_threshold is not None:
            if self.author_papers is None:
                self.set_author_papers()
            paper_nums_df = pd.DataFrame.from_dict(
                {k: len(v)
                 for k, v in self.author_papers.items()},
                orient='index',
                columns=['num_papers']).sort_values(by='num_papers',
                                                    axis='index')
            idx_to_remove = round(paper_nums_df.shape[0] *
                                  (1 - self.prod_threshold))
            rows_to_remove = paper_nums_df.iloc[:idx_to_remove, :]
            nodes_to_remove = rows_to_remove.index.tolist()
            _ = co_citation_graph.remove_nodes_from(nodes_to_remove)
        self.co_cite_net = co_citation_graph

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
        for uid, cluster_id in cluster_output.set_index(
                "name").to_dict().items():
            for author in self.paper_authors[uid]:
                self.cite_uids_to_authors[cluster_id].append(author)

    def cluster_co_author_network(self):
        """
        Clusters co-author network with Louvain clustering and calculates the
        distances between each author and all clusters.
        """
        print('\nPerforming Louvain clustering on co-author network...')
        self.co_author_partitions = list(
            louvain_partitions(self.co_author_net, seed=1234))
        co_author_tree = GenericTreeNode('co-author')
        co_author_tree.parse_children(self.co_author_partitions)
        co_author_tree.get_distances()
        self.co_author_clusters_to_authors = co_author_tree.get_cluster_membership(
        )
        self.co_author_cluster_distances = co_author_tree.node_distances

    def cluster_co_citation_network(self):
        """
        Clusters co-citation network with Louvain clustering and calculates the
        distances between each author and all clusters.
        """
        print('\nPerforming Louvain clustering on co-citation network...')
        self.co_cite_partitions = list(
            louvain_partitions(self.co_cite_net, seed=1234))
        co_cite_tree = GenericTreeNode('co-author')
        co_cite_tree.parse_children(self.co_cite_partitions)
        co_cite_tree.get_distances()
        self.co_cite_clusters_to_authors = co_cite_tree.get_cluster_membership(
        )
        self.co_cite_cluster_distances = co_cite_tree.node_distances

    def fit_topic_model(self):
        """
        Fit topic model and set topic cluster IDs, save plot with topic rep
        study system distributions.
        """
        self.set_tm_doc_df()
        docs = self.tm_doc_df.abstract.values.tolist()
        print('\nFitting topic model...')
        topics, probs = self.topic_model.fit_transform(docs)
        if self.outlier_reduction_params is not None:
            print('\nReducing outliers...')
            new_topics = self.topic_model.reduce_outliers(
                docs, topics, **self.outlier_reduction_params)
            self.topic_model.update_topics(docs,
                                           topics=new_topics,
                                           vectorizer_model=self.vec_model,
                                           representation_model=self.rep_model)
        self.id_to_topic = {
            int(itop[0]): itop[1]
            for itop in self.topic_model.get_topic_info()['Name'].str.split(
                '_')
        }
        doc_tops = self.topic_model.get_document_info(docs)
        doc_tops['UID'] = self.tm_doc_df.index
        paper_to_topic_df = doc_tops[['UID', 'Topic']]
        self.paper_to_topic = {
            row.UID: row.Topic
            for idx, row in paper_to_topic_df.iterrows()
        }
        self.set_topics_to_authors()

    def calculate_community_enrichment(self):
        """
        Calculate conference author enrichment in all types of clusters.
        """
        print('\nCalculating community enrichments for all cluster types...')
        enrichments = {}
        for clust_type, clusters_to_authors in {
                'co_citation': self.co_cite_clusters_to_authors,
                'co_author': self.co_author_clusters_to_authors,
                'topic': self.topics_to_authors
        }.items():
            if self.save_clusters:
                savename = f'{self.outpath}/{self.outprefix}_{clust_type}_clusters_to_authors.json'
                with open(savename, 'w') as myf:
                    json.dump(clusters_to_authors, myf)
                print(
                    f'Saved {clust_type} clusters to authors dict as {savename}'
                )
            clust_enrich = {}
            for clust, authors in clusters_to_authors.items():
                num_conf = [
                    auth for auth in authors if auth in self.
                    all_possible_conf_names  ## This double counts authors with two alternative names in one cluster
                ]
                total_num = len(authors)
                enrich_prop = len(num_conf) / total_num
                clust_enrich[clust] = enrich_prop
            # Use threshold if requested
            if self.enrich_threshold is not None:
                cutoff = np.percentile(list(clust_enrich.values()),
                                       self.enrich_threshold)
                clust_enrich = {
                    clust: (0.0 if enrich < cutoff else enrich)
                    for clust, enrich in clust_enrich.items()
                }

            enrichments[clust_type] = clust_enrich

        self.enriched_clusters = enrichments

    @staticmethod
    def calculate_topic_pa_score(author, topics_to_authors, enriched_clusters):
        """
        Calculates presence/absence score for a given author.

        parameters:
            author, str: author
            topics_to_authors, dict: keys are topics, values are lists of authors
            enriched_clusters: list, enriched clusters

        returns:
            mean_topic_score
        """
        # Scoring: 1 if the cluster is not enriched, 0 if it is, average for all
        # clusters containing the author
        author_topics = []
        for topic, authors in topics_to_authors.items():
            if author in authors:
                author_topics.append(topic)
        topic_scores = [
            1 if top not in enriched_clusters else 0 for top in author_topics
        ]
        # Some docs are dropped for being truly interdisciplinary and not having
        # a class, have to account for that here
        if len(topic_scores) == 0:
            return 0
        else:
            mean_topic_score = mean(topic_scores)
            return mean_topic_score

    @staticmethod
    def calculate_mean_hier_score(author, cluster_distances,
                                  enriched_clusters):
        """
        Calculate mean distance score for a given author for a
        hierarcically-clustered network.

        parameters:
            author, str: author
            cluster_distances, dict of dict: cluster distances
            enriched_clusters: list, enriched clusters

        returns:
            mean_cluster_score, float: score
        """
        # Get absolute scores
        try:
            cluster_type_scores = [
                cluster_distances[author][clust_id]
                for clust_id in enriched_clusters
            ]
            # Currently, the closer you are, the lower your score.
            # We want to privilege being some optimal distance from the enriched
            # clusters, because too close and they'll likely already be in the
            # interpersonal network we're trying to expand, but too far and they may
            # be irrelevant. As a first attempt, we'll use distance from the 25th
            # percentile as the score, and normalize on either side; so that being
            # in the same cluster as conference authors is the same penalty as being
            # maximally far away.
            penalty_threshold = np.percentile(cluster_type_scores, 25)
            close_side_distance = penalty_threshold - 0
            far_side_distance = max(
                cluster_type_scores
            ) - penalty_threshold  ## May want to change this to the max possible rather than the max observed
            cluster_scores = []
            for sc in cluster_type_scores:
                dist = penalty_threshold - sc
                if dist < 0:
                    normed = 1 - (abs(dist) / far_side_distance)
                else:
                    normed = 1 - (dist / close_side_distance)
                cluster_scores.append(normed)
            mean_cluster_score = mean(cluster_scores)
            return mean_cluster_score
        except KeyError:
            return 0

    def calculate_geography_score(self, author):
        """
        Calcualte gepgraphy score for one author.

        parameters:
            author, str: author

        returns:
            geography_score, float: score between 0 and 1
            count, int: 1 if generic score was used, 0 otherwise
        """
        # Split the conference affiliations by percentile
        country_counts = Counter(self.attendee_affils_list)
        split_50p = np.percentile(list(country_counts.values()), 50)
        top_50p = [
            country for country, count in country_counts.items()
            if count >= split_50p
        ]
        bottom_50p = [
            country for country, count in country_counts.items()
            if count < split_50p
        ]
        gen_prob_score = utils.calculate_gen_prob_geo_score(
            self.author_affils_dict, top_50p, bottom_50p)

        # Get author country
        try:
            affil = self.author_affils_dict[author]

            # Calculate score
            if affil in top_50p:
                geography_score = 0
            elif affil in bottom_50p:
                geography_score = 0.5
            else:
                geography_score = 1
            count = 0

        except KeyError:
            geography_score = gen_prob_score
            count = 1

        return geography_score, count

    def calculate_candidate_scores(self):
        """
        Get scores for all potential candidates.

        returns:
            all_scores, dict: keys are author names, values are composite scores
        """
        print('\nCalculating candidate scores...')

        # Get IDs of clusters with nonzero enrichments
        enriched = defaultdict(list)
        for cluster_type, enrichments in self.enriched_clusters.items():
            for cluster, enrich in enrichments.items():
                if enrich != 0.0:
                    enriched[cluster_type].append(cluster)

        all_scores = {}
        author_score_list = []
        used_generic = 0
        for author in self.author_papers.keys():
            if author not in self.conference_authors.keys():
                author_scores = {}
                # Hierarchically-clustered network scores
                for clust_type, cluster_distances in {
                        'co_citation': self.co_cite_cluster_distances,
                        'co_author': self.co_author_cluster_distances
                }.items():
                    enriched_ids = [
                        clust_id for clust_id, enrich in
                        self.enriched_clusters[clust_type].items()
                        if enrich > 0
                    ]
                    author_scores[clust_type] = self.calculate_mean_hier_score(
                        author, cluster_distances, enriched_ids)

                # Topic cluster scores
                enriched_tops = [
                    clust_id for clust_id, enrich in
                    self.enriched_clusters['topic'].items() if enrich > 0
                ]
                mean_topic_score = self.calculate_topic_pa_score(
                    author, self.topics_to_authors, enriched_tops)
                if ('co_citation'
                        in author_scores.keys()) and ('co_author'
                                                      in author_scores.keys()):
                    author_scores['topic'] = mean_topic_score

                # Geography score
                author_scores[
                    'geography'], count = self.calculate_geography_score(
                        author)
                used_generic += count

                # Record individual scores
                author_score_list.append(author_scores)

                # Combine into composite score
                if len(author_scores) > 0:
                    author_overall_score = mean(author_scores.values())

                # If the author is a previous attendee, wipe score to 0
                if author in self.all_possible_conf_names:
                    author_overall_score = 0

                # Add to all scores
                all_scores[author] = author_overall_score

        print('Used the general geographic probability score for '
              f'{used_generic} of {len(self.author_papers)} authors.')

        # Save all individual scores
        scorepath = f'{self.outpath}/{self.outprefix}_individual_component_scores.jsonl'
        with jsonlines.open(scorepath, 'w') as writer:
            writer.write_all(author_score_list)
        print(f'Saved all individual scores as {scorepath}')

        return all_scores

    def get_conference_candidates(self, cutoff=5):
        """
        Get candidates for conference invitation.

        parameters:
            cutoff, int: number of candidates to return, uses highest scores.

        returns:
            candidates, list of str: candidates
        """
        print('\nBeginning calculations for conference candidates')
        print(
            '---------------------------------------------------------------')

        # Get extra networks
        self.create_co_citation_network()
        self.create_co_author_network()

        # Perform topic modeling
        self.fit_topic_model()

        # Perform other clustering
        self.cluster_co_citation_network()
        self.cluster_co_author_network()

        # Get enrichments
        self.calculate_community_enrichment()

        # Apply heuristic calculation
        all_scores = self.calculate_candidate_scores()

        # Apply threshold
        sorted_scores = {
            k: v
            for k, v in sorted(
                all_scores.items(), key=lambda item: item[1], reverse=True)
        }
        candidates = list(sorted_scores.keys())[:cutoff]

        # Save all composite scores
        score_df = pd.DataFrame.from_dict(sorted_scores,
                                          orient='index',
                                          columns=['composite_score'])
        score_path = f'{self.outpath}/{self.outprefix}_composite_scores.csv'
        score_df.to_csv(score_path, index=True)
        print(f'Saved overall composite scores as {score_path}')

        # Update the co-networks with candidates
        new_co_cite_attrs = {}
        for node, attrs in self.co_cite_net.nodes(data=True):
            if node in candidates:
                new_co_cite_attrs[node] = 'candidate'
        nx.set_node_attributes(self.co_cite_net, new_co_cite_attrs,
                               'is_conference_attendee')
        nx.write_graphml(
            self.co_cite_net,
            f'{self.outpath}/{self.outprefix}_co_citation_network.graphml')
        print(
            f'Saved co-citation network as {self.outpath}/{self.outprefix}_co_citation_network.graphml'
        )

        new_co_auth_attrs = {}
        for node, attrs in self.co_author_net.nodes(data=True):
            if node in candidates:
                new_co_auth_attrs[node] = 'candidate'
        nx.set_node_attributes(self.co_author_net, new_co_auth_attrs,
                               'is_conference_attendee')
        nx.write_graphml(
            self.co_author_net,
            f'{self.outpath}/{self.outprefix}_co_author_network.graphml')
        print(
            f'Saved co-author network as {self.outpath}/{self.outprefix}_co_author_network.graphml'
        )
        return candidates
