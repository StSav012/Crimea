CC:=g++
LD:=ld
AR:=ar
SH:=sh

CFLAGS:= -fPIC -c -O -g -Wall -Wpedantic -I$(TOPDIR)/include -L$(TOPDIR)/lib

LIB_VERSION:=1
LIB_PATCHLEVEL:=56
LIB_RELEASE:=

CFLAGS+= -I../include -L../lib

LIBS:=libl780.so$(LIB_RELEASE)

PARTS:= stubs.o maincomp.o lguids.o 780.o

all: $(LIBS)

libl780.so$(LIB_RELEASE): $(PARTS)
	$(CC) -shared -Wl,-soname,libl780.so -o libl780.so$(LIB_RELEASE) $(PARTS) -lc

maincomp.o: maincomp.cpp
	$(CC) $(CFLAGS) maincomp.cpp

stubs.o: stubs.cpp
	$(CC) $(CFLAGS) stubs.cpp

lguids.o: lguids.cpp
	$(CC) $(CFLAGS) lguids.cpp

780.o: 780.cpp
	$(CC) $(CFLAGS) 780.cpp

install:
	cp libl780.so /usr/lib/

clean:
	if ls *.o > /dev/null; then rm *.o; fi
	if ls *.so > /dev/null; then rm *.so; fi
