NODE_VER=12.8.1
NODEENV=python vendor/nodeenv.py
VENV=nodeenv

.PHONY: deps clean run
run:
	. $(VENV)/bin/activate; npm start

deps:
	[ -d "$(VENV)" ] || $(NODEENV) --node=$(NODE_VER) $(VENV)
	. $(VENV)/bin/activate; npm install
	. $(VENV)/bin/activate; npm rebuild zeromq --runtime=electron --target=7.0.0

clean:
	-rm -r node_modules/ $(VENV)
