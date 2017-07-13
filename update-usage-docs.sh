looper --help > USAGE.temp 2>&1

for cmd in run summarize destroy check clean "--details"; do
	echo $cmd
	echo -e "\n\n>looper $cmd --help" >> USAGE.temp
	looper $cmd --help >> USAGE.temp 2>&1
done

sed -i 's/^/\t/' USAGE.temp
sed -e '/>looper --help/r USAGE.temp' -e '$G' doc/source/usage.template > doc/source/usage.rst
cat doc/source/usage.rst
rm USAGE.temp
