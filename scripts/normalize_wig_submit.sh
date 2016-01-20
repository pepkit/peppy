#! /bin/bash

scale=10000000
genome="mm10"
results_dir="/scratch/lab_bock/shared/projects/geissmann/results_pipeline/results_pipeline/"
stats_path="/scratch/lab_bock/shared/projects/geissmann/results_pipeline/results_pipeline/ALL_stats_summary.tsv"

logdir="$results_dir/log/"
mkdir -p $logdir

 

sbatch --export=NONE --get-user-env=L --job-name=normalize_wig --ntasks=1 --cpus-per-task=1 --mem-per-cpu=8000 --partition=longq --time=2-00:00:00 -o ${logdir}/normalize_wig_%j.log normalize_wig.R -g $genome -n $scale -r $results_dir -s $stats_path