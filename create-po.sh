#!/usr/bin/zsh

xgettext -d plyoox -o src/translation/locales/base.pot src/**/*.py
cd src/translation && python3 merge_po.py