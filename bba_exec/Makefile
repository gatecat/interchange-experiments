run: bba_exec_test blob.bin
	./bba_exec_test blob.bin

clean:
	rm -f bba_exec_test plugin.elf plugin.bin blob.bba blob.bin

plugin.elf: plugin.c
	gcc -nostartfiles -static -fPIC -Wl,--entry=func -o $@ $^

plugin.bin: plugin.elf
	# FIXME: do we need .rodata too??
	objcopy -O binary -j .text plugin.elf plugin.bin

blob.bba: plugin.bin
	python3 create_bba.py $^ $@

blob.bin: blob.bba
	bbasm --l $^ $@

bba_exec_test: bba_exec_test.cc
	g++ -o $@ $^

.PHONY: run
