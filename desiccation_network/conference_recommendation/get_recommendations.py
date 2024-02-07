"""
Generate conference invite recommendations based on bibliometric factors.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import sys
import json
import jsonlines
import networkx as nx
from ast import literal_eval
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
import openai
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance, KeyBERTInspired, PartOfSpeech, OpenAI
import pandas as pd
from recommendation_system import RecommendationSystem


def build_topic_model(topic_model_config):
    """
    Build topic model from a config. Assumes that all of sentence transformer,
    umap, vectorizer and representations models are present in config.

    Currently supports MMR and OpenAI representation models.
    """
    embedding_model = SentenceTransformer(
        topic_model_config['sent_trans_model'])
    umap_model = UMAP(**topic_model_config['umap_params'])
    topic_model_config['vectorizer_params']['ngram_range'] = tuple(topic_model_config['vectorizer_params']['ngram_range'])
    vectorizer_model = CountVectorizer(
        **topic_model_config['vectorizer_params'])
    if topic_model_config['representation_model_name'] == 'openai':
        with open(abspath(topic_model_config['openai_api_key_path'])) as myf:
            API_KEY = literal_eval(myf.read().split(' ')[-1].strip())
        client = openai.OpenAI(api_key=API_KEY)
        representation_model = OpenAI(
            client, **topic_model_config['representation_params'])
    elif topic_model_config['representation_model_name'].lower() == 'mmr':
        representation_model = MaximalMarginalRelevance(
            **topic_model_config['representation_params'])

    return BERTopic(embedding_model=embedding_model,
                    umap_model=umap_model,
                    representation_model=representation_model,
                    vectorizer_model=vectorizer_model), vectorizer_model, representation_model


def main(paper_dataset, classed_cite_net, topic_model_config, attendees,
         alt_names, cutoff, enrich_threshold, prod_threshold, save_clusters,
         outpath, outprefix):

    # Build topic model
    topic_model, vec_model, rep_model = build_topic_model(topic_model_config)
    if topic_model_config['outlier_reduction']:
        outlier_reduction_params = topic_model_config[
            'outlier_reduction_params']
    else:
        outlier_reduction_params = None

    # Build recommendation instance
    rec_model = RecommendationSystem(paper_dataset, classed_cite_net,
                                     topic_model, vec_model, rep_model, attendees, alt_names,
                                     outlier_reduction_params,
                                     enrich_threshold, prod_threshold,
                                     save_clusters, outpath, outprefix)

    # Get recommendations
    recs = rec_model.get_conference_candidates(cutoff)

    # Save
    print('\nSaving output candidates...')
    savename = f'{outpath}/{outprefix}_top_{cutoff}_candidates.txt'
    with open(savename, 'w') as myf:
        myf.write('\n'.join(recs))
    print(f'Saved output as {savename}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate conference recs')

    parser.add_argument(
        'jsonl_path',
        type=str,
        help='Path to jsonl dataset with papers, authors and institutions')
    parser.add_argument(
        'graphml_path',
        type=str,
        help='Path to classified citation network graphml file')
    parser.add_argument(
        'topic_model_config',
        type=str,
        help='Path to a json file with modeling preferences for BERTopic')
    parser.add_argument(
        'attendee_path',
        type=str,
        help='Path to .csv file with conference attendees, columns are '
        'Surname, First_name, Affiliation, Country')
    parser.add_argument(
        'alt_name_path',
        type=str,
        help='Path to alternative publication names for attendees, columns '
        'are Registration_surname, Registration_first_name, '
        'Alternative_name_1..., Maiden_name')
    parser.add_argument('-cutoff',
                        type=float,
                        default=0.1,
                        help='Proportion of top candidates to return.')
    parser.add_argument(
        '-enrich_threshold',
        type=float,
        default=None,
        help='Number between 0 and 1, proportion of authors in a cluster '
        'that should be conference attendees to consider a cluster '
        '"enriched" in conference attendees. For smaller conferences, this '
        'should be left as None, as few clusters will contain authors and '
        'they will only be present in smaller numbers')
    parser.add_argument(
        '-prod_threshold',
        type=float,
        default=None,
        help='Number between 0 and 1, the percent of authors to consider '
        'based on publications')
    parser.add_argument('--save_clusters',
                        action='store_true',
                        help='Whether or not to save cluster to author maps.')
    parser.add_argument('outpath',
                        type=str,
                        default='',
                        help='Path to directory to save output')
    parser.add_argument('outprefix',
                        type=str,
                        default='',
                        help='String to prepend to output file names')

    args = parser.parse_args()

    # Read in files here
    with jsonlines.open(abspath(args.jsonl_path)) as reader:
        paper_dataset = [obj for obj in reader]

    classed_cite_net = nx.read_graphml(abspath(args.graphml_path))

    with open(abspath(args.topic_model_config)) as myf:
        topic_model_config = json.load(myf)

    attendees = pd.read_csv(abspath(args.attendee_path))

    alt_names = pd.read_csv(abspath(args.alt_name_path))

    args.outpath = abspath(args.outpath)

    main(paper_dataset, classed_cite_net, topic_model_config, attendees,
         alt_names, args.cutoff, args.enrich_threshold, args.prod_threshold,
         args.save_clusters, args.outpath, args.outprefix)
