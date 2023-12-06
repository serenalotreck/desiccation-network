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


def main(jsonl, output_csv):

    # Read in the data
    print('\nReading in the data...')
    with jsonlines.open(jsonl) as reader:
        data = []
        for obj in reader:
            data.append(obj)

    # Define proportion to assign relevance
    print(f'There are {len(data)} papers in the search results.')
    prop = float(input('Give the proportion of these papers you want to examine: '))
    assert 0 <= prop <= 1, ('Must be a number between 0 and 1, please try again')

    # Get the papers to check
    print('\nSampling papers...')
    num_papers = round(prop*len(data))
    print(f'Sampling {num_papers} papers.')
    to_present = sample(data, num_papers)

    # Start collecting responses
    print('\nYou will now be presented with texts to which to assign relevance. '
            'For each text, type Y if the paper is relevant to the task, and '
            'type N if it is not. If unsure, for example, if a paper has only '
            'a title and no abstract and the title is not clear, please label '
            'as M (for "maybe").')
    relevances = {}
    paper_number = 0
    for paper in to_present:
        try:
            text = paper['title'] + '\n' + paper['abstract']
        except TypeError:
            text = paper['title']
        except KeyError:
            text = paper['title']
        print(f'\nPaper number: {paper_number}, paperId: {paper["paperId"]}')
        print(text)
        labeled = False
        while not labeled:
            lab = input('Is this paper relevant? Y, N or M: ')
            if lab not in ['Y', 'N', 'M']:
                print('Invalid label, please try again.')
            else:
                labeled = True
        relevances[paper['paperId']] = lab
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

    args = parser.parse_args()

    args.jsonl = abspath(args.jsonl)
    args.output_csv = abspath(args.output_csv)

    main(args.jsonl, args.output_csv)
