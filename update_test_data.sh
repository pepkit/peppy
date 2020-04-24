#!/bin/bash

if [ $# -ne 1 ]; then
    echo $0: usage: update_test_data.sh branch
    exit 1
fi

branch=$1

wget https://github.com/pepkit/example_peps/archive/${branch}.zip
mv ${branch}.zip tests/data/
cd tests/data/
rm -rf example_peps-${branch} 
unzip ${branch}.zip
rm ${branch}.zip
