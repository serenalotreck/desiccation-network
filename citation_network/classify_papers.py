"""
Classifies nodes ina citation network by study organism.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
import json
from tqdm import tqdm
from taxonerd import TaxoNERD
from taxonerd.linking.linking import EntityLinker
import taxoniq
from spacy.tokens import Span
from collections import Counter
import networkx as nx
import time
import regex


def fuzzy_match_kingdoms(paper_dict, generic_dict):
    """
    Find fuzzy matches for generic names in the title and abstracts of papers
    not classified by other means.

    parameters:
        paper_dict, dict: keys are "title" and "abstract"
        generic_dict, dict: keys are generic terms, values are kingdom names

    returns:
        classes, list of str: kingdoms identified
    """
    classes = []
    for term, king in generic_dict.items():

        # Combine text to search
        if paper_dict['abstract'] is not None:
            text = paper_dict['title'] + ' ' + paper_dict['abstract']
        else:
            text = paper_dict['title']

        # Build the regex string
        sub_len = len(term)//3
        spacejoined = "\s+".join(term.split())
        reg = fr'\b({spacejoined}){{e<={sub_len}}}\b'

        # Search in paper
        matches = regex.search(reg, text, flags=regex.IGNORECASE)

        # Map to classes
        if matches is not None:
            classes.append(king)

    return classes


def map_taxoniq(uniq_names, doc, species_ids):
    """
    Use taxoniq directly to attempt to map species names not linked by
    TaxoNERD.

    parameters:
        uniq_names, list of str: unique species names
        doc, spacy Doc object: doc with linked entities
        species_ids, dict: keys are species, values are NCBI ID's

    returns:
        species_ids, dict: updated species IDs with futher identified species
    """
    missed = [s for s in uniq_names if uniq_names not in [ent.text for ent in
        doc.ents]]
    still_missed = []
    for ent in missed:
        try:
            t1 = taxoniq.Taxon(scientific_name=ent)
            tax_id = t1.tax_id
            species_ids[ent] = tax_id
        except KeyError:
            still_missed.append(ent)
    print(f'Linked an additional {len(missed) - len(still_missed)} entities.')

    return species_ids


def map_paper_species(paper_spec_names, species_dict, generic_dict, to_classify):
    """
    Get the kingdom classifications for each paper.

    parameters:
        paper_spec_names, dict: keys are paper ID's, values are lists of species
        species_dict, dict: keys are species names, values are kingdoms
        generic_dict, dict: keys are generic descriptors of a kingdom, values
            are kingdom names
        to_classify, dict: keys are paper IDs, values are dict with title and
            abstract

    returns:
        classified, dict: keys are paper ID's, values are kingdoms
    """
    # Map species classifications
    classified = {}
    species_missed = []
    additional_papers_identified = 0
    for paperId, spec_names in paper_spec_names.items():
        uniq_spec = list(set(spec_names))
        classes = []
        # Try either generic terms 
        if (len(uniq_spec) == 0) and (generic_dict != ''):
            classes = fuzzy_match_kingdoms(to_classify[paperId], generic_dict)
            if len(classes) != 0:
                additional_papers_identified += 1
        for spec in uniq_spec:
            try:
                classes.append(species_dict[spec])
            except:
                species_missed.append(spec)
                continue
        if len(classes) == 1:
            # If no disagreement, return
            king = classes[0]
        elif len(classes) > 1:
            # If disagreement, return the most common class
            # If there's a tie, this method will resort to the class that was
            # inserted first in the Counter object
            king = Counter(classes).most_common(1)[0][0]
        else:
            # If there's no classification, return NOCLASS
            king = 'NOCLASS'
        classified[paperId] = king

    print(
        f'{len(set(species_missed))} species names were not identifiable in the classification dict'
    )
    if generic_dict != '':
        print(f'An additional {additional_papers_identified} papers were identified '
            'because of the generic fuzy match approach')

    return classified


def get_species_classes(paper_spec_names, nlp, linker):
    """
    Get organism classifications from a list of NCBI Taxonomy IDs

    parameters:
        paper_spec_names, dict: keys are paperId's, values are lists of
            species names for the paper
        nlp, spacy NLP object: model to use to make doc for linking
        linker, taxonerd EntityLinker instance: linker to use to get IDs

    returns:
        species_dict, keys are species names, values are kingdom
            classifications
    """
    # Get unique species names
    all_names = [s for p, ss in paper_spec_names.items() for s in ss]
    print(f'There were {len(all_names)} non-unique entities identified.')
    uniq_names = list(set(all_names))
    print(f'There are {len(uniq_names)} unique species names to classify.')

    # Make into a doc with entities
    print('Formatting unique entities into one document...')
    doc = nlp(' '.join(uniq_names))
    span_idxs = []
    for i, ent in enumerate(uniq_names):
        if i == 0:
            start = 0
        else:
            start = len(' '.join(uniq_names[:i]).split(' '))
        end = start + len(ent.split(' '))
        span_idxs.append((start, end))
    spans = [Span(doc, e[0], e[1], "ENTITY") for e in span_idxs]
    doc.set_ents(spans)
    print(f'Number of entities in dummy doc: {len(doc.ents)}')

    # Perform linking
    print('Performing entity linking...')
    start = time.time()
    doc = linker(doc)
    print(f'Time to apply linker: {time.time() - start: .2f}')
    species_ids = {}
    print(f'There are {len(doc.ents)} remaining species names after linking.')
    for ent in doc.ents:
        ent_id = ent._.kb_ents[0][0].split(':')[1]
        species_ids[ent.text] = ent_id
    print(f'Using taxoniq to attempt to map the missed entities...')
    species_ids = map_taxoniq(uniq_names, doc, species_ids)

    # Map to kingdoms
    print('Mapping to kingdom classifications...')
    species_dict = {}
    defs = {
        'Metazoa': 'Animal',
        'Viridiplantae': 'Plant',  # Consider adding algae
        'Bacteria': 'Microbe',
        'Archea': 'Microbe'
    }
    not_tracked_lineage, no_sub_eukaryota_lineage_identified, not_found_in_taxonomy = 0, 0, 0
    for spec_ent, ncbi_id in tqdm(species_ids.items()):
        try:
            t1 = taxoniq.Taxon(ncbi_id)
            lineage = [t.scientific_name for t in t1.ranked_lineage]
            if lineage[-1] == 'Bacteria' or lineage[-1] == 'Archea':
                king = defs[lineage[-1]]
            elif lineage[-1] == 'Eukaryota':
                try:
                    king = defs[lineage[-2]]
                except KeyError:
                    not_tracked_lineage += 1
                    continue
                except IndexError:
                    no_sub_eukaryota_lineage_identified += 1
                    continue
        except KeyError:
            not_found_in_taxonomy += 1
            continue
        species_dict[spec_ent] = king
    #print(
    #    f'{lost_species} unique species names were lost during kingdom identification.'
    #)
    print(f'{not_tracked_lineage} species were lost because their lineage wasnt '
            f'one of interest, {no_sub_eukaryota_lineage_identified} were lost '
            'because they only were identified as eykaryota, and '
            f'{not_found_in_taxonomy} because their ID wasnt found in NCBI '
            'Taxonomy')
    not_classed_empty = []
    not_classed_all = []
    for paper, specs in paper_spec_names.items():
        in_dict = False
        for  spec in specs:
            if spec in species_dict.keys():
                in_dict = True
        if not in_dict:
            not_classed_all.append(paper)
        if len(specs) == 0:
            not_classed_empty.append(paper)
    print('Number of papers missing a classification because all its species '
            f'didnt get linked: {len(not_classed_all)}')
    print([paper_spec_names[paper] for paper in not_classed_all])

    return species_dict


def get_species_names(title, abstract, taxonerd):
    """
    Gets the species names for a paper.

    parameters:
        title, str: title of the paper
        abstract, str: abstract of the paper
        taxonerd, TaxoNERD instance: model to use for classification

    returns:
        species, list of str: species names in the paper
    """
    # Combine title and abstract
    if abstract is not None:
        text = title + ' ' + abstract
    else:
        text = title

    # Do TaxoNERD classification
    ent_df = taxonerd.find_in_text(text)

    # Get the unique organisms
    try:
        species = list(set(ent_df['text']))
    except KeyError:
        species = []

    return species


def generate_links_without_classification(search_results):
    """
    Generate a list of edges by paper ID from the results of a Semantic Scholar query. Removes malformed
    citations with no paperID.

    parameters:
        search_results, dict: query results

    returns:
        nodes, list of two-tuple: the paper ID and an attribute dictionary containing the paper's title
        edges, list of three-tuple: the paper IDs of both citing and cited paper, and an attribute dictionary with the paper's title
    """
    nodes, edges = [], []
    i = 0
    for paper in tqdm(search_results):
        citing = (paper['paperId'], {'title': paper['title']})
        cited = [(p['paperId'], {
            'title': p['title']
        }) for p in paper['references'] if p['paperId'] is not None]
        nodes.append(citing)
        nodes.extend(cited)
        edges.extend([(citing[0], p[0], num)
                      for num, p in enumerate(cited, i)])
        i += len(cited)
    return nodes, edges


def generate_links_with_classification(search_results, taxonerd, nlp, linker,
        generic_dict):
    """
    Generate a list of edges by paper ID from the results of a Semantic Scholar query. Removes malformed
    citations with no paperID, and classifies nodes by the organisms in their titles.

    parameters:
        search_results, dict: query results
        taxonerd, TaxoNERD instance: model to use for classification
        nlp, spacy NLP object: model to use to make doc for linking
        linker, taxonerd EntityLinker instance: linker to use to get IDs
        generic_dict, dict: keys are generic terms for kingdoms, values are
            kingdoms

    returns:
        nodes, list of two-tuple: the paper ID and an attribute dictionary containing the paper's title
        edges, list of three-tuple: the paper IDs of both citing and cited paper, and an attribute dictionary with the paper's title
    """
    # Make dict of unique papers for classification
    to_classify = {}
    for paper in search_results:
        if (paper['paperId'] not in to_classify.keys()) and (paper['paperId']
                                                             is not None):
            to_classify[paper['paperId']] = {
                'title': paper['title'],
                'abstract': paper['abstract']
            }
        for ref in paper['references']:
            if (ref['paperId'] not in to_classify.keys()) and (ref['paperId']
                                                               is not None):
                try:
                    to_classify[ref['paperId']] = {
                        'title': ref['title'],
                        'abstract': ref['abstract']
                    }
                except KeyError:
                    to_classify[ref['paperId']] = {
                        'title': ref['title'],
                        'abstract': None
                    }

    print(f'There are {len(to_classify)} unique papers to classify.')

    # Identify entites
    paper_spec_names = {}
    start = time.time()
    for paperId, data in tqdm(to_classify.items()):
        species_names = get_species_names(data['title'], data['abstract'],
                                          taxonerd)
        paper_spec_names[paperId] = species_names
    print(f'Time to get entities from all papers: {time.time() - start: .2f}')

    # Map entities to classifications
    start = time.time()
    species_dict = get_species_classes(paper_spec_names, nlp, linker)
    classified = map_paper_species(paper_spec_names, species_dict,
            generic_dict, to_classify)
    print(
        f'Time to get the classification of entities from all papers: {time.time() - start: .2f}'
    )

    # Map the classifications back to original data structure
    nodes, edges = [], []
    i = 0
    for paper in tqdm(search_results):
        org = classified[paper['paperId']]
        citing = (paper['paperId'], {
            'title': paper['title'],
            'study_system': org
        })
        cited = [(p['paperId'], {
            'title': p['title'],
            'study_system': classified[p['paperId']]
        }) for p in paper['references'] if p['paperId'] is not None]
        nodes.append(citing)
        nodes.extend(cited)
        edges.extend([(citing[0], p[0], num)
                      for num, p in enumerate(cited, i)])
        i += len(cited)
    return nodes, edges


def main(search_result_path, graph_save_path, generic_dict, prefer_gpu, skip_classification):

    # Read in search results
    print('\nLoading citation data...')
    with open(search_result_path) as myf:
        search_results = json.load(myf)

    # Define TaxoNERD model for classification
    if not skip_classification:
        print('\nLoading TaxoNERD model...')
        start = time.time()
        taxonerd = TaxoNERD(prefer_gpu=prefer_gpu)
        nlp = taxonerd.load(model="en_core_eco_biobert")
        print(f'Time to load model: {time.time() - start: .2f}')
        print('\nLoading entity linker...')
        start = time.time()
        linker = EntityLinker(linker_name='ncbi_taxonomy',
                              resolve_abbreviations=False)
        print(f'Time to load linker: {time.time() - start: .2f}')

    # Get graph nodes and edges
    print('\nFormatting and classifying nodes and edges...')
    if skip_classification:
        nodes, edges = generate_links_without_classification(search_results)
    else:
        nodes, edges = generate_links_with_classification(
            search_results, taxonerd, nlp, linker, generic_dict)

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
    parser.add_argument('-generic_dict', type=str, default='',
                        help='Path to dictionary mapping general terms to '
                        'life kingdoms, to be used for fuzzy mapping')
    parser.add_argument('--prefer_gpu',
                        action='store_true',
                        help='Whether or not GPU is available to use')
    parser.add_argument('--skip_classification',
                        action='store_true',
                        help='Build the graph without node classification')

    args = parser.parse_args()

    args.search_result_path = abspath(args.search_result_path)
    args.graph_save_path = abspath(args.graph_save_path)
    if args.generic_dict != '':
        args.generic_dict = abspath(args.generic_dict)
        with open(args.generic_dict) as myf:
            generic_dict = json.load(myf)

    main(args.search_result_path, args.graph_save_path, generic_dict,
            args.prefer_gpu, args.skip_classification)
