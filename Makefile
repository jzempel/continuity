prefix = /usr/local
bindir = $(prefix)/bin
BUILD = build
INSTALLER = pyinstaller-1.5.1

.PHONY: install uninstall clean

install: $(BUILD)/dist/continuity
	mkdir -p $(DESTDIR)$(bindir)/
	mv -f $(BUILD)/dist/continuity $(DESTDIR)$(bindir)/continuity

uninstall: clean
	rm -rf $(INSTALLER)
	rm -f $(DESTDIR)$(bindir)/continuity

clean:
	rm -rf $(BUILD)
	rm -f logdict*.final.*.log

$(BUILD)/dist/continuity: $(BUILD) | $(INSTALLER)
	arch -i386 $(BUILD)/bin/python $(INSTALLER)/Configure.py
	arch -i386 $(BUILD)/bin/python $(INSTALLER)/Makespec.py -F run.py -n continuity -o $(BUILD)
	arch -i386 $(BUILD)/bin/python $(INSTALLER)/Build.py $(BUILD)/continuity.spec

$(BUILD):
	virtualenv $(BUILD)
	$(BUILD)/bin/python setup.py develop

$(INSTALLER):
	curl -o pyinstaller.tar.bz2 http://cloud.github.com/downloads/pyinstaller/pyinstaller/$(INSTALLER).tar.bz2
	tar xjf pyinstaller.tar.bz2
	rm -fr pyinstaller.tar.bz2
	sed -e "s/del sys\.modules\[fqname\]/if fqname in sys\.modules: del sys\.modules\[fqname\]/" $(INSTALLER)/iu.py > $(INSTALLER)/iu.tmp
	mv -f $(INSTALLER)/iu.tmp $(INSTALLER)/iu.py
