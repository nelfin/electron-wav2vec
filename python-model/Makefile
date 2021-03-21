VENV=venv

.PHONY: deps clean run
run:
	. $(VENV)/bin/activate; python run.py

deps:
	[ -d "$(VENV)" ] || python -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

clean:
	-rm -r "$(VENV)"
