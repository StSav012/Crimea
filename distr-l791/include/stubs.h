#ifndef __STUBS__
#define __STUBS__ 1

#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <atomic_ops.h>


typedef struct { volatile AO_t counter; } atomic_t;

// windows types...

#include "../include/guiddef.h"

#define __stdcall


typedef void *LPVOID;
typedef void *PVOID;
typedef int   HANDLE;
typedef void *HMODULE;
typedef void *HINSTANCE;
typedef char CHAR, *PCHAR;
typedef unsigned char UCHAR, *PUCHAR;
typedef unsigned int ULONG, ULONG32, *PULONG;
typedef int LONG, *PLONG;
typedef short SHORT, *PSHORT;
typedef unsigned short USHORT, *PUSHORT;
typedef int BOOL;

typedef LONG HRESULT;

typedef struct _OVERLAPPED {
    ULONG Internal;
    ULONG InternalHigh;
    union {
        struct {
            ULONG Offset;
            ULONG OffsetHigh;
        };

        PVOID Pointer;
    };

    HANDLE  hEvent;
} OVERLAPPED, *LPOVERLAPPED;


#define TRUE 1
#define FALSE 0
#define INVALID_HANDLE_VALUE ((HANDLE)(-1))


#define ERROR_INVALID_FUNCTION           1L    // dderror
#define ERROR_FILE_NOT_FOUND             2L
#define ERROR_PATH_NOT_FOUND             3L
#define ERROR_TOO_MANY_OPEN_FILES        4L
#define ERROR_ACCESS_DENIED              5L
#define ERROR_INVALID_HANDLE             6L

#ifdef RC_INVOKED
#define _HRESULT_TYPEDEF_(_sc) _sc
#else // RC_INVOKED
#define _HRESULT_TYPEDEF_(_sc) ((HRESULT)_sc)
#endif // RC_INVOKED

#define E_NOINTERFACE                    _HRESULT_TYPEDEF_(0x80004002L)
#define S_OK                             ((HRESULT)0x00000000L)


#ifndef NULL
#ifdef __cplusplus
#define NULL    0
#else
#define NULL    ((void *)0)
#endif
#endif



// some math function
#define l_fabs(x) ((x>=0) ? x:(-x))
#define l_ceil(x) ((double)((int)x+1))

BOOL FreeLibrary(HINSTANCE handle);
HINSTANCE LoadLibrary(const char *szLibFileName);
void *GetProcAddress(HINSTANCE handle, const char *szProcName);


BOOL CloseHandle(HANDLE hDevice);
HANDLE CreateFile(const char *szDrvName);

BOOL IoControl(HANDLE hDevice,
               ULONG dwIoControlCode,
               LPVOID lpInBuffer,
               ULONG nInBufferSize,
               LPVOID lpOutBuffer,
               ULONG nOutBufferSize,
               PULONG lpBytesReturned,
               LPOVERLAPPED lpOverlapped);

#endif

