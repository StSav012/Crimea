#include <stdlib.h>
#include <dlfcn.h>

#include <iostream>

using namespace std;

#define INITGUID

#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/pcicmd.h"
#include "../include/plx.h"

int compare(const void *a, const void *b) {
    if (*(double*)a < *(double*)b) {
        return -1;
    }
    else if (*(double*)a > *(double*)b) {
        return 1;
    }
    return 0;
}

typedef IDaqLDevice* (*CREATEFUNCPTR)(ULONG Slot);

CREATEFUNCPTR CreateInstance;

signed short *p;
unsigned int *pp;

int main(int argc, char **argv) {
    PLATA_DESCR_U2 pd;
    ADC_PAR_0 adcPar;
    ULONG size;
    void *handle;
    char const *deviceName = "L783";
    ULONG idx;

    handle = dlopen("liblcomp.so", RTLD_LAZY);
    if (!handle) {
        return 1;
    }

    CreateInstance = (CREATEFUNCPTR) dlsym(handle, "CreateInstance");
    if (dlerror() != NULL) {
        return 2;
    }

    LUnknown* pIUnknown = CreateInstance(0);
    if (pIUnknown == NULL) { 
        return 3;
    }

    DaqL780* pI;
    if (pIUnknown->QueryInterface(IID_ILDEV, (void**)&pI) != S_OK) {
        return 4; 
    }
    pIUnknown->Release();

    pI->OpenLDevice();

    if (pI->LoadBios(deviceName) != L_SUCCESS) {
        pI->CloseLDevice();
        pI->Release();
        return 5;
    }
    if (pI->PlataTest() != L_SUCCESS) {
        pI->CloseLDevice();
        pI->Release();
        return 6;
    }
    pI->ReadPlataDescr(&pd); // REQUIRED: fill up properties from just loaded flash

    size = L_ADC_FIFO_LENGTH_PLX; //131072;

    pI->RequestBufferStream(&size);

    adcPar.s_Type = L_ADC_PARAM;
    adcPar.AutoInit = 1;     // 1 = in loop
    adcPar.dRate = 25.0;      // kHz
    adcPar.dKadr = 0;
    adcPar.dScale = 0;
    adcPar.SynchroType = 3;
    adcPar.SynchroSensitivity = 0;
    adcPar.SynchroMode = 0;
    adcPar.AdChannel = 0;
    adcPar.AdPorog = 0;
    adcPar.NCh = 2;
    if (argc > 1 && argv[1][0] >= '0' && argv[1][0] <= '9') {
        idx = atoi(argv[1]);
        if (idx >= 16) {
            pI->CloseLDevice();
            pI->Release();
            return 7;
        }
        adcPar.NCh = idx * 2;
    }
    for (ULONG i = 0; i < adcPar.NCh; ++i) {
        adcPar.Chn[i] = i;
    }
    adcPar.IrqEna = 1;
    adcPar.AdcEna = 1;

    pI->FillDAQparameters(&adcPar);
    pI->SetParametersStream(&adcPar, &size, (void **)&p, (void **)&pp, L_STREAM_ADC);

    pI->EnableCorrection(1);
    pI->InitStartLDevice();
    pI->StartLDevice();
    
    do {
        cin >> idx;
        idx *= 2;
        if (idx >= 0 && idx < adcPar.NCh) {
            // copy voltages and calculate median
            ULONG count = (size - idx + 1) / adcPar.NCh;
            double *data = new double[count];
            for (ULONG i = idx, j = 0; i < size && j < count; i += adcPar.NCh) {
                data[j++] = (double)p[i];
            }
            qsort(data, count, sizeof(double[0]), compare);
            double s;
            if (count & 1) {
                s = data[count / 2];
            }
            else {
                s = 0.5 * data[count / 2] + 0.5 * data[count / 2 - 1];
            }
            delete[] data;
            s *= 10. / (1 << 12);                   // scaling
            cout << (idx >> 1) << '\t' << s << endl;
        }
    } while (idx >= 0 && idx < 16);

    pI->StopLDevice();
    pI->CloseLDevice();
    pI->Release();

    if (handle) {
        dlclose(handle);
    }
    return 0;
}

