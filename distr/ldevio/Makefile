CC:=g++

CFLAGS:= -D_REENTERANT -DLCOMP_LINUX=1 -rdynamic -O2 -Wall -I$(TOPDIR)/include -L$(TOPDIR)/lib

CFLAGS+= -I../include -I/usr/include/nptl -L/usr/lib/nptl -L/usr/lib -ldl -lpthread

main: main.cpp
	$(CC) main.cpp $(CFLAGS) -o ldevio

clean:
	if [ -f ldevio ]; then; rm ldevio; fi
