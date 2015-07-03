#! /bin/bash

wd="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/"
dataDir="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/results_pipeline/"
outDir=$wd/differentialExpression
sampleAnnpotationFile="/fhgfs/groups/lab_bock/shared/projects/setdb2/data/pypiper_pipeline/metadata/projectSampleAnnotation.csv"
genome="m38_cdna"

groups_column="treatment_length"
comparison_column="treatment"

groups="0h 2h 8h 24h"
cond1="WT"
cond2="KO"


script_dir=`dirname $0`

logdir=$outDir/log
mkdir -p $logdir

if [ ! -e $outDir/$(basename $sampleAnnpotationFile) ]
then
cp $sampleAnnpotationFile $outDir
fi

local_sampleAnnpotationFile=$outDir/$(basename $sampleAnnpotationFile)


for group in $groups;do
  	
	job=${group}_${cond1}-${cond2}_DE
	
	echo $job
if [ ! -e $outDir/$job ]; then
echo "Submitting!"
sbatch --export=NONE --get-user-env=L --job-name=$job --ntasks=1 --cpus-per-task=1 --mem-per-cpu=9000 --partition=longq --time=2-00:00:00 -o "$logdir/${job}_%j.log"  $script_dir/bitSeq-DE-humanIslet-treatment-parallel.R $wd $local_sampleAnnpotationFile $dataDir $group $genome $outDir/$job $cond1  $cond2 $groups_column $comparison_column
else
  echo "file found. Not submitting!"
fi

done



