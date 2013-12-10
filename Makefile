prefix = /usr/local
bindir = $(prefix)/bin
sysconfdir = $(prefix)/etc
version = 1.5.1
BUILD = build
INSTALLER = pyinstaller-$(version)
PYTHON = python

override EXENAME = continuity
override PYTHON_PATH = $(BUILD)/lib/python

.PHONY: install uninstall clean

install: $(BUILD)/dist/$(EXENAME)
	mkdir -p $(DESTDIR)$(bindir)/
	mv -f $(BUILD)/dist/$(EXENAME) $(DESTDIR)$(bindir)/$(EXENAME)
	mkdir -p $(DESTDIR)$(sysconfdir)/bash_completion.d/
	cp -f completion.bash $(DESTDIR)$(sysconfdir)/bash_completion.d/$(EXENAME)

uninstall: clean
	rm -rf $(INSTALLER)
	rm -f $(DESTDIR)$(bindir)/$(EXENAME)
	rm -f $(DESTDIR)$(sysconfdir)/bash_completion.d/$(EXENAME)

clean:
	rm -rf $(BUILD)
	rm -f logdict*.final.*.log

$(BUILD)/dist/$(EXENAME): export PYTHONPATH = $(PYTHON_PATH)
$(BUILD)/dist/$(EXENAME): export VERSIONER_PYTHON_PREFER_32_BIT = yes
$(BUILD)/dist/$(EXENAME): $(BUILD) | $(INSTALLER)
	arch -i386 $(PYTHON) -O $(INSTALLER)/Configure.py
	arch -i386 $(PYTHON) $(INSTALLER)/Makespec.py -F main.py -n $(EXENAME) -o $(BUILD)
	arch -i386 $(PYTHON) -O $(INSTALLER)/Build.py $(BUILD)/$(EXENAME).spec

$(BUILD):
	mkdir -p $(PYTHON_PATH)/
	@PYTHONPATH=$(PYTHON_PATH) $(PYTHON) setup.py install --home $(BUILD)

$(INSTALLER):
	curl -L -o pyinstaller.tar.gz https://github.com/pyinstaller/pyinstaller/archive/v$(version).tar.gz
	tar xjf pyinstaller.tar.gz
	rm -fr pyinstaller.tar.gz
	sed -e "s/del sys\.modules\[fqname\]/if fqname in sys\.modules: del sys\.modules\[fqname\]/" $(INSTALLER)/iu.py > $(INSTALLER)/iu.tmp
	mv -f $(INSTALLER)/iu.tmp $(INSTALLER)/iu.py
