"""
Script to facilitate the labeling of abstracts as relevant/not relevant for a
given search topic.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import networkx as nx
from random import sample
import jsonlines
import pandas as pd


def main(jsonl, output_csv, to_pull):

    # Read in the data
    print('\nReading in the data...')
    with jsonlines.open(jsonl) as reader:
        data = []
        for obj in reader:
            data.append(obj)

    # Get the paper ID key to use
    try:
        _ = data[0]['paperId']
        key_for_id = 'paperId'
    except KeyError:
        key_for_id = 'UID'

    # Define proportion to assign relevance
    if to_pull == '':
        print(f'There are {len(data)} papers in the search results.')
        prop = float(input('Give the proportion of these papers you want to examine: '))
        assert 0 <= prop <= 1, ('Must be a number between 0 and 1, please try again')

    # Get the papers to check
    print('\nSampling papers...')
    if to_pull == '':
        num_papers = round(prop*len(data))
        print(f'Sampling {num_papers} papers.')
        to_present = sample(data, num_papers)
    else:
        print('Pulling sample to reproduce from previous labeling instance...')
        to_pull_df = pd.read_csv(to_pull, index_col=0)
        to_present = [p for p in data if p[key_for_id] in to_pull_df.index]
        print(f'{len(to_present)} papers obtained.')

    # Start collecting responses
    print('\nYou will now be presented with texts to which to assign relevance. '
            'For each text, type Y if the paper is relevant to the task, and '
            'type N if it is not.')
    relevances = {}
    paper_number = 0
    for paper in to_present:
        try:
            text = paper['title'] + '\n' + paper['abstract']
        except TypeError:
            text = paper['title']
        except KeyError:
            text = paper['title']
        print(f'\nPaper number: {paper_number}, paperId: {paper[key_for_id]}')
        print(text)
        labeled = False
        while not labeled:
            lab = input('Is this paper relevant? Y or N: ')
            if lab not in ['Y', 'N']:
                print('Invalid label, please try again.')
            else:
                labeled = True
        relevances[paper[key_for_id]] = lab
        paper_number += 1

    # Save results
    print('\nDone with labeling! Now saving outputs...')
    df = pd.DataFrame.from_dict(relevances, orient='index',
            columns=['relevant'])
    print(f'Snapshot of results:\n{df.head()}')
    df.to_csv(output_csv)
    print(f'Saved results as {output_csv}')

    print('\nDone!')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Ascribe paper relevance')

    parser.add_argument('jsonl', type=str,
            help='Path to jsonl file for relevance checking')
    parser.add_argument('output_csv', type=str,
            help='Path to save output csv')
    parser.add_argument('-to_pull', type=str, default='',
            help='Path to a csv containing paperIds from a previous run, to '
            'use for the sample')

    args = parser.parse_args()

    args.jsonl = abspath(args.jsonl)
    args.output_csv = abspath(args.output_csv)
    if args.to_pull != '':
        args.to_pull = abspath(args.to_pull)

    main(args.jsonl, args.output_csv, args.to_pull)
