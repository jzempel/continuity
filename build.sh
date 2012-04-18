#!/bin/bash

if [ ! -d pyinstaller-1.5.1 ]; then
    curl -o pyinstaller.tar.bz2 http://cloud.github.com/downloads/pyinstaller/pyinstaller/pyinstaller-1.5.1.tar.bz2
    tar xjf pyinstaller.tar.bz2
    rm -fr pyinstaller.tar.bz2
    sed -e "s/del sys\.modules\[fqname\]/if fqname in sys\.modules: del sys\.modules\[fqname\]/" pyinstaller-1.5.1/iu.py > pyinstaller-1.5.1/iu.tmp
    mv -f pyinstaller-1.5.1/iu.tmp pyinstaller-1.5.1/iu.py
fi

pushd pyinstaller-1.5.1
virtualenv continuity
source continuity/bin/activate
popd

python setup.py develop

pushd pyinstaller-1.5.1
arch -i386 python ./Configure.py
arch -i386 python ./Makespec.py --onefile ../shell.py -n continuity
arch -i386 python ./Build.py continuity/continuity.spec
popd

mv -f pyinstaller-1.5.1/continuity/dist/continuity /usr/local/bin/
