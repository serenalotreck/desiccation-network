"""
Classifies nodes ina citation network by study organism.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import json
from tqdm import tqdm
from taxonerd import TaxoNERD
import taxoniq


def classify_orgs(ents, defs):
    """
    Get organism classifications from a list of NCBI Taxonomy IDs

    parameters:
        ents, list of int: NCBI Taxonomy ID's
        defs, dict: keys are lineage categories, values are the final
            kingdom classification for those categories

    returns:
        kings, list of str: unique kingdom classifications
    """
    kings = []
    for i in ents:
        try:
            t1 = taxoniq.Taxon(i)
            lineage = [t.scientific_name for t in t1.ranked_lineage]
            if lineage[-1] == 'Bacteria' or lineage[-1] == 'Archea':
                kings.append(defs[lineage[-1]])
            elif lineage[-1] == 'Eukaryota':
                try:
                    kings.append(defs[lineage[-2]])
                except KeyError:
                    continue
        except KeyError:
            continue

    kings = list(set(kings))
    return kings


def classify_paper(title, abstract, taxonerd):
    """
    Gets the Kingdom classification of a paper title.
    
    parameters:
        title, str: title of the paper
        abstract, str: abstract of the paper
        taxonerd, TaxoNERD instance: model to use for classification

    returns:
        king, str: kindgom of the paper
    """
    # Do TaxoNERD classification
    title_df = taxonerd.find_in_text(title)

    # Get the unique organisms
    title_ents = list(
        set([
            title_df['entity'][j][0][0].split("NCBI:")[1]
            for j in range(len(title_df))
        ]))

    # Set up definitions for kingdom classification
    defs = {
        'Metazoa': 'Animal',
        'Viridiplantae': 'Plant',  # Consider adding algae
        'Bacteria': 'Microbe',
        'Archea': 'Microbe'
    }

    # Classify unique organisms
    title_classes = classify_orgs(title_ents, defs)

    # If abstract isn't None, also classify abstract
    if abstract is not None:
        abstract_df = taxonerd.find_in_text(abstract)
        abstract_ents = list(
            set([
                abstract_df['entity'][j][0][0].split("NCBI:")[1]
                for j in range(len(abstract_df))
            ]))
        abstract_classes = classify_orgs(abstract_ents, defs)
    else:
        abstract_classes = []

    # Get the kingdom
    if (len(title_classes) == len(abstract_classes) ==
            1) and (title_classes == abstract_classes):
        king = title_classes[0]
    elif len(title_classes) == 0 and len(abstract_classes) == 1:
        king = abstract_classes[0]
    elif len(abstract_classes) == 0 and len(title_classes) == 1:
        king = title_classes[0]
    else:
        # For now, come back to this
        king = 'NOCLASS'
    return king


def generate_links_with_classification(search_results, taxonerd):
    """
    Generate a list of edges by paper ID from the results of a Semantic Scholar query. Removes malformed
    citations with no paperID, and classifies nodes by the organisms in their titles.
    
    parameters:
        search_results, dict: query results
        taxonerd, TaxoNERD instance: model to use for classification
        
    returns:
        nodes, list of two-tuple: the paper ID and an attribute dictionary containing the paper's title
        edges, list of three-tuple: the paper IDs of both citing and cited paper, and an attribute dictionary with the paper's title
    """

    # Classify nodes and identify edges
    nodes, edges = [], []
    i = 0
    for paper in tqdm(search_results):
        org = classify_paper(paper['title'], paper['abstract'], taxonerd)
        citing = (paper['paperId'], {
            'title': paper['title'],
            'study_system': org
        })
        cited = [(p['paperId'], {
            'title':
            p['title'],
            'study_system':
            classify_paper(p['title'], p['abstract'], taxonerd)
        }) for p in paper['references'] if p['paperId'] is not None]
        nodes.append(citing)
        nodes.extend(cited)
        edges.extend([(citing[0], p[0], num)
                      for num, p in enumerate(cited, i)])
        i += len(cited)
    return nodes, edges


def main(search_result_path, graph_save_path, prefer_gpu):

    # Read in search results
    print('\nLoading citation data...')
    with open(search_result_path) as myf:
        search_results = json.load(myf)

    # Define TaxoNERD model for classification
    print('\nLoading TaxoNERD model...')
    taxonerd = TaxoNERD(prefer_gpu=prefer_gpu)
    nlp = taxonerd.load(model="en_core_eco_biobert",
                        linker="ncbi_taxonomy",
                        threshold=0.7)

    # Get graph nodes and edges
    print('\nFormatting and classifying nodes and edges...')
    nodes, edges = generate_links_with_classification(search_results, taxonerd)

    # Build graph
    print('\nBuilding graph...')
    citenet = nx.MultiDiGraph()
    _ = citenet.add_nodes_from(nodes)
    _ = citenet.add_edges_from(edges)

    # Save graph
    print('\nSaving graph...')
    nx.write_graphml(citenet, graph_save_path)
    print(f'Graph saved to {graph_save_path}')

    print('\nDone!')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Classify nodes and format graph')

    parser.add_argument('search_result_path',
                        type=str,
                        help='Output from pull_papers.py')
    parser.add_argument('graph_save_path',
                        type=str,
                        help='Path to save graph, extension is .graphml')
    parser.add_argument('--prefer_gpu', action='store_true',
                        help='Whether or not GPU is available to use')

    args = parser.parse_args()

    args.search_result_path = abspath(args.search_result_path)
    args.graph_save_path = abspath(args.graph_save_path)

    main(args.search_result_path, args.graph_save_path, args.prefer_gpu)
