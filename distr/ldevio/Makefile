CC:=g++

CFLAGS:= -D_REENTERANT -rdynamic -O2 -Wall -L/usr/lib -ldl -lpthread

all:
	$(CC) main.cpp $(CFLAGS) -o ldevio

clean:
	if [ -f ldevio ]; then; rm ldevio; fi

