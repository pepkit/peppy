#! /bin/bash

wd="/scratch/lab_bock/shared/projects/hap1-knockouts/"
dataDir="/scratch/lab_bock/shared/projects/hap1-knockouts/results_pipeline/"
outDir=$wd/differentialExpression
sampleAnnpotationFile="/data/groups/lab_bock/jklughammer/gitRepos/hap1-knockouts/metadata/rna.sample_annotation.csv"
genome="hg19_cdna"

groups_column="exp_category"
comparison_column="treatment"

groups="QUANT TRUSEQ"
cond1="WT"
cond2s="DNMT3B-KO MECP2-KO TET2-KO DNMT1-KO"


script_dir=`dirname $0`

logdir=$outDir/log
mkdir -p $logdir

if [ ! -e $outDir/$(basename $sampleAnnpotationFile) ]
then
cp $sampleAnnpotationFile $outDir
fi

local_sampleAnnpotationFile=$outDir/$(basename $sampleAnnpotationFile)


for group in $groups;do

	for cond2 in $cond2s;do
  	
	job=${group}_${cond1}-${cond2}_DE
	
	echo $job
if [ ! -e $outDir/$job ]; then
echo "Submitting!"
sbatch --export=NONE --get-user-env=L --job-name=$job --ntasks=1 --cpus-per-task=1 --mem-per-cpu=9000 --partition=longq --time=2-00:00:00 -o "$logdir/${job}_%j.log"  $script_dir/bitSeq-DE-humanIslet-treatment-parallel.R $wd $local_sampleAnnpotationFile $dataDir $group $genome $outDir/$job $cond1  $cond2 $groups_column $comparison_column
else
  echo "file found. Not submitting!"
fi
	done
done



