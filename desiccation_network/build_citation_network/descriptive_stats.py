"""
Calculates basic descriptive stats about a citation network dataset and its
classifications (the outputs of pull_papers.py and classify_papers.py).

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import jsonlines
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter, defaultdict


def get_per_class_cumulative_years(years_per_class):
    """
    Get cumulative years per class.

    parameters:
        years_per_class, dict: years per class

    returns:
        cumulative_years_per_class, nested dict: outer keys are classes, values
            are dicts where key is year and value is the cumulative count
    """
    cumulative_years_per_class = {}
    for cls, yrs in years_per_class.items():
        yr_counts = Counter(yrs)
        ordered_yrs = sorted(yr_counts.keys())
        cumulative_years = {
            y: (yr_counts[ordered_yrs[i]] +
                sum([yr_counts[k] for k in ordered_yrs[:i]])) / 1000
            for i, y in enumerate(ordered_yrs)
        }
        cumulative_years_per_class[cls] = cumulative_years

    return cumulative_years_per_class


def per_class_cumulative(years_per_class, search_term, out_loc, out_prefix):
    """
    Generates a cumulative plot of publications separated by class.

    parameters:
        years_per_class, dict: years per class
        search_term, str: name for title
        out_loc, str: path to directory to save
        out_prefix, str: string to prepend to output filename

    returns:
        None
    """
    colors = {
        'Plant': '#009E73',
        'Animal': '#56B4E9',
        'Microbe': '#E69F00',
        'Fungi': '#F0E442',
        'NOCLASS': '#CC79A7',
        'missing_in_new': '#C7C7C7'
    }
    fig, ax = plt.subplots(1, 1, figsize=(24, 6))
    cumulative_years_per_class = get_per_class_cumulative_years(
        years_per_class)
    for cls, cumulative_years in cumulative_years_per_class.items():
        ax.scatter(cumulative_years.keys(),
                   cumulative_years.values(),
                   color=colors[cls],
                   alpha=0.5,
                   label=cls)
    plt.legend()
    plt.title(
        f'Cumulative publications over time for search term "{search_term}"')
    plt.ylabel('Total publications (thousands)')
    plt.xlabel('Year')
    savepath = f'{out_loc}/{out_prefix}_per_class_cumulative_plot.png'
    plt.savefig(savepath, format='png', dpi=600, bbox_inches='tight')
    print(f'Saved per-class cumulative plot as {savepath}')


def get_per_class_years(flattened_papers, paper_classifications):
    """
    Get per class years.

    parameters:
        flattened_papers, dict: papers
        paper_classifications, dict: keys are papers, values are classes

    returns:
        years_per_class, dict: keys are classes, values are lists of years
    """
    years_per_class = defaultdict(list)
    missing_class = 0
    for pid, p in flattened_papers.items():
        try:
            year = int(p['year'])
        except KeyError:
            continue
        try:
            p_class = paper_classifications[pid]
        except KeyError:
            missing_class += 1
            continue
        if year is not None:
            years_per_class[p_class].append(year)
    if missing_class > 0:
        print(f'{missing_class} papers were dropped because they were not '
              'found in the classification dataset.')

    return years_per_class


def per_class_histogram(flattened_papers, paper_classifications, search_term,
                        out_loc, out_prefix):
    """
    Generates a histogram of publication years separated by classification.

    parameters:
        flattened_papers, dict: keys are paperId's, values are papers
        paper_classifications, dict: keys are paperId's, values are classes
        search_term, str: name for title
        out_loc, str: path to directory to save
        out_prefix, str: string to prepend to output filename

    returns:
        years_per_class, dict: years per class
    """
    # Prep data
    years_per_class = get_per_class_years(flattened_papers,
                                          paper_classifications)

    colors = {
        'Plant': '#009E73',
        'Animal': '#56B4E9',
        'Microbe': '#E69F00',
        'Fungi': '#F0E442',
        'NOCLASS': '#CC79A7',
        'missing_in_new': '#C7C7C7'
    }
    fig, ax = plt.subplots(1, 1)
    for cls, yrs in years_per_class.items():
        _ = ax.hist(yrs, bins=100, color=colors[cls], label=cls, alpha=0.5)
    plt.legend()
    plt.title(
        f'New publications per year by study system for search term "{search_term}"'
    )
    plt.xlabel('Publication Year')
    plt.ylabel('Count')
    savepath = f'{out_loc}/{out_prefix}_histogram_per_class.png'
    plt.savefig(savepath, format='png', dpi=600, bbox_inches='tight')
    print(f'Saved per-class histogram as {savepath}')

    return years_per_class


def get_overall_cumulative_years(paper_years):
    """
    Get overall cumulative year numbers.

    parameters:
        paper_years, list of int: list of all paper years

    returns:
        cumulative_years, dict: keys are years, values are number of papers up
            to that year, divided by 1,000
    """
    counts_per_year = Counter(paper_years)
    ordered_years = sorted(counts_per_year.keys())
    cumulative_years = {
        y: (counts_per_year[ordered_years[i]] +
            sum([counts_per_year[k] for k in ordered_years[:i]])) / 1000
        for i, y in enumerate(ordered_years)
    }

    return cumulative_years


def overall_cumulative(paper_years, search_term, out_loc, out_prefix):
    """
    Generates, shows and saves overall cumulative pubs.

    parameters:
        paper_years, list of int: publication years
        search_term, str: name for title
        out_loc, str: path to directory to save
        out_prefix, str: string to prepend to output filename

    returns:
        None
    """
    cumulative_years = get_overall_cumulative_years(paper_years)
    fig, ax = plt.subplots(1, 1)
    ax.scatter(cumulative_years.keys(), cumulative_years.values())
    plt.title(
        f'Cumulative publications over time for search term "{search_term}"')
    plt.ylabel('Total publications (thousands)')
    plt.xlabel('Year')
    savepath = f'{out_loc}/{out_prefix}_overall_cumulative_pubs.png'
    plt.savefig(savepath, format='png', dpi=600, bbox_inches='tight')
    print(f'Saved cumulative plot as {savepath}')


def get_overall_years(flattened_papers):
    """
    Helper for overall_historgram, gets paper years.
    
    parameters:
        flattened_papers, list of dict: papers

    returns:
        years, list of int: paper years
    """
    missing_years = 0
    paper_years = []
    for pid, p in flattened_papers.items():
        try:
            year = p['year']
            if year is not None:
                paper_years.append(int(year))
            else:
                missing_years += 1
        except KeyError:
            missing_years += 1
    print(
        f'{missing_years} papers of {len(flattened_papers.keys())} total papers did not have a year of publication.'
    )

    return paper_years


def overall_histogram(flattened_papers, search_term, out_loc, out_prefix):
    """
    Generates, shows and saves overall histogram.

    parameters:
        flattened_papers, dict: keys are paperIds, values are papers
        search_term, str: name for title
        out_loc, str: path to directory to save
        out_prefix, str: string to prepend to output filename

    returns:
        paper_years, list of int: publication years
    """
    paper_years = get_overall_years(flattened_papers)

    fig, ax = plt.subplots(1, 1)
    _ = ax.hist(paper_years, bins=100)
    plt.title(f'New publications per year for search term "{search_term}"')
    plt.xlabel('Publication Year')
    plt.ylabel('Count')
    savepath = f'{out_loc}/{out_prefix}_overall_pub_histogram.png'
    plt.savefig(savepath, format='png', dpi=600, bbox_inches='tight')
    print(f'Saved histogram as {savepath}')

    return paper_years


def flatten_papers(papers, keyname):
    """
    Flatten pulled papers and their data.

    parameters:
        papers, list: list of papers to flatten
        keyname, str: whether to use "paperId" or "UID" to access papers

    returns:
        flattened_papers, dict: flattened papers indexed by paperId
    """
    flattened_papers = {}
    for p in papers:
        try:
            flattened_papers[p[keyname]] = {
                'title': p['title'],
                'abstract': p['abstract'],
                'year': p['year']
            }
        except KeyError as e:
            if e.args[0] == 'abstract':
                try:
                    flattened_papers[p[keyname]] = {
                        'title': p['title'],
                        'year': p['year']
                    }
                except KeyError:
                    flattened_papers[p[keyname]] = {'title': p['title']}
            elif e.args[0] == 'year':
                try:
                    flattened_papers[p[keyname]] = {
                        'title': p['title'],
                        'abstract': p['abstract']
                    }
                except KeyError:
                    flattened_papers[p[keyname]] = {'title': p['title']}
        ## Uncomment to include references
        # for r in p['references']:
        #     try:
        #         flattened_papers[r[keyname]] = {'title': r['title'], 'abstract': r['abstract'], 'year': r['year']}
        #     except KeyError as e:
        #         if e.args[0] == 'abstract':
        #             try:
        #                 flattened_papers[r[keyname]] = {'title': r['title'], 'year': r['year']}
        #             except KeyError:
        #                 flattened_papers[r[keyname]] = {'title': r['title']}
        #         elif e.args[0] == 'year':
        #             try:
        #                 flattened_papers[r[keyname]] = {'title': r['title'], 'abstract': r['abstract']}
        #             except KeyError:
        #                 flattened_papers[r[keyname]] = {'title': r['title']}

    return flattened_papers


def main(jsonl, graphml, search_term, out_loc, out_prefix):

    # Read in the data
    print('\nReading in data...')
    with jsonlines.open(jsonl) as reader:
        pulled_papers = []
        for obj in reader:
            pulled_papers.append(obj)
    classified_graph = nx.read_graphml(graphml)
    try:
        pulled_papers[0]['paperId']
        keyname = 'paperId'
    except KeyError:
        keyname = 'UID'

    # Prep the data
    print('\nPreparing the data and performing initial statistics...')
    flattened_papers = flatten_papers(pulled_papers, keyname)
    paper_classifications = {
        k: v['study_system']
        for k, v in classified_graph.nodes(data=True)
    }
    print(f'There are {len(flattened_papers)} unique papers in the dataset.')
    classes, flattened, intersection = len(set(paper_classifications)), len(
        set(flattened_papers.keys())), len(
            set(flattened_papers.keys()).intersection(
                set(paper_classifications)))
    print('Performing common-sense check on the two versions of the dataset:')
    print(f'There are {intersection} papers in common between both datasets.')
    if (classes - intersection != 0) or (flattened - intersection != 0):
        print(
            'This is not identical to the number of papers in each dataset alone.'
        )
        if classes - intersection > 0:
            print(
                f'There are {classes - intersection} papers missing from the classified papers.'
            )
        if flattened - intersection > 0:
            print(
                f'There are {flattened - intersection} papers missing from the original papers.'
            )
    else:
        print('This is identical to the number of papers in each dataset.')

    # Generate overall histogram
    print('\nGenerating overall publication histogram...')
    pub_years = overall_histogram(flattened_papers, search_term, out_loc,
                                  out_prefix)

    # Generate overall cumulative
    print('\nGenerating overall cumulative publications per year chart...')
    overall_cumulative(pub_years, search_term, out_loc, out_prefix)

    # Generate per-class histogram
    print('\nGenerating per-class histogram...')
    years_per_class = per_class_histogram(flattened_papers,
                                          paper_classifications, search_term,
                                          out_loc, out_prefix)

    # Generate per-class cumulative
    print('\nGenerating per-class overall plot...')
    per_class_cumulative(years_per_class, search_term, out_loc, out_prefix)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Get descriptive stats')

    parser.add_argument('jsonl',
                        type=str,
                        help='Path to output of pull_papers.py')
    parser.add_argument(
        'graphml',
        type=str,
        help='Path to output of classify_papers.py that took the jsonl arg '
        'as input')
    parser.add_argument('search_term',
                        type=str,
                        help='String to use in chart titles')
    parser.add_argument('out_loc', type=str, help='Path to save outputs')
    parser.add_argument('out_prefix',
                        type=str,
                        help='String to prepend to output file names')

    args = parser.parse_args()

    args.jsonl = abspath(args.jsonl)
    args.graphml = abspath(args.graphml)
    args.out_loc = abspath(args.out_loc)

    main(args.jsonl, args.graphml, args.search_term, args.out_loc,
         args.out_prefix)
