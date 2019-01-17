help:
	@echo "This project supports the following targets"
	@echo ""
	@echo " make help - show this text"
	@echo " make submodules - make sure that the submodules are up-to-date"
	@echo " make lint - run flake8"
	@echo " make test - run the unittests and lint"
	@echo " make unittest - run the tests defined in the unittest subdirectory"
	@echo " make functional - run the tests defined in the functional subdirectory"
	@echo " make release - build the charm"
	@echo " make clean - remove unneeded files"
	@echo ""

submodules:
	@echo "Cloning submodules"
	@git submodule update --init --recursive

lint:
	@echo "Running flake8"
	@cd src && tox -e lint

test: unittest functional lint

unittest:
	@cd src && tox -e unit

functional: build
	@cd src && tox -e functional

build:
	@echo "Building charm to base directory $(JUJU_REPOSITORY)"
	@-git describe --tags > ./src/repo-info
	@LAYER_PATH=./layers INTERFACE_PATH=./interfaces TERM=linux \
		JUJU_REPOSITORY=$(JUJU_REPOSITORY) charm build ./src --force

release: clean build
	@echo "Charm is built at $(JUJU_REPOSITORY)/builds"

push: release
	@echo "Pushing $(JUJU_REPOSITORY)/builds/gitlab"
	@charm push $(JUJU_REPOSITORY)/builds/gitlab cs:~pirate-charmers/gitlab

clean:
	@echo "Cleaning files"
	@if [ -d src/.tox ] ; then rm -r src/.tox ; fi
	@if [ -d src/.pytest_cache ] ; then rm -r src/.pytest_cache ; fi
	find . -iname \*.pyc -delete

# The targets below don't depend on a file
.PHONY: lint test unittest functional build release clean help submodules
