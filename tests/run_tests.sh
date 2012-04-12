#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pushd $DIR
cd ..
export PYTHONPATH=$PWD
export CMDPATH=$PWD
cd -
for i in `ls -1 test*.py` ; do
    python $i
done
popd
