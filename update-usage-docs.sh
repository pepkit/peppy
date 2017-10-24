cp doc/source/usage.template usage.template
#looper --help > USAGE.temp 2>&1

for cmd in "--help" "run --help" "summarize --help" "destroy --help" "check --help" "clean --help" "--help"; do
	echo $cmd
	echo -e "\n\`\`looper $cmd\`\`" > USAGE_header.temp
	echo -e "----------------------------------" >> USAGE_header.temp
	looper $cmd --help > USAGE.temp 2>&1
	sed -i 's/^/\t/' USAGE.temp
	sed -i '1s/^/\n.. code-block:: none\n\n/' USAGE.temp
	#sed -i -e "/\`looper $cmd\`/r USAGE.temp" -e '$G' usage.template  # for -in place inserts
	cat USAGE_header.temp USAGE.temp >> usage.template # to append to the end
done
rm USAGE.temp
rm USAGE_header.temp
mv usage.template  doc/source/usage.rst
cat doc/source/usage.rst
#rm USAGE.temp
