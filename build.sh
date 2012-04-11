#!/bin/bash

if [ ! -d pyinstaller-1.5.1 ]; then
    curl -o pyinstaller.tar.bz2 http://cloud.github.com/downloads/pyinstaller/pyinstaller/pyinstaller-1.5.1.tar.bz2
    tar xjf pyinstaller.tar.bz2
    rm -fr pyinstaller.tar.bz2
fi

pushd pyinstaller-1.5.1
virtualenv continuity
source continuity/bin/activate
popd

python setup.py develop

pushd pyinstaller-1.5.1
arch -i386 python ./Configure.py
arch -i386 python ./Makespec.py --onefile ../prepare_commit_message.py
arch -i386 python ./Build.py prepare_commit_message/prepare_commit_message.spec
popd

mv -f pyinstaller-1.5.1/prepare_commit_message/dist/prepare_commit_message .git/hooks/prepare-commit-msg
