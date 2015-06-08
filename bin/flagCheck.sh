completed=`ls */*completed.flag 2> /dev/null | wc -l`
running=`ls */*running.flag 2> /dev/null | wc -l`
failed=`ls */*failed.flag 2> /dev/null | wc -l`
echo "completed: $completed" 
echo "running: $running"
echo "failed: $failed" 
ls  */*.flag | xargs -n1 basename | sort | uniq -c

if [ $failed -lt 10 ]; then
echo "List of failed flags:"
ls */*failed.flag 2> /dev/null
fi

if [ $completed -lt 10 ]; then
echo "List of completed flags:"
ls */*completed.flag 2> /dev/null
fi

if [ $running -lt 10 ]; then
echo "List of running flags:"
ls */*running.flag 2> /dev/null
fi

