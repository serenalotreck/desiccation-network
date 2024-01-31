"""
Script to facilitate the labeling of keywords as relevant/not relevant for a
given search topic.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import networkx as nx
from random import sample
import jsonlines
import pandas as pd


def main(keyword_csv, output_csv):

    # Read in the data
    print('\nReading in the data...')
    keywords = pd.read_csv(keyword_csv)

    # Start collecting responses
    print('\nYou will now be presented with keywords to which to assign relevance. '
            'For each keyword, type Y if it is relevant to the task, and '
            'type N if it is not.')
    relevances = {}
    key_number = 0
    for keyword in keywords['keywords']:
        print(f'\nKeyword number: {key_number}')
        print(keyword)
        labeled = False
        while not labeled:
            lab = input('Is this keyword relevant? Y or N: ')
            if lab not in ['Y', 'N']:
                print('Invalid label, please try again.')
            else:
                labeled = True
        relevances[keyword] = lab
        key_number += 1

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

    parser.add_argument('keyword_csv', type=str,
            help='Path to csv file for relevance checking, with one column '
            'labeled "keywords"')
    parser.add_argument('output_csv', type=str,
            help='Path to save output csv')

    args = parser.parse_args()

    args.keyword_csv = abspath(args.keyword_csv)
    args.output_csv = abspath(args.output_csv)

    main(args.keyword_csv, args.output_csv)
