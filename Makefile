.PHONY: test test-tools

test:
	python -m pytest api/tests -q

test-tools:
	python -m pytest api/tests/test_search_sam.py api/tests/test_parse_pdf.py -q
