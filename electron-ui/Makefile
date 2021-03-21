NODE_VER=14.6.0
NODEENV=python vendor/nodeenv.py
VENV=nodeenv

.PHONY: deps clean run
run:
	. $(VENV)/bin/activate; npm start

deps:
	[ -d "$(VENV)" ] || $(NODEENV) --node=$(NODE_VER) $(VENV)
	. $(VENV)/bin/activate; npm install

clean:
	-rm -r node_modules/ $(VENV)
