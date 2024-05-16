# desiccation-network
Code for the project *Drying to Connect: A bibliometric analysis of desiccation tolerance research across the kingdoms of life*.

## Dependencies
From the root directory of this repo, run:
```
conda env create -f environment.yml
```
to install the conda environment.

## Pre-processing data
We've chosen to use Web of Science as our data source because we have internal access to a paywalled version of the Web of Science Core Collection (the [XML dataset](https://clarivate.libguides.com/rawdata)). Instructions in this section will focus on how to use Web of Science with our codebase. Scripts referenced in this section are found in `desiccation_network/preprocess_data`.

**NOTE:** There is code to pull abstracts with [Semantic Scholar](semanticscholar.org) (an open-source API); however, we transitioned data sources relatively early in the project, so we can't guarantee that the code still works and that its output works with the rest of the pipeline -- PR's are more than welcome if you'd like to use/improve this functionality!

### Obtaining papers of interest
The first step involves identifying the papers of interest from Web of Science. We do this by going to the Web of Science search engine ina  browser, and entering search terms of interest. Make sure that the Core Collection is specified, as all other papers will be dropped from following pre-processing steps, and it saves manual labor to exclude those in the initial search. An example of the search configuration we used:

![image](https://github.com/serenalotreck/desiccation-network/assets/41377532/333d11b4-78d8-45f2-8c7b-c044d2aee6bb)

Once you click `Search`, you will export the results with the Fast 5000 option:

![image](https://github.com/serenalotreck/desiccation-network/assets/41377532/be07aa5e-65b2-4a69-9e47-d961d8ddfbf7)

You'll need to sign in to access this option. If you want to include more than 5,000 results, you'll need to download multiple Fast 5000 files. You can then concatenate them vertically to make one large file (they are tab-delimited `.txt` files; you can use `pandas` for this), or simply run the subsequent steps multiple times (we recommend concatenating).

### Processing XML dataset
If you're affiliated with Michigan State University, feel free to contact @serenalotreck for details on dataset access; otherwise, you'll need to determine your institution's specifics for obtaining the XML dataset. Once the dataset is downloaded and unzipped (triple-layered zip structure -- overall dataset is zipped, each year is zipped, and each individual file is gzipped; this will take several hours to complete unzipping, and the dataset will consume ~500GB of disk space once complete), you'll need to run the following:

```
python process_xml_dataset.py <path/to/dataset/> dataset_map.json
```
This step creates a mapping of paper ID's to XML file names, which saves a lot of time when completing the next step for smaller datasets.

### Pulling paper metadata

Finally, we obtain the paper metadata from the XML dataset for our search results. Specifically, this step currenty pulls the following information:
* Unique ID (“UID”)
* Title
* Abstract
* Publication year
* Authors
* Author affiliations (“addresses”)
* References
* Static keywords (those derived from the journal in which the paper was published)
* Dynamic keywords (derived from a yearly clustering analysis performed by Clarviate)
* Author-defined keywords

An example command to pull metadata for a dataset whose WoS Fast 5000 search results are stored in a file called `wos_search.txt`, saving our output as `metadata_results_output.jsonl`:

```
python wos_pull_papers.py <path/to/xml/dataset/> metadata_results_output.jsonl dataset_map.json -gui_search wos_search.txt
```

Note that this process can be quite computationally intensive depending on the size of the dataset; there is a `--parallelize` option to help speed this up.

Running the code above will get the metadata for the main search results. If we want to also get abstracts for the references of those results, we can re-run the script with the following options:

```
python wos_pull_papers.py <path/to/xml/dataset/> metadata_results_with_refs_output.jsonl dataset_map.json -jsonl_to_modify metadata_results_output.jsonl
```
We did not use this option for our analyses, as we excluded any references that weren't also in the main search results; however, we've left the option here in case you'd like to include all references. Note that this will be more computationally intensive than the main results only, we definitely suggest adding the `--parallelize` option!

### Further pre-processing
All subsequent pre-processing steps are up to the user's preference, and should be performed with custom code. For example, we removed all references not in the main results, and added the abstracts from the main results to the references that remained. We also filtered the abstracts included in our results using the papers' static keywords in a heuristic classification approach; see `notebooks/WoS_dataset_filtering.ipynb`. The scripts in `desiccation_network/quality_control` were used to assist in this process, as it involved some manual labeling.

## Building citation network
Once the data have been obtained, we can build the citation network. Scripts in this section can be found in `desiccation_network/build_citation_network`.

### Building network
A citation network can be built with document classification or without. With document classification, each paper is classified as belonging to one of Plants, Animals, Microbes or Fungi, based on (a) the presence of taxonomic terms (species' common and scientific names) amd (b) fuzzy string matching with kingdom specific terms ("generic mapping"). The file `desiccation_network/build_citation_network/maps/term_map.json` contains our generic mapping terms; however, the user can modify that file to add or remove terms based on their needs.

Citation network construction with classification:
```
python classify_papers.py metadata_results_output.jsonl classified_citation_network.graphml -intermediate_save_path <path/to/save/intermediate/output> -generic_dict maps/term_map.json --prefer_gpu
```
This will generate a `.graphml` file of the citation network, with a `study_system` attribute for each node. `.graphml` files can be visualized in software such as [Gephi](https://gephi.org/) or [Cytoscape](https://cytoscape.org/); it can also be manipulated with the package `networkx` for those who prefer staying in Python. Classification is relatively computationally intensive, so we recommend using `-intermediate_save_path` in case the program crashes; to pick up where you left off, add the option `--use_intermed` on the next run. You can also provide a `.jsonl` path for the first positional argument, and specify `--return_jsonl` to get the classifications in the jsonl format of the dataset, without building the citation network.

Citation network construction without classification:
```
python classify_papers.py metadata_results_output.jsonl unclassified_citation_network.graphml --skip_classification
```

### Descriptive statistics
For classified networks, we provide a script to visualize basic statistics about the documents in the dataset with respect to the classifications:
```
python descriptive_stats.py metadata_results_output.jsonl classified_citation_network.graphml "desiccation tolerance OR anhydrobiosis" <path/to/save/graphs/> <string to prepend to output filenames>
```

### Downstream citation network analysis
There are many options for downstream analysis of the resulting citation network -- the code to generate the analysis we performed in this project can be found in `notebooks` for inspiration!

## Conference recommendation algorithm
The code in `desiccation_network/conference_recommendation` allows the prediction of new attendees for a given conference. Given the correct data pre-processing, this algorithm could be used for any conference.

The two principal scripts for conference recommendations are `get_recommendations.py`, which performs the prediction, and `describe_candidates.py`, which creates a csv file of all publications for each of the candidate authors that was used in determining potential attendees.

The required inputs to `get_recommendations.py` are:
* `jsonl_path`: the path to the jsonl-formatted dataset of papers originally drawn from the WOS XML dataset.
* `graphml_path`: the path to the classified citation network that was constructed from the file specified by `jsonl_path` using `classify_papers.py`
* `topic_model_config`: the path to a json file specifying the configurations for BERTopic component models. Two example topic model configuration files can be found in `conference_recommendation/topic_model_configs`. Explanations of the parameters can be found in the documentation for [BERTopic](https://maartengr.github.io/BERTopic/index.html).
* `attendee_path`: the path to a csv file containing the names of past conference attendees. The file must have the following columns:

| Surname | First_name | Affiliation | Country |
| -------- | ------- | -------- | ------- |

* `alt_name_path`: the path to a csv file containing alternative publishing names for conference authors, containing the following columns:

| Registration_surname | Registration_first_name | Alternative_name_1 | Alternative_name_2 | Alternative_name_3 | Maiden_name |
| -------- | ------- | -------- | ------- | -------- | ------- |

`Alternative_name_<x>`  and `Maiden_name` are all in Firstname Lastname order. An example entry for someone that occationally publishes with a middle initial would be:

| Registration_surname | Registration_first_name | Alternative_name_1 | Alternative_name_2 | Alternative_name_3 | Maiden_name |
| -------- | ------- | -------- | ------- | -------- | ------- |
| Lotreck | Serena | Serena G. Lotreck |  |  |  |

For our use case, we manually searched each author and looked for a Google Scholar or Semantic Scholar author page containing their publications, and looked through them to find potential alternative names. While this parameter is required, you can simply leave all `Alternative_name_<x>` columns blank in order to perform recommendation without consideration of alternative names.
* `-cutoff` (optional):  an integer specifying how many candidates to return. Default value is 5 candidates.
* `-enrich_threshold` (optional): an integer between 0 and 100. Used in consideration of what network clusters should be considered "enriched" in previous conference attendees by using the provided value to make a cut in the distribution of enrichment values.
* `-prod_threshold` (optional): a float between 0 and 1. Used to create a threshold based on productivity, in terms of how many publications each author has. For example, a productivity threshold of 0.4 will take the 40% most productive authors by publication number.
* `--save_clusters` (optional flag): whether or not to save the cluster information used to make attendee recommendations
* `outpath`: path to a directory to save the outputs
* `outprefix`: string to prepend to output file names.


An example of how to run this script:
  ```
  python get_recommendations.py /path/to/dataset.jsonl /path/to/classified_network.graphml topic_model_configs/mmr_topic_config.json /path/to/attendees.csv /path/to/alt_names.csv /output/path/ output_prefix -cutoff 10 -prod_threshold 0.03 -enrich_threshold 50 --save_clusters
  ```

Once you've run `get_recommendations.py`, you can pass the output to `describe_candidates.py` like this. If you've provided the output prefix of "my_recs" with a `cutoff` value of 10, the relevant output file would be called `my_recs_top_10_candidates.txt`:

```
python describe_candidates.py my_recs_top_10_candidates.txt /path/to/dataset.jsonl /output/path/ output_prefix
```
This will return a CSV with the articles from the dataset pertaining to each candidate, with the following columns:

| publication_title | publication_abstract | publication_year | candidate | affiliation_at_pub|
| -------- | ------- | -------- | ------- | -------- |

