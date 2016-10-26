prefix = /usr/local
bindir = $(prefix)/bin
sharedir = $(prefix)/share
sysconfdir = $(prefix)/etc
version = 3.2
BUILD = build
INSTALLER = pyinstaller-$(version)
PYTHON = python
VERSION = `$(PYTHON) -c "import continuity; print continuity.__version__"`

override EXENAME = continuity
override PYTHON_PATH = $(BUILD)/lib/python

.PHONY: install uninstall clean release

install: $(BUILD)/dist/$(EXENAME)
	mkdir -p $(DESTDIR)$(bindir)/
	mv -f $(BUILD)/dist/$(EXENAME) $(DESTDIR)$(bindir)/$(EXENAME)
	mkdir -p $(DESTDIR)$(sysconfdir)/bash_completion.d/
	cp -f completion.bash $(DESTDIR)$(sysconfdir)/bash_completion.d/$(EXENAME)
	mkdir -p $(DESTDIR)$(sharedir)/man/man1/
	cp -f $(BUILD)/sphinx/man/*.1 $(DESTDIR)$(sharedir)/man/man1/

uninstall: clean
	rm -rf $(INSTALLER)
	rm -f $(DESTDIR)$(bindir)/$(EXENAME)
	rm -f $(DESTDIR)$(sysconfdir)/bash_completion.d/$(EXENAME)
	rm -f $(DESTDIR)$(sharedir)/man/man1/$(EXENAME).1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-backlog.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-continuity.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-finish.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-issue.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-issues.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-review.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-start.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-story.1
	rm -f $(DESTDIR)$(sharedir)/man/man1/git-tasks.1

clean:
	rm -rf $(BUILD)
	rm -rf $(EXENAME).egg-info
	rm -rf dist
	rm -rf docs/_build
	rm -f logdict*.final.*.log

release:
	git tag -f $(VERSION)
	git push --tags
	$(PYTHON) setup.py develop
	$(PYTHON) setup.py build_sphinx
	$(PYTHON) setup.py upload_sphinx
	$(PYTHON) setup.py sdist upload
	openssl dgst -sha256 dist/continuity-$(VERSION).tar.gz

$(BUILD)/dist/$(EXENAME): export PYTHONPATH = $(PYTHON_PATH)
$(BUILD)/dist/$(EXENAME): $(BUILD) | $(INSTALLER)
	cd $(INSTALLER)/bootloader && $(PYTHON) waf distclean all
	$(PYTHON) $(INSTALLER)/pyinstaller.py -F main.py -n $(EXENAME) --distpath=$(BUILD)/dist --specpath=$(BUILD)

$(BUILD):
	mkdir -p $(PYTHON_PATH)/
	@PYTHONPATH=$(PYTHON_PATH) $(PYTHON) setup.py install --home $(BUILD)
	@PYTHONPATH=$(PYTHON_PATH) $(PYTHON) setup.py build_sphinx --build-dir $(BUILD)/sphinx --builder man

$(INSTALLER):
	curl -L -o pyinstaller.tar.gz https://github.com/pyinstaller/pyinstaller/archive/v$(version).tar.gz
	tar xjf pyinstaller.tar.gz
	rm -fr pyinstaller.tar.gz
