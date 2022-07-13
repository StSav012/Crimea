#include <dlfcn.h>
#include <iostream>

using namespace std;

#define INITGUID

#include "../include/stubs.h"
#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/780.h"

int compare(const void *a, const void *b) {
    if (*(double*)a < *(double*)b) {
        return -1;
    }
    else if (*(double*)a > *(double*)b) {
        return 1;
    }
    return 0;
}

//Att. for board slot numbers!!!!

int main(int argc, char **argv) {
    void *handle;
    char *error;

    cout << "L-780 simple example." << endl;
    cout << "(c) 2007 L-Card." << endl;

    handle = dlopen("./liblcomp.so", RTLD_LAZY);
    if (!handle) {
        cout << "error opening dll!! " << dlerror() << endl;
        return 1;
    }

    dlerror();

    typedef DaqL780* (*CREATEFUNCPTR)(ULONG Slot);
    CREATEFUNCPTR CreateInstance = (CREATEFUNCPTR) dlsym(handle, "createInstance");
    if ((error = dlerror()) != NULL) {
        cout << error << endl;
        return 1;
    }

    DaqL780* pI = CreateInstance(0);
    cout << errno << endl;
    if (pI == nullptr) {
        cout << "CreateInstance call failed " << endl;
        return 1;
    }

    cout << "Open Handle" << hex << pI->Open() << endl;

    cout << endl << "Slot parameters" << endl;
    SLOT_PAR sl;
    pI->GetSlotParam(sl);

    cout << "Base    " << hex << sl.Base << endl;
    cout << "BaseL   " << sl.BaseL << endl;
    cout << "Mem     " << sl.Mem << endl;
    cout << "MemL    " << sl.MemL << endl;
    cout << "Type    " << sl.BoardType << endl;
    cout << "DSPType " << sl.DSPType << endl;
    cout << "Irq     " << sl.Irq << endl;

    cout << "Load Firmware " << pI->LoadBios() << endl;
    cout << "Board Test    " << pI->Test() << endl;

    cout << endl << "Read FLASH" << endl;

    // FIXME: why is this necessary to get the correct value of the frame rate???
    BOARD_DESCR pd;
    pI->ReadBoardDescr(pd); // fill up properties

    ULONG size = 512*1024;

    pI->RequestStreamBuffer(size);

    cout << "Buffer size:             " << size << endl;

    ADC_PAR adcPar;
    // заполняем структуру  с описанием параметров сбора данных с АЦП
    adcPar.s_Type = ADC_PARAM;
    adcPar.AutoInit = 1;       // 1 = in loop
    adcPar.dRate = 200.0;      // kHz
    adcPar.dFrame = .01;

    adcPar.SynchroType = 0;
    adcPar.SyncChannel = 0;

    adcPar.NCh = 4;
    adcPar.Chn[0] = 0x0;
    adcPar.Chn[1] = 0x1;
    adcPar.Chn[2] = 0x2;
    adcPar.Chn[3] = 0x3;

    adcPar.FIFO = 1024;

    adcPar.IrqStep = 1024;
    adcPar.Pages = 64;
    adcPar.IrqEna = 3;  // работает без прерываний
    adcPar.AdcEna = 1;  // разрешаем АЦП
    // можно прерывания разрешить тогда будет генерироваться событие см OSC_L791.TST

    pI->FillADCParameters(adcPar);

    pI->SetStreamParameters(adcPar, STREAM_ADC);
    size = pI->GetIOBufferSize(STREAM_ADC);
    uint16_t *data = pI->GetIOBuffer(STREAM_ADC);

    if (data == nullptr) {
        cout << "Failed to allocate data" << endl;
        return 1;
    }

    cout << "L791 Buffer size [word]: " << size << endl;
    cout << "Pages:                   " << adcPar.Pages << endl;
    cout << "IrqStep:                 " << adcPar.IrqStep << endl;
    cout << "FIFO:                    " << adcPar.FIFO << endl;
    cout << "Frame rate [kHz]:        " << adcPar.dRate << endl;
    cout << "Frame delay [ms]:        " << adcPar.dFrame << endl;

    pI->InitStart();
    cout << "init device started" << endl;
    pI->Start();
    cout << "device started" << endl;

    ULONG idx;
    do {
        cout << "enter something: ";
        cin >> idx;
        if (idx >= 0 && idx < adcPar.NCh) {
            // copy voltages and calculate median
            ULONG count = (size - idx + 1) / adcPar.NCh;
            uint16_t *raw_data = new uint16_t[count];
            for (ULONG i = idx, j = 0; i < size && j < count; i += adcPar.NCh) {
                raw_data[j++] = data[i];
            }
            qsort(raw_data, count, sizeof(uint16_t), compare);
            double s;
            if (count & 1) {
                s = (double)raw_data[count / 2];
            }
            else {
                s = 0.5 * (double)raw_data[count / 2] + 0.5 * (double)raw_data[count / 2 - 1];
            }
            delete[] raw_data;
            s *= 10. / (1 << 14);                   // scaling
            cout << idx << '\t' << s << endl;
        }
    } while (idx >= 0 && idx < 16);

    pI->Stop();
    cout << "device stoped" << endl;
    pI->Close();
    cout << "device closed" << endl;
    pI->Release();

    if (handle) {
        dlclose(handle);
    }
    return 0;
}
