"""
Script to get publication titles and locations for conference invite candidates.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import jsonlines
from collections import defaultdict
import numpy as np
import pandas as pd


def get_author_info(candidate_list, dataset):
    """
    Get publications, years, and affiliations for candidate authors.

    parameters:
        candidate_list, list of str: candidate WOS names
        dataset, list of dict: dataset

    returns:
        candidate_data, df: columns are candidate, publication_title,
            publication_abstract, publication_year, affiliation_at_pub
    """
    candidate_data_dict = defaultdict(list)
    for paper in dataset:
        for author in paper['authors']:
            try:
                if author['wos_standard'].lower() in candidate_list:
                    try:
                        addresses = {add['addr_no']: add for add in paper['addresses']}
                        country = addresses[author['addr_no']]['country']
                    except KeyError:
                        country = np.nan
                    try:
                        candidate_data_dict['publication_title'].append(paper['title'])
                    except KeyError:
                        candidate_data_dict['publication_title'].append(np.nan)
                    try:
                        candidate_data_dict['publication_abstract'].append(paper['abstract'])
                    except KeyError:
                        candidate_data_dict['publication_abstract'].append(np.nan)
                    try:
                        candidate_data_dict['publication_year'].append(paper['year'])
                    except KeyError:
                        candidate_data_dict['publication_year'].append(np.nan)
                    try:
                        candidate_data_dict['candidate'].append(author['wos_standard'].lower())
                    except KeyError:
                        candidate_data_dict['candidate'].append(np.nan)
                    candidate_data_dict['affiliation_at_pub'].append(country)
                        
            except KeyError:
                continue
    
    candidate_data = pd.DataFrame(candidate_data_dict)
    
    return candidate_data
    

def main(candidates, dataset, outpath, outprefix):
    
    # Read in candidates
    with open(candidates) as myf:
        cands = [l.strip() for l in myf.readlines()]
    print(f'\nThere are {len(cands)} candidates.')

    # Read in dataset
    with jsonlines.open(dataset) as reader:
        data = [obj for obj in reader]
    
    # Process
    print('\nGetting candidate data...')
    cand_df = get_author_info(cands, data)
    print('Snapshot of candidate dataframe:')
    print(cand_df.head())
    
    # Save
    savename = f'{outpath}/{outprefix}_candidate_publication_info.csv'
    cand_df.to_csv(savename, index=False)
    print(f'\nSaved candidate publication information as {savename}')
    
    print('\nDone!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Describe candidates')
    
    parser.add_argument('candidates', type=str,
            help='Path to .txt file with candidates')
    parser.add_argument('dataset', type=str,
            help='Path to the jsonl dataset used to get candidates')
    parser.add_argument('outpath', type=str,
            help='Path to directory to save output')
    parser.add_argument('outprefix', type=str,
            help='String to prepend to outputs')

    args = parser.parse_args()
    
    args.candidates = abspath(args.candidates)
    args.dataset = abspath(args.dataset)
    args.outpath = abspath(args.outpath)
    
    main(args.candidates, args.dataset, args.outpath, args.outprefix)