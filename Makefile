prefix = /usr/local
bindir = $(prefix)/bin
BUILD = build
INSTALLER = pyinstaller-1.5.1
PYTHON = python

override EXENAME = continuity
override PYTHON_PATH = $(BUILD)/lib/python

.PHONY: install uninstall clean

install: $(BUILD)/dist/$(EXENAME)
	mkdir -p $(DESTDIR)$(bindir)/
	mv -f $(BUILD)/dist/$(EXENAME) $(DESTDIR)$(bindir)/$(EXENAME)

uninstall: clean
	rm -rf $(INSTALLER)
	rm -f $(DESTDIR)$(bindir)/$(EXENAME)

clean:
	rm -rf $(BUILD)
	rm -f logdict*.final.*.log

$(BUILD)/dist/$(EXENAME): export PYTHONPATH = $(PYTHON_PATH)
$(BUILD)/dist/$(EXENAME): export VERSIONER_PYTHON_PREFER_32_BIT = yes
$(BUILD)/dist/$(EXENAME): $(BUILD) | $(INSTALLER)
	arch -i386 $(PYTHON) -O $(INSTALLER)/Configure.py
	arch -i386 $(PYTHON) $(INSTALLER)/Makespec.py -F run.py -n $(EXENAME) -o $(BUILD)
	arch -i386 $(PYTHON) -O $(INSTALLER)/Build.py $(BUILD)/$(EXENAME).spec

$(BUILD):
	mkdir -p $(PYTHON_PATH)/
	@PYTHONPATH=$(PYTHON_PATH) $(PYTHON) setup.py install --home $(BUILD)

$(INSTALLER):
	curl -o pyinstaller.tar.bz2 http://cloud.github.com/downloads/pyinstaller/pyinstaller/$(INSTALLER).tar.bz2
	tar xjf pyinstaller.tar.bz2
	rm -fr pyinstaller.tar.bz2
	sed -e "s/del sys\.modules\[fqname\]/if fqname in sys\.modules: del sys\.modules\[fqname\]/" $(INSTALLER)/iu.py > $(INSTALLER)/iu.tmp
	mv -f $(INSTALLER)/iu.tmp $(INSTALLER)/iu.py
