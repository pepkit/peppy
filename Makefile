lint:
	ruff format .

run-coverage:
	coverage run -m pytest

html-report:
	coverage html --omit="*/test*"

open-coverage:
	cd htmlcov && google-chrome index.html

coverage: run-coverage html-report open-coverage
