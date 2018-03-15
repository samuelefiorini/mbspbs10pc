#!/bin/bash
# Run main scripts

# --- Assign labels --- #
clear; python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2009
python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2010
python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2011
python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2012
python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2013
python scripts/labels_assignment.py -r ../../data -o tmp/dump -m -nj 32 -t 2014

# --- Extract raw data --- #
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2009_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2009_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2009_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2010_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2010_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2010_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2011_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2011_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2011_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2012_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2012_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2012_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2013_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2013_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2013_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2014_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2014_METAFTER_class_1.csv -nj 8
clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_2014_METONLY_class_1.csv -nj 8

clear; python scripts/extract_sequences.py -sic -r ../../data -ep -s tmp/dump_class_0.csv -nj 8 # Negative examples

# --- Prepare data for matching with CEM --- #
clear; python scripts/matching_step1.py -s tmp -o tmp/metformin

# --- Match with CEM --- #
clear; Rscript scripts/matching_step2.R
