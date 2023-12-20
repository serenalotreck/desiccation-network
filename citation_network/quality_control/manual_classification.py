"""
Given a graph with classified nodes, takes a sample of nodes from the NOCLASS
group, retrieves their titles and abstracts, and presents a given number to the
user for manual classification. Saves output as a csv file.

Intended as a diagnostic tool for missing classifications.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import networkx as nx
from random import sample
import requests
import sys
sys.path.append('../data/')
from semantic_scholar_API_key import API_KEY
header = {'x-api-key': API_KEY}
import pandas as pd


def main(graphml, output_csv):

    print('\nReading graph file...')
    graph = nx.read_graphml(graphml)

    print('\nGetting nodes with no classification...')
    noclass_paperIds = []
    for node, attrs in graph.nodes(data=True):
        if attrs['study_system'] == 'NOCLASS':
            noclass_paperIds.append(node)
    print(f'{len(noclass_paperIds)} of {len(graph.nodes)} nodes are NOCLASS.')
    prop = float(input('Give the proportion of these nodes you want to classify: '))
    assert 0 <= prop <= 1, ('Must be a number between 0 and 1, please try again')

    print('\nSampling and retrieving papers...')
    num_to_retrieve = round(prop*len(noclass_paperIds))
    print(f'Retrieving {num_to_retrieve} abstracts.')
    to_retrieve = sample(noclass_paperIds, num_to_retrieve)
    if len(to_retrieve) > 500:
        num_reps = len(to_retrieve)//500 + 1
    else: num_reps = 1
    all_retrievals = []
    for i in range(num_reps):
        to_retr_subset = to_retrieve[i*500: 500*(i+1)]
        r = requests.post(
            'https://api.semanticscholar.org/graph/v1/paper/batch',
            headers=header,
            params={'fields': 'title,abstract'},
            json={"ids": to_retr_subset}
        ).json()
        all_retrievals.append(r)
    to_classify = {}
    for r in all_retrievals:
        for p in r:
            print(p)
            try:
                if p['abstract'] is not None:
                    text = p['title'] + '\n' + p['abstract']
                else:
                    text = p['title']
            except KeyError:
                text = p['title']
            try:
                to_classify[p['paperId']] = text
            except KeyError:
                to_classify[p['UID']] = text

    print('\nYou will now be presented with text to classify. For each doc, '
            'when prompted, enter P for plant, A for animal, F for fungi, M '
            'for microbe, or U for unclear.')
    classes = {}
    paper_number = 0
    for paperId, text in to_classify.items():
        print(f'\nPaper number {paper_number}, {paperId}:\n{text}')
        classed = False
        while not classed:
            cls = input('Input paper class here: ')
            if cls not in ['A', 'P', 'F', 'M', 'U']:
                print('Invalid classification ID, please try again.')
            else:
                classed = True
        classes[paperId] = cls
        paper_number += 1

    print('\nDone with classifications! Now saving output...')
    df = pd.DataFrame.from_dict(classes, orient='index')
    print(f'Snapshot of classification dataframe:\n{df.head()}')
    df.to_csv(output_csv)
    print(f'Saved dataframe to {output_csv}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Manual classification')

    parser.add_argument('graphml', type=str,
            help='Graph file to use')
    parser.add_argument('output_csv', type=str,
            help='Path to save output')

    args = parser.parse_args()

    args.graphml = abspath(args.graphml)
    args.output_csv = abspath(args.output_csv)

    main(args.graphml, args.output_csv)
