completed=`ls */*completed.flag 2> /dev/null | wc -l`
running=`ls */*running.flag 2> /dev/null | wc -l`
failed=`ls */*failed.flag 2> /dev/null | wc -l`
echo "completed: $completed" 
echo "running: $running"
echo "failed: $failed" 
ls  */*.flag | xargs -n1 basename | sort | uniq -c
echo "List of failed flags:"
ls */*failed.flag 2> /dev/null
