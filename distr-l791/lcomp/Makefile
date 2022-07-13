CC:=g++
LD:=ld
AR:=ar
SH:=sh

CFLAGS:= -fPIC -c -O -g -Wall -Wpedantic -I$(TOPDIR)/include -L$(TOPDIR)/lib

LIB_VERSION:=1
LIB_PATCHLEVEL:=56
LIB_RELEASE:=

CFLAGS+= -I../include -L../lib

LIBS:=libl791.so$(LIB_RELEASE)

PARTS:= stubs.o maincomp.o lguids.o 791.o

all: $(LIBS)

libl791.so$(LIB_RELEASE): $(PARTS)
	$(CC) -shared -Wl,-soname,libl791.so -o libl791.so$(LIB_RELEASE) $(PARTS) -lc

maincomp.o: maincomp.cpp
	$(CC) $(CFLAGS) maincomp.cpp

stubs.o: stubs.cpp
	$(CC) $(CFLAGS) stubs.cpp

lguids.o: lguids.cpp
	$(CC) $(CFLAGS) lguids.cpp

ldevbase.o: ldevbase.cpp
	$(CC) $(CFLAGS) ldevbase.cpp

791.o: 791.cpp
	$(CC) $(CFLAGS) 791.cpp

install:
	cp libl791.so /usr/lib/

clean:
	if ls *.o > /dev/null; then rm *.o; fi
	if ls *.so > /dev/null; then rm *.so; fi
