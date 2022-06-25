CC:=g++

CFLAGS:= -D_REENTERANT -rdynamic -O0 -Wall -I$(TOPDIR)/include -L$(TOPDIR)/lib
CFLAGS+= -I../include -I/usr/include/nptl -L/usr/lib/nptl -ldl -lpthread

adctest: adctest.cpp
	$(CC) adctest.cpp $(CFLAGS) -o adctest

clean:
	rm adctest
