#sys.argv[1] should be the path of the roster file specifying the input files
#sys.argv[2] should be the modality
#sys.argv[3] should be the output file
#sys.argv[4] should be the verbose argument

import cPickle
from sgRNA_learning import *
import pandas as pd


def predictWeissmanScore(tssTable, p1p2Table, sgrnaTable, libraryTable, pickleFile, fastaFile, chromatinFiles, modality, verbose):
   
    # open pickle file to continue from previously trained session/model
    try:
        with open(pickleFile) as infile:
            fitTable, estimators, scaler, reg, transformedParams_train_header = cPickle.load(infile)
    except:
        raise Exception('Trained model file not found.') 

    # set indices for pd dataframes
    tssTable = tssTable.set_index(['gene', 'transcripts'])
    p1p2Table = p1p2Table.set_index(['gene', 'transcript'])
    sgrnaTable = sgrnaTable.set_index('sgId')
    libraryTable = libraryTable.set_index('sgId')

    paramTable = getParamTable(tssTable, p1p2Table, sgrnaTable, libraryTable, fastaFile, chromatinFiles, verbose)
    
    transformedParams_new = getTransformedParams(paramTable, fitTable, estimators, verbose)

    printNow('\nPredicting scores...', verbose)
    try:
        predictedScores = pd.Series(reg.predict(scaler.transform(transformedParams_new.loc[:, transformedParams_train_header.columns].fillna(0).values)), index=transformedParams_new.index)
    except:
        raise Exception('Error getting predictions: Environment may be corrupted. Please try reinstalling package.')

    return predictedScores

def getParamTable(tssTable, p1p2Table, sgrnaTable, libraryTable, fastaFile, chromatinFiles, verbose):
    
    try:
        genomeDict=loadGenomeAsDict(fastaFile, verbose)
    except:
        raise Exception('Cannot open genome FASTA file: File is corrupted or does not exist.')

    printNow('\nLoading chromatin data...', verbose)

    try:
        bwhandleDict = {'dnase':BigWigFile(open(chromatinFiles[0])), 'faire':BigWigFile(open(chromatinFiles[1])), 'mnase':BigWigFile(open(chromatinFiles[2]))}
    except:
        raise Exception('Error opening chromatin files: Error in files or files do not exist.')

    # parse primary TSS and secondary TSS
    p1p2Table['primary TSS'] = p1p2Table['primary TSS'].apply(lambda tupString: (int(tupString.strip('()').split(', ')[0].split('.')[0]), int(tupString.strip('()').split(', ')[1].split('.')[0])))
    p1p2Table['secondary TSS'] = p1p2Table['secondary TSS'].apply(lambda tupString: (int(tupString.strip('()').split(', ')[0].split('.')[0]),int(tupString.strip('()').split(', ')[1].split('.')[0])))

    printNow('\nCalculating parameters...', verbose)

    try:
       paramTable = generateTypicalParamTable(libraryTable, sgrnaTable, tssTable, p1p2Table, genomeDict, bwhandleDict, verbose)
    except:
       raise Exception('Error generating parameter table.')
     
    return paramTable


def getTransformedParams(paramTable, fitTable, estimators, verbose):
    
    printNow('\nTransforming parameters...', verbose)

    try:
        transformedParams_new = transformParams(paramTable, fitTable, estimators)
    except:
        raise Exception('Error transforming parameters.')

    # reconcile differences in column headers
    colTups = []
    for (l1, l2), col in transformedParams_new.iteritems():
        colTups.append((l1,str(l2)))
    transformedParams_new.columns = pd.MultiIndex.from_tuples(colTups)

    return transformedParams_new



# Ready to load the data from R
roster_file = sys.argv[1]
modality = sys.argv[2]
output_file = sys.argv[3]
verbose = sys.argv[4]

roster = pd.read_csv(roster_file, sep='\t', header=0)
roster = dict(zip(roster.object, roster.path))
tssTable = pd.read_csv(roster["tssTable"],sep='\t', header=0)
p1p2Table = pd.read_csv(roster["p1p2Table"],sep='\t', header=0)
sgrnaTable = pd.read_csv(roster["sgrnaTable"],sep='\t', header=0)
libraryTable = pd.read_csv(roster["libraryTable"],sep='\t', header=0)
pickleFile = roster["pickleFile"]
fastaFile = roster["fasta"]

keys = ["dnase", "faire", "mnase"]
chromatinFiles = [roster.get(key) for key in keys]



scores = predictWeissmanScore(tssTable, p1p2Table, sgrnaTable, libraryTable, pickleFile, fastaFile, chromatinFiles, modality, verbose)
np.savetxt(output_file, scores)

