"""
Code to pull papers and their references for a given search result.

Uses the Semantic Scholar Academic Graph API.

Obtains abstracts for initial search results on the first pass, then pulls the
abstracts for each reference, and combines into one output.

Limitations: Can only pull the first 10,000 papers for a query. Is slow.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import requests
from tqdm import tqdm
import sys
sys.path.append('../data/')
from semantic_scholar_API_key import API_KEY
header = {'x-api-key': API_KEY}
import json


def combine_dicts(dict_list):
    """
    Combine a list of dictionaries into one dict when each dict has the same keys and values are lists.
    
    paramters:
        dict_list, list of dict: dicts to combine
    
    returns:
        updated_dict, dict: combined dict
    """
    updated_dict = defaultdict(list)
    for curr_dict in dict_list:
        for key, value in curr_dict.items():
            for item in value:
                updated_dict[key].append(item)
    return updated_dict

def main(search_term, out_path):
    
    # Make initial search
    print('\nMaking initial search query...')
    search_results = []
    for offset in tqdm(range(0, 10000, 100)):
        query = f'http://api.semanticscholar.org/graph/v1/paper/search?query=desiccation+tolerance&offset={offset}&limit=99&fields=title,abstract,references'
        search = requests.get(query, headers=header).json()
        search_results.append(search)
    search_results = combine_dicts(search_results)
    print(f'There are {len(search_results["data"])} papers in the initial search results.')
    
    # Get abstracts for references
    print('\nMaking reference abstract search query...')
    ref_dict = {}
    for paper in tqdm(search_results['data']):
        for ref in paper['references']:
            query = f'http://api.semanticscholar.org/graph/v1/paper/{ref["paperId"]}?fields=title,abstract'
            search = requests.get(query, headers=header).json()
            ref_dict[paper["paperId"]] = search
    print(f'There are {len(ref_dict)} references in this dataset.')
    
    # Combine into one output dict
    print('\nCombining all results...')
    for initial_paper in tqdm(search_results['data']):
        for ref_paper in initial_paper['references']:
            ref_paper['abstract'] = ref_dict[ref_paper['paperId']]
    
    # Save
    print('\nSaving results...')
    with open(out_path, 'w') as myf:
        jsonl.dump(myf, search_results)
    print(f'Saved output as {out_path}')
    
    print('\nDone!')

    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Get citation network papers')
    
    parser.add_argument('search_term', type=str,
                       help='Term to search. Replace spaces with +.')
    parser.add_argument('out_path', type=str,
                       help='File name with full path to save output. '
                       'Extension is .json')
    
    args = parser.parse_args()
    
    args.out_path = abspath(args.out_path)
    
    main(args.search_term, args.out_path)