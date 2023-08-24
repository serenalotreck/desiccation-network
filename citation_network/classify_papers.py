"""
Classifies nodes ina citation network by study organism.

Author: Serena G. Lotreck
"""
import argparse
from os.path import abspath
from tqdm import tqdm
from taxonerd import TaxoNERD
import taxoniq
import pickle


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


def get_kingdom(title, abstract, taxonerd):
    """
    Uses TaxoNERD to get ID's from title and abstract, gets kingdoms and
    compares to get the final kingdom classification for the article.

    parameters:
        title, str: title of the article
        abstract, str: abstract of the article
        taxonerd, TaxoNERD instance: TaxoNERD model

    returns:
        king, str: kingdom for the study organism of the paper
    """
    # Do TaxoNERD classification
    title_df = taxonerd.find_in_text(title)
    abstract_df = taxonerd.find_in_text(abstract)

    # Get the unique organisms
    title_ents = list(set([title_df['entity'][j][0][0].split("NCBI:")[1] for j in
            range(len(title_df))]))
    abstract_ents = list(set([abstract_df['entity'][j][0][0].split("NCBI:")[1] for j in
            range(len(abstract_df))]))

    # Set up definitions for kingdom classification
    defs = {
            'Metazoa': 'Animal',
            'Viridiplantae': 'Plant', # Consider adding algae
            'Bacteria': 'Microbe',
            'Archea': 'Microbe'
            }

    # Classify unique organisms
    title_classes = classify_orgs(title_ents, defs)
    abstract_classes = classify_orgs(abstract_ents, defs)

    # Compare title and abstract
    if (len(title_classes) == len(abstract_classes) == 1) and (title_classes ==
            abstract_classes):
        king = title_classes[0]
        return king
    elif len(title_classes) == 0 and len(abstract_classes) == 1:
        return abstract_classes[0]
    elif len(abstract_classes) == 0 and len(title_classes) == 1:
        return title_classes[0]
    else:
        # For now, come back to this
        return None


def classify_paper(paper, taxonerd):
    """
    Get the study organism kingdom from a paper.

    parameters:
        paper, tethne.classes.paper.Paper object: paper to check
        taxonerd, TaxoNERD instance: TaxoNERD model

    returns:
        king, str: 'Animal', 'Plant' or 'Microbe' if paper contains at least
        one of title or abstract, otherwise returns None
    """
    # Get title
    try:
        title = paper['title']
    except AttributeError:
        title = ''

    # Get abstract
    try:
        abstract = paper['abstract']
    except AttributeError:
        abstract = ''

    # Get the kingdom
    king = get_kingdom(title, abstract, taxonerd)

    return king


def classify_nodes(papers, taxonerd, out_loc, out_prefix):
    """
    Find the kingdom (plant, animal, microbe) of the study organism of each
    paper. Follows this general algorithm:

        1. Use taxoNERD to extract species names from title and abstract
        2. Use NCBITaxon to classify each species name into a kingdom
        3. If there are classifications in both the title and the abstract,
        compare the kingdoms extracted from title and abstract:
            a. If they're the same (expected), this is the study organism
            kingdom
            b. If they're different, use the kingdom in the title
        4. If there's no classification in the abstract or title but there is
        in the other:
            a. If there's only one kingdom classification, use it as the study
            organism
        5. Catch all instances that fall through this algorithm without being
        classified and save to a file

    paramters:
        papers, tethne.classes.Corpus object: papers to classify
        taxonerd, TaxoNERD instance: TaxoNERD model
        out_loc, str: directory to save output
        out_prefix, str: string to prepend to output files

    returns:
        TODO decide what output format is best
    """
    dropped_papers = []
    keep_papers = []
    paper_kings = {}
    for paper in tqdm(papers):

        # Get kingdom
        king = classify_paper(paper, taxonerd)

        if king is None:
            # Save to dropped outputs
            dropped_papers.append(paper)
        else:
            try:
                # Save the taxonomic classification
                if isinstance(paper.doi, str):
                    paper_kings[paper.doi] = king
                    # Save kept papers
                    keep_papers.append(paper)
                else:
                    dropped_papers.append(paper)
            except AttributeError:
                # Drop if it doesn't have a DOI
                dropped_papers.append(paper)

    # Make and save new corpus of dropped papers
    drop_corpus = Corpus(dropped_papers)
    drop_save = f'{out_loc}/{out_prefix}_classification_dropped_documents.pickle'
    with open(drop_save, 'w') as myf:
        pickle.dump(drop_corpus, myf)
    #_ = drop_corpus.to_hdf5(datapath=drop_save)
    verboseprint('Papers that could not be classified by study organism have '
                f'been saved to {drop_save}. {len(dropped_papers)} were dropped.')

    # Generate a summary of classification
    counts = Counter(paper_kings.values())
    verboseprint('A summary of the identified classes:')
    verboseprint(counts)

    # Make new corpus with kept papers and add taxonomic class as feature
    keep_corpus = Corpus(keep_papers, index_by='doi')
    keep_corpus.add_features('kingdom_class', paper_kings)
    keep_save = f'{out_loc}/{out_prefix}_classification_kept_documents.pickle'
    with open(keep_save, 'w') as myf:
        pickle.dump(keep_corpus, myf)
    #_ = keep_corpus.to_hdf5(datapath=keep_save)
    verboseprint('Papers with successfull study organism classification have '
            f'been saved to {keep_save}. {len(keep_papers)} were kept.')
    return keep_corpus


def main(wos_file, out_loc, out_prefix):

    # Read in the WOS file
    verboseprint('\nReading in WOS output...')
    papers = wos.read(wos_file)

    # Classify the nodes by study system
    verboseprint('\nLoading TaxoNERD model...')
    taxonerd = TaxoNERD(prefer_gpu=False)
    nlp = taxonerd.load(model="en_core_eco_biobert", linker="ncbi_taxonomy", threshold=0.7)
    verboseprint('\nClassifying papers by study organism...')
    classed_papers = classify_nodes(papers, taxonerd, out_loc, out_prefix)

    # Build the network
    verboseprint('\nBuilding citation network...')
    graph = direct_citation(classed_papers)

    # Output in file renderable by cytoscape
    verboseprint('\nSaving citation network...')
    out_file = f'{out_loc}/{out_prefix}_citation_network.graphml'
    to_graphml(graph, out_file)

    verboseprint('\nDone!\n')

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Build citation network')

    parser.add_argument('wos_file', type=str,
            help='Path to Web of Science Full Citation output')
    parser.add_argument('out_loc', type=str,
            help='Path to directory to save output')
    parser.add_argument('out_prefix', type=str,
            help='String to prepend to output file name')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Whether or not to print updates')

    args = parser.parse_args()

    args.wos_file = abspath(args.wos_file)
    args.out_loc = abspath(args.out_loc)

    verboseprint = print if args.verbose else lambda *a, **k: None

    main(args.wos_file, args.out_loc, args.out_prefix)
