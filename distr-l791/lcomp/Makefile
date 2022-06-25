CC:=g++
LD:=ld
AR:=ar
SH:=sh

CFLAGS:= -fPIC -c -O -g -Wall -I$(TOPDIR)/include -L$(TOPDIR)/lib

LIB_VERSION:=1
LIB_PATCHLEVEL:=56
LIB_RELEASE:=
#.$(LIB_VERSION).$(LIB_PATCHLEVEL)

CFLAGS+= -I../include -L../lib

LIBS:=liblcomp.so$(LIB_RELEASE)

# PARTS:= stubs.o maincomp.o lguids.o ldevbase.o 791.o
PARTS:= stubs.o maincomp.o lguids.o 791.o

all: $(LIBS)

liblcomp.so$(LIB_RELEASE): $(PARTS)
	$(CC) -shared -Wl,-soname,liblcomp.so -o liblcomp.so$(LIB_RELEASE) $(PARTS) -lc


maincomp.o: maincomp.cpp
	$(CC) $(CFLAGS) maincomp.cpp

stubs.o: stubs.cpp
	$(CC) $(CFLAGS) stubs.cpp

lguids.o: lguids.cpp
	$(CC) $(CFLAGS) lguids.cpp

ldevbase.o: ldevbase.cpp
	$(CC) $(CFLAGS) ldevbase.cpp

plx.o: plx.cpp
	$(CC) $(CFLAGS) plx.cpp

loadplx.o: loadplx.cpp
	$(CC) $(CFLAGS) loadplx.cpp

791.o: 791.cpp
	$(CC) $(CFLAGS) 791.cpp

install:
	cp liblcomp.so /usr/lib/

clean:
	if ls *.o > /dev/null; then rm *.o; fi
	if ls *.so > /dev/null; then rm *.so; fi
