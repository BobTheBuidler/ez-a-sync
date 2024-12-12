
.PHONY: docs

docs:
	rm -r ./docs/source -f
	rm -r ./docs/_templates -f
	rm -r ./docs/_build -f
	sphinx-apidoc --private -o ./docs/source ./a_sync

cython:
	python setup.py build_ext --inplace

stubs:
	stubgen ./a_sync -o . --include-docstrings