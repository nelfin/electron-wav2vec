PYTHON_CONFIGURE_OPTS=--enable-shared --enable-framework

.PHONY: help deps clean run
help:
	@echo "make deps	install dependencies"
	@echo "make clean	remove installed dependencies"
	@echo "make run	start app"
	@echo "make help	this message"

deps:
	@command -v pyenv || ( \
		echo "*** please install pyenv, https://github.com/pyenv/pyenv#installation"; \
		exit 1)
	env PYTHON_CONFIGURE_OPTS="$(PYTHON_CONFIGURE_OPTS)" pyenv install --skip-existing
	$(MAKE) -C python-model deps
	$(MAKE) -C electron-ui deps

clean:
	$(MAKE) -C python-model clean
	$(MAKE) -C electron-ui clean

run:
	@$(MAKE) -C electron-ui run >/dev/null & \
	ELECTRON_PID=$$!; \
	$(MAKE) -C python-model run >/dev/null & \
	PYTHON_PID=$$!; \
	echo "electron=$$ELECTRON_PID python=$$PYTHON_PID"; \
	wait $$ELECTRON_PID; \
	kill $$PYTHON_PID
