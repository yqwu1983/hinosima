#################################################################################################################
# snk.canupipe.py                                                                                               #
#                                                                                                               #
## Script to correct pacbio (long) reads using illumina (short) reads.                                          #
# 1. Correct pacbio reads using colormap (or proovread) and illumina reads.                                     #
# 2. Assembly pacbio reads using canu                                                                           #
# (optional, compare assemblies using quast)                                                                    #
# (optional, compare corrected reads using a reference(blasr, samtools-cigar, count-deletions/insertions)       #
#    (tmp/blasr_output/countID.py)                                                                              #
#                                                                                                               #
## Requirements:                                                                                                #
# - pacbio fasta files uncorrected.                                                                             #
# - illumina fasta file.                                                                                        #
# - (optional reference, in case to choose to do comparison step)                                               #
#                                                                                                               #
## Example run:                                                                                                 #
# $ module load python/3.5.0                                                                                    #
# (dry run) $  snakemake -j 60 --snakefile snk_canupipe.py --cluster "sbatch --partition=compute                #
#                              --cpus-per-task=8 --time=14-0 --job-name=snkmk --mem=20GB"                       # 
#                              --config pfasta=pacbio.fasta ifasta=illumina.fastq fix=colormap -np              #
#                                                                                                               #
#                                                                                                               #
#################################################################################################################

import subprocess, sys, os, glob 
from os.path import join
from os.path import basename

# Input parameters  ------------------------------------------------------------------------
#

#PACBIO fasta file
PFASTA = config["pfasta"]

#ILLUMINA fastq file
IFASTA =  config["ifasta"]

#Correction software
fixalth = config["fix"]

#split correction step
numJobs=101
threadsCorrection=8

#software location
colormap="/apps/unit/MikheyevU/miquel/colormap/runCorr.sh"
proovread="/apps/unit/MikheyevU/miquel/proovread/bin/proovread"
canu_dir="/apps/unit/MikheyevU/miquel/canu-1.3/Linux-amd64/bin/"

# Regular expression matching the FASTA files.
SAMPLES, = glob_wildcards(join(PFASTA, '{sample,[^/]+}.fasta'))

# Patterns using the sample wildcard
PATTERN = '{sample}.fasta'

SUBSAM=[]
prefix=basename(PFASTA).split(".")[0]
for i in range(0,numJobs):
    SUBSAM.append(prefix+"."+str(i).zfill(3))

# Rules ------------------------------------------------------------------------
#

rule all:
    input:
        #Only split&correction&merge
        prefix+'_corrected.fasta'
        #+Assembly
        #prefix+'_assembly/res.contigs.fasta'

rule splitFASTA:
	input:
		PFASTA
	output:
		trimmed=expand(prefix+'_trim/{sample}.fasta', sample=SUBSAM),
		datab=prefix+'_trim/'
	shell:"""
	    pyfasta split -n {numJobs} {input} && mv *.[0-9]*.fasta {output.datab}
    """

FASTA_DIR2 = prefix+'_trim/'
PATTERN2 = '{sample2}.fasta'

rule correction:
    input:
        fastas=join(FASTA_DIR2, PATTERN2),
        datab=FASTA_DIR2,
        illumina=IFASTA
    output:
        files=prefix+'_corrected/{sample2}_iter2.fasta'
    params:
        algorithm=fixalth
    shell:"""
        bn=$(basename {output.files} _iter2.fasta)
        if [ "{params.algorithm}" == "colormap" ];then
          {colormap} {input.fastas} {input.illumina} {prefix}_corrected/ $bn {threadsCorrection}
        else
          {proovread} -l {input.fastas} -s {input.illumina} --pre {prefix}_corrected/$bn_iter2 -t 24 --coverage=100
        fi
    """

rule mergeFASTA:
    input:
        expand(prefix+"_corrected/{sample2}_iter2.fasta", sample2=SUBSAM)
    output:
        prefix+'_corrected.fasta'
    shell:"""
        cat {input} > {output}
    """

rule assembly:
   input:
       prefix+'_corrected.fasta'
   output:
      resFile=prefix+'_assembly/res.contigs.fasta',
      resDir=prefix+'_assembly/',
   shell:"""
      canu -p {prefix} -d {output.resDir} genomeSize=565m -pacbio-raw {input} useGrid=1 "gridOptions=--partition=compute --mem=80GB --cpus-per-task=24 --time=14-0"
  """


