"""
This function computes the differential abundance score of functions or taxa
"""
# to comply with both Py2 and Py3
from __future__ import absolute_import, division, print_function

# general imports
import argparse
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import sys
import os.path


def main(args):

    # some default args for testing
    # args = {'input_file': "/Volumes/ohadm/OhadM/MUSiCC/Data/KO2Sample_T2D.tab",
    #         'output_file': "out.tab", 'class_file': "/Volumes/ohadm/OhadM/MUSiCC/Data/Sample2Class_T2D.tab",
    #         'method': "Wilcoxon", 'row_metadata': "/Volumes/ohadm/OhadM/MUSiCC/Matrices/KOvsNAME_KEGG_2013_07_15.lst",
    #         'verbose': True}

    # if verbose, print given options
    if 'verbose' in args.keys() and args['verbose']:
        print("Given parameters: ", args)

    # set some initial settings for the script
    np.set_printoptions(precision=5, suppress=False, linewidth=200)  # nicer output

    if 'verbose' in args.keys() and args['verbose']:
        print("Loading files... ", end="", flush=True)

    # read the input abundance from a file
    if 'input_file' in args.keys():
        if not os.path.isfile(args['input_file']):
            sys.exit('Error: Input file "' + args['input_file'] + '" does not exist')
        abundance_data = pd.read_table(args['input_file'], index_col=0)
    # read the input abundance from a panda data frame
    elif 'input_pd' in args.keys():
        abundance_data = args['input_pd']
    else:
        sys.exit('Error: No input abundance given to script')

    # change rows with NaNs as IDs to a string ID
    non_nan_id = np.array(abundance_data.index)
    for i in range(abundance_data.index.shape[0]):
        if not isinstance(non_nan_id[i], str) and not isinstance(non_nan_id[i], np.int_):
            print("Fixing row ID for: " + str(non_nan_id[i]))
            non_nan_id[i] = "NaN_" + str(i)

    abundance_data.index = non_nan_id

    # read the metadata if given
    if 'row_metadata' in args.keys() and args['row_metadata'] is not None:
        if not os.path.isfile(args['row_metadata']):
            sys.exit('Error: Metadata file does not exist')
        metadata = pd.read_table(args['row_metadata'], index_col=0, header=None)
        metadata.columns = ['Metadata']
        metadata.index.name = 'KO'
    else:
        metadata = pd.DataFrame(data=abundance_data.index.values, index=abundance_data.index, columns=['Metadata'])

    # read the class file
    if 'class_file' in args.keys():
        if not os.path.isfile(args['class_file']):
            sys.exit('Error: Class file does not exist')
        if args['class_header']:
            class_data = pd.read_table(args['class_file'], index_col=0, dtype=str)
        else:
            class_data = pd.read_table(args['class_file'], index_col=0, header=None, dtype=str)
        class_data.columns = ['Class']
        class_data.index.name = 'Sample'

    elif 'class_pd' in args.keys():
        class_data = args['class_pd']

    else:
        sys.exit('Error: No class file given (-c)')

    # intersect the class file with the abundance file and create new
    # data frames that hold only the shared samples
    # sort both sample lists
    cols_abundances = [col for col in abundance_data.columns if col in class_data.index]
    cols_abundances.sort()
    rows_class = [row for row in class_data.index if row in abundance_data.columns]
    rows_class.sort()
    abundance_data = abundance_data[cols_abundances]
    class_data = class_data.loc[rows_class]

    number_of_samples = abundance_data.shape[1]
    number_of_kos = abundance_data.shape[0]

    pvals = np.zeros(number_of_kos)
    signLogP = np.zeros(number_of_kos)
    mean_cases = np.zeros(number_of_kos)
    mean_controls = np.zeros(number_of_kos)
    stat_value = np.zeros(number_of_kos)

    # define controls and cases
    controls = (class_data.values.reshape(number_of_samples) == args['control_label'])
    cases = (class_data.values.reshape(number_of_samples) == args['case_label'])

    if 'verbose' in args.keys() and args['verbose']:
        print("Done.", flush=True)
        print("Number of samples: " + str(number_of_samples), flush=True)
        print("Number of controls: " + str(sum(controls)), flush=True)
        print("Number of cases: " + str(sum(cases)), flush=True)
        print("Number of functions: " + str(number_of_kos), flush=True)
        print("Computing differential abundance... ", end="", flush=True)

    for i in range(number_of_kos):

        mean_cases[i] = np.mean(abundance_data.values[i, cases])
        mean_controls[i] = np.mean(abundance_data.values[i, controls])

        if args['method'] == "Wilcoxon" or args['method'] == "wilcoxon":
            (z, p) = stats.ranksums(abundance_data.values[i, cases], abundance_data.values[i, controls])
            stat_value[i] = z
            pvals[i] = p
            signLogP[i] = -1 * np.log10(p) * np.sign(z)

        if args['method'] == "Ttest" or args['method'] == "ttest":
            #print("cases: " + str(abundance_data.values[i, cases]))
            #print("controls: " + str(abundance_data.values[i, controls]))
            #print("cases mean/std = " + str(np.mean(abundance_data.values[i, cases])) + "/" + str(np.std(abundance_data.values[i, cases])))
            #print("controls mean/std = " + str(np.mean(abundance_data.values[i, controls])) + "/" + str(np.std(abundance_data.values[i, controls])))
            (t, p) = stats.ttest_ind(abundance_data.values[i, cases], abundance_data.values[i, controls])
            stat_value[i] = t
            pvals[i] = p
            signLogP[i] = -1 * np.log10(p) * np.sign(t)

    # write output to file
    if 'verbose' in args.keys() and args['verbose']:
        print("Done.", flush=True)
        print("Writing output... ", end="", flush=True)

    #print(pvals)
    bonferroni, _, _, _ = multipletests(pvals, alpha=0.05, method="bonferroni")
    fdr_1, _, _, _ = multipletests(pvals, alpha=0.01, method="fdr_bh")
    fdr_5, _, _, _ = multipletests(pvals, alpha=0.05, method="fdr_bh")
    fdr_10, _, _, _ = multipletests(pvals, alpha=0.1, method="fdr_bh")

    # create output data frame
    output_df = pd.DataFrame(data=np.vstack((mean_cases, mean_controls, stat_value, pvals, signLogP, bonferroni, fdr_1, fdr_5, fdr_10)).transpose(),
                             index=abundance_data.index,
                             columns=np.array(("meanCases","meanControls", "StatValue", "pval", "singLogP", "Bonf", "FDR-0.01", "FDR-0.05", "FDR-0.1")))

    # join with metadata
    output_df = output_df.join(metadata)
    output_df.index.name = 'Function'

    # write to output file
    if 'output_file' in args.keys():
        output_df.to_csv(args['output_file'], sep='\t', na_rep='None')
    elif 'output_pd' in args.keys():
        args['output_pd'] = output_df
    else:
        sys.exit('Error: No output destination given')

    if 'verbose' in args.keys() and args['verbose']:
        print("Done.", flush=True)

################################################################################################################

if __name__ == "__main__":
    # get options from user
    parser = argparse.ArgumentParser(description='Compute Differential Abundance')
    parser.add_argument('input_file', help='Input abundance file to compute differential abundance')
    parser.add_argument('-c', '--class', dest='class_file', help='Class assignment file for the two different compared classes', default=None)
    parser.add_argument('-ch', '--class_header', dest='class_header', help='Flag indicating whether class file contains a column header (default: false)', action='store_true')
    parser.add_argument('-rmeta', '--row_metadata', dest='row_metadata', help='Metadata to add to each row (Default: add row ID as metadata)', default=None)
    #parser.add_argument('-sa', '--sec_abundance', dest='second_abun_file', help='Secondary abundance file to use with the input', default=None)
    parser.add_argument('-o', '--out', dest='output_file', help='Output destination for differential abundance scores (default: DA.tab)', default='DA.tab')
    parser.add_argument('-m', '--method', dest='method', help='Method to compute differential abundance (default: Wilcoxon)', default='Wilcoxon')
    parser.add_argument('-control_label', dest='control_label', help='Define control label (default: 0)', default='0')
    parser.add_argument('-case_label', dest='case_label', help='Define control label (default: 1)', default='1')

    #parser.add_argument('-hf', '--higher_file', dest='higher_file', help='optional input, a tab-delimited file converting the KOs to a higher network level (say pathways). Each row has the KO ID followed by binary (0/1) values of whether this KO belongs to the higher level. Column headers are "KO" followed by all the higher level IDs', default=None)
    #parser.add_argument('-hm', '--higher_method', dest='higher_method', help='Method to convert KO values to higher values (default: Sum)', default='Sum')
    #parser.add_argument('-if', '--input_format', dest='input_format', choices=['tab', 'csv'], help='Option indicating the format of the input file (default: tab)', default='tab')
    #parser.add_argument('-of', '--output_format', dest='output_format', choices=['tab', 'csv'], help='Option indicating the format of the output file (default: tab)', default='tab')
    parser.add_argument('-v', '--verbose', dest='verbose', help='Increase verbosity of module (default: false)', action='store_true')
    given_args = parser.parse_args()

    main(vars(given_args))

