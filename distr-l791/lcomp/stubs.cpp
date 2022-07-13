#include <stdio.h>
#include <dlfcn.h>
#include <string.h>

#include "../include/stubs.h"
#include "../include/ioctl.h"

// 0 sucess 1 error

BOOL FreeLibrary(HINSTANCE handle)
{
    return dlclose(handle);
}

HINSTANCE LoadLibrary(const char *szLibFileName)
{
    return dlopen(szLibFileName, RTLD_LAZY);
}

void *GetProcAddress(HINSTANCE handle, const char *szProcName)
{
    dlerror();
    void *ptr = dlsym(handle, szProcName);
    if (dlerror() == NULL) {
        return ptr;
    }
    return NULL;
}


BOOL CloseHandle(HANDLE hDevice)
{
    return close(hDevice);
}

HANDLE CreateFile(const char *szDrvName)
{
    return open(szDrvName, O_RDWR);
}

// in linux define handle as int
// maximum read/write size is 4096 byte
// see source for limitations...
BOOL IoControl(HANDLE hDevice,
               ULONG dwIoControlCode,
               LPVOID lpInBuffer,
               ULONG nInBufferSize,
               LPVOID lpOutBuffer,
               ULONG nOutBufferSize,
               PULONG lpBytesReturned)
{
    BOOL status = FALSE;
    IOCTL_BUFFER ibuf;
    unsigned int i;
    do {
        if (nInBufferSize > 4096) {
            printf("in buffer size > 4096");
            break;
        }
        if (nOutBufferSize > 4096) {
            printf("out buffer size > 4096");
            break;
        }

        memset(&ibuf, 0, sizeof(ibuf));

        if (lpOutBuffer) {
            ibuf.outSize = nOutBufferSize;
            for (i = 0; i < nOutBufferSize; ++i) {
                ibuf.outBuffer[i] = ((PUCHAR)lpOutBuffer)[i];
            }
        }

        if (lpInBuffer) {
            for (i = 0; i < nInBufferSize; ++i) {
                ibuf.inBuffer[i] = ((PUCHAR)lpInBuffer)[i];
            }
            ibuf.inSize = nInBufferSize;
        }

        if (ioctl((int)hDevice, dwIoControlCode, &ibuf)) {
            break;
        }
        if (lpOutBuffer) {
            for (i = 0; i < nOutBufferSize; ++i) {
                ((PUCHAR)lpOutBuffer)[i] = ibuf.outBuffer[i];
            }
        }
        *lpBytesReturned = ibuf.outSize;
        status = TRUE;
    } while (status == FALSE);
    return status;
}
