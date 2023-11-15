"""
Classifies nodes ina citation network by study organism.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
from os import listdir
import json
import jsonlines
from tqdm import tqdm
from taxonerd import TaxoNERD
from taxonerd.linking.linking import EntityLinker
import taxoniq
from spacy.tokens import Span
from collections import Counter
import networkx as nx
import time
import regex
from math import ceil


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
        sub_len = len(term) // 3
        spacejoined = "\s+".join(term.split())
        reg = fr'\b({spacejoined}){{e<={sub_len}}}\b'

        # Search in paper
        matches = regex.search(reg, text, flags=regex.IGNORECASE)

        # Map to classes
        if matches is not None:
            classes.append(king)

    return classes


def map_paper_species(paper_spec_names, species_dict, generic_dict,
                      to_classify):
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
    for paperId, spec_names in tqdm(paper_spec_names.items()):
        classes = []
        # Try either generic terms
        if (len(spec_names) == 0) and (generic_dict != ''):
            classes = fuzzy_match_kingdoms(to_classify[paperId], generic_dict)
            if len(classes) != 0:
                additional_papers_identified += 1
        for i, spec in enumerate(spec_names):
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
            classes = fuzzy_match_kingdoms(to_classify[paperId], generic_dict)
            if len(classes) == 1:
                king = classes[0]
            elif len(classes) > 1:
                king = Counter(classes).most_common(1)[0][0]
            else:
                # If there's no classification, return NOCLASS
                king = 'NOCLASS'
                print(
                    f'\nSpec names for paper without classification: {spec_names}')
        classified[paperId] = king

    return classified


def map_specs_to_kings(species_ids):
    """
    Maps species names to kingdom classifications.

    parameters:
        species_ids, dict: keys are species names, values are NCBI IDs

    returns:
        species_dict, dict: keys are species names, values are kingdoms
    """
    species_dict = {}
    defs = {
        'Metazoa': 'Animal',
        'Viridiplantae': 'Plant',  # Consider adding algae
        'Bacteria': 'Microbe',
        'Archea': 'Microbe',
        'Fungi': 'Fungi'
    }
    not_tracked_lineage = 0
    no_sub_eukaryota_lineage = 0
    not_found_in_taxonomy = 0
    empty_lineage = 0
    for spec_ent, ncbi_id in tqdm(species_ids.items()):
        try:
            t1 = taxoniq.Taxon(ncbi_id)
            lineage = [t.scientific_name for t in t1.ranked_lineage]
            if lineage[-1] == 'Bacteria' or lineage[-1] == 'Archea':
                king = defs[lineage[-1]]
            elif lineage[-1] == 'Eukaryota':
                try:
                    king = defs[lineage[-2]]
                    if king == 'Opisthokonta':
                        king = defs[lineage[-3]]
                except KeyError:
                    not_tracked_lineage += 1
                    continue
                except IndexError:
                    no_sub_eukaryota_lineage += 1
                    continue
        except KeyError:
            not_found_in_taxonomy += 1
            continue
        except IndexError:
            empty_lineage += 1
        species_dict[spec_ent] = king

    print(f'When building the species --> kingdom dict, {not_tracked_lineage} '
            'species were dropped because their kingdom wasn\'t in our list '
            f'of interest, {no_sub_eukaryota_lineage} were dropped because '
            'they were only identifyable as Eukaryota, and '
            f'{not_found_in_taxonomy} because they did not appear in '
            'taxoniq\'s local version of NCBI Taxonomy. This could mean they '
            'are not in the actual taxonomy, or that they were added after '
            'taxoniq last updated its database version. Finally, '
            f'{empty_lineage} species were dropped because their lineage in '
            'the taxonomy entry was empty.')

    return species_dict


def link_taxoniq(uniq_names, docs, species_ids):
    """
    Use taxoniq directly to attempt to link species names not linked by
    TaxoNERD.

    parameters:
        uniq_names, list of str: unique species names
        docs, list of spacy Doc object: docs with linked entities
        species_ids, dict: keys are species, values are NCBI ID's

    returns:
        species_ids, dict: updated species IDs with futher identified species
    """
    all_doc_ents = [ent.text for doc in docs for ent in doc.ents]
    missed = [
        s for s in uniq_names
        if uniq_names not in all_doc_ents
    ]
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


def make_ent_docs(uniq_names, nlp):
    """
    Make entities into dummy docs for linking. If there are more than 1 million
    characters worth of entities, breaks up into multiple docs to get around
    spacy's character limit.

    parameters:
        uniq_names, list of str: unique entities to link
        nlp, spacy NLP object: model to use to build doc

    returns:
        docs, list of spacy Doc object: docs with entities set as doc.ents
    """
    # Get the number of docs that we need to make
    if len(' '.join(uniq_names)) < 10000:
        num_docs = 1
    else:
        num_docs = ceil(len(' '.join(uniq_names))/10000)

    # Make docs
    docs = []
    last_idx = 0 # To break up entities for docs
    single_tok_times = []
    for _ in range(num_docs):
        char_num = 0 # So we can break when we get to too long
        names_to_keep = [] # For making the doc later
        span_idxs = [] # For keeping track of spans
        prev_last = 0
        for i, ent in enumerate(uniq_names[last_idx:]):
            # We can't naively assume what spacy's tokenization wil be;
            # splitting on spaces causes errors if spacy's tokenization is
            # different. Therefore, we need to check how many tokens are in
            # spacy's tokenization for each word
            if char_num + len(ent) >= 10000:
                last_idx += i
                break
            start = prev_last
            single_tok_start_time = time.time()
            num_toks = len(nlp(ent, disable=['tagger', 'attribute_ruler',
                'lemmatizer', 'parser', 'ner']))
            single_tok_times.append(time.time() - single_tok_start_time)
            end = start + num_toks
            prev_last += num_toks
            span_idxs.append((start, end))
            names_to_keep.append(ent)
            char_num += len(ent) + 1 # To account for trailing space
        single_doc_start_time = time.time()
        doc = nlp(' '.join(names_to_keep))
        toks = "\n".join([t.text for t in doc])
        spans = [Span(doc, e[0], e[1], "ENTITY") for e in span_idxs]
        doc.set_ents(spans)
        print(f'It took {time.time() - single_doc_start_time:.2f} seconds to '
                f'tokenize and add ents to doc number {_}')
        docs.append(doc)
    print('On average, it took '
        f'{sum(single_tok_times)/len(single_tok_times):.2f} seconds to '
        'tokenize each entity')

    return docs


def get_species_classes(paper_spec_names, nlp, linker, intermediate_save_path,
                        use_intermed):
    """
    Get organism classifications from a list of NCBI Taxonomy IDs

    parameters:
        paper_spec_names, dict: keys are paperId's, values are lists of
            species names for the paper
        nlp, spacy NLP object: model to use to make doc for linking
        linker, taxonerd EntityLinker instance: linker to use to get IDs
        intermediate_save_path, str: path to directory to save intermediate
            results
        use_intermed, bool: whether or not to read intermediate files out of
            the intermediate save path

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
    docs = make_ent_docs(uniq_names, nlp)

    # Perform linking
    if use_intermed and ('species_ids.json' in
            listdir(intermediate_save_path)):
        species_id_save_name = f'{intermediate_save_path}/species_ids.json'
        with open(species_id_save_name) as myf:
            species_ids = json.load(myf)
        print(f'Read in species NCBI IDs from {species_id_save_name}')
    else:
        print('Performing TaxoNERD entity linking...')
        species_ids = {}
        print(f'There are {len(docs)} spacy documents to link.')
        for i, doc in enumerate(docs):
            start = time.time()
            doc = linker(doc)
            print(f'Time to apply linker on doc {i}: {time.time() - start: .2f}')
            for ent in doc.ents:
                ent_id = ent._.kb_ents[0][0].split(':')[1]
                print('ent id for species ', ent, ': ', ent_id)
                species_ids[ent.text] = ent_id
         # Use taxoniq to try and fill in some unlinked species
        print(f'Using taxoniq to attempt to link the missed entities...')
        species_ids = link_taxoniq(uniq_names, docs, species_ids)
        if intermediate_save_path != '':
            species_id_save_name = f'{intermediate_save_path}/species_ids.json'
            with open(species_id_save_name, 'w') as myf:
                json.dump(species_ids, myf)
            print(f'Saved species id dictionary as {species_id_save_name}')
   

    # Map to kingdoms
    print('Mapping to kingdom classifications...')
    species_dict = map_specs_to_kings(species_ids)

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


def get_unique_papers(search_results):
    """
    Get unique papers to classify.

    parameters:
        search_results, list of dict: search results to parse

    returns:
        to_classify, dict: keys are paperIds, values are dict with title and
            abstract
    """
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
    return to_classify


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
                                       intermediate_save_path, use_intermed, generic_dict):
    """
    Generate a list of edges by paper ID from the results of a Semantic Scholar query. Removes malformed
    citations with no paperID, and classifies nodes by the organisms in their titles.

    parameters:
        search_results, dict: query results
        taxonerd, TaxoNERD instance: model to use for classification
        nlp, spacy NLP object: model to use to make doc for linking
        linker, taxonerd EntityLinker instance: linker to use to get IDs
        intermediate_save_path, str: path to directory to save intermediate
            results
        use_intermed, bool: whether or not to read intermediate files out of
            the intermediate save path
        generic_dict, dict: keys are generic terms for kingdoms, values are
            kingdoms

    returns:
        nodes, list of two-tuple: the paper ID and an attribute dictionary containing the paper's title
        edges, list of three-tuple: the paper IDs of both citing and cited paper, and an attribute dictionary with the paper's title
    """
    # Make dict of unique papers for classification
    to_classify = get_unique_papers(search_results)

    # Start timer
    start = time.time()

    # Identify entites
    if use_intermed and ('paper_to_species.json' in
            listdir(intermediate_save_path)):
        paper_spec_save_name = f'{intermediate_save_path}/paper_to_species.json'
        with open(paper_spec_save_name) as myf:
            paper_spec_names = json.load(myf)
        print(f'Read in paper to species dict from {paper_spec_save_name}')
    else:
        paper_spec_names = {}
        for paperId, data in tqdm(to_classify.items()):
            species_names = get_species_names(data['title'], data['abstract'],
                                              taxonerd)
            paper_spec_names[paperId] = species_names
        print(f'Time to get entities from all papers: {time.time() - start: .2f}')
        if intermediate_save_path != '':
            paper_spec_save_name = f'{intermediate_save_path}/paper_to_species.json'
            with open(paper_spec_save_name, 'w') as myf:
                json.dump(paper_spec_names, myf)
            print(f'Saved paper --> species dict as {paper_spec_save_name}')

    # Map entities to classifications
    if use_intermed and ('species_dict.json' in
            listdir(intermediate_save_path)):
        species_dict_save_name = f'{intermediate_save_path}/species_dict.json'
        with open(species_dict_save_name) as myf:
            species_dict = json.load(myf)
        print(f'Read in species dict as {species_dict_save_name}')
    else:
        start = time.time()
        species_dict = get_species_classes(paper_spec_names, nlp, linker,
                intermediate_save_path, use_intermed)
        if intermediate_save_path != '':
            species_dict_save_name = f'{intermediate_save_path}/species_dict.json'
            with open(species_dict_save_name, 'w') as myf:
                json.dump(species_dict, myf)
            print(f'Saved species dict as {species_dict_save_name}')

    if use_intermed and ('paper_classifications.json' in
            listdir(intermediate_save_path)):
        classified_save_name = f'{intermediate_save_path}/paper_classifications.json'
        with open(classified_save_name) as myf:
            classified = json.load(myf)
        print(f'Read in paper classifications from {classified_save_name}')
    else:
        classified = map_paper_species(paper_spec_names, species_dict,
                                   generic_dict, to_classify)
        if intermediate_save_path != '':
            classified_save_name = f'{intermediate_save_path}/paper_classifications.json'
            with open(classified_save_name, 'w') as myf:
                json.dump(classified, myf)
            print(f'Saved paper classifications as {classified_save_name}')
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


def main(search_result_path, graph_save_path, intermediate_save_path,
        use_intermed, generic_dict, prefer_gpu, skip_classification):

    # Read in search results
    print('\nLoading citation data...')
    with jsonlines.open(search_result_path) as reader:
        search_results = []
        for obj in reader:
            search_results.append(obj)

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
            search_results, taxonerd, nlp, linker, intermediate_save_path,
            use_intermed, generic_dict)

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
    parser.add_argument('-intermediate_save_path', type=str, default='',
                        help='Path to directory to save intermediate results, '
                        'which can be used to re-start this script from the '
                        'middle')
    parser.add_argument('-generic_dict',
                        type=str,
                        default='',
                        help='Path to dictionary mapping general terms to '
                        'life kingdoms, to be used for fuzzy mapping')
    parser.add_argument('--prefer_gpu',
                        action='store_true',
                        help='Whether or not GPU is available to use')
    parser.add_argument('--use_intermed', action='store_true',
                        help='Use files with original names from '
                        'intermediate_save_path directory for recovery')
    parser.add_argument('--skip_classification',
                        action='store_true',
                        help='Build the graph without node classification')

    args = parser.parse_args()

    args.search_result_path = abspath(args.search_result_path)
    args.graph_save_path = abspath(args.graph_save_path)
    if args.intermediate_save_path != '':
        args.intermediate_save_path = abspath(args.intermediate_save_path)
    if args.generic_dict != '':
        args.generic_dict = abspath(args.generic_dict)
        with open(args.generic_dict) as myf:
            generic_dict = json.load(myf)

    main(args.search_result_path, args.graph_save_path,
            args.intermediate_save_path, args.use_intermed, generic_dict,
         args.prefer_gpu, args.skip_classification)
