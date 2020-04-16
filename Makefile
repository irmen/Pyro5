.PHONY: all dist docs install upload clean test
PYTHON=python3

all:
	@echo "targets: dist, docs, upload, install, clean, test"

docs:
	$(PYTHON) setup.py build_sphinx

dist:
	$(PYTHON) setup.py sdist bdist_wheel

upload: dist
	@echo "Uploading to Pypi using twine...."
	twine upload dist/*

install:
	$(PYTHON) setup.py install

test:
	PYTHONPATH=. python3 -m pytest tests

clean:
	@echo "Removing tox dirs, logfiles, temp files, .pyo/.pyc files..."
	rm -rf .tox .eggs .cache .pytest_cache *.egg-info
	find . -name __pycache__ -print0 | xargs -0 rm -rf
	find . -name \*_log -print0 | xargs -0  rm -f
	find . -name \*.log -print0 | xargs -0  rm -f
	find . -name \*_URI -print0 | xargs -0  rm -f
	find . -name \*.pyo -print0 | xargs -0  rm -f
	find . -name \*.pyc -print0 | xargs -0  rm -f
	find . -name \*.class -print0 | xargs -0  rm -f
	find . -name \*.DS_Store -print0 | xargs -0  rm -f
	find . -name \.coverage -print0 | xargs -0  rm -f
	find . -name \coverage.xml -print0 | xargs -0  rm -f
	rm -f MANIFEST
	rm -rf build
	rm -rf dist
	rm -rf tests/test-reports
	find . -name  '.#*' -print0 | xargs -0  rm -f
	find . -name  '#*#' -print0 | xargs -0  rm -f
	@echo "clean!"
