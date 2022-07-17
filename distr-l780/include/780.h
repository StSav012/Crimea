#include <stdint.h>

class DaqL780
{
public:
    // Base functions
    IFC(ULONG) ReadFlashWord(USHORT Addr, PUSHORT Data);
    IFC(ULONG) WriteFlashWord(USHORT Addr, USHORT Data);
    IFC(ULONG) ReadBoardDescr(BOARD_DESCR &pd);
    IFC(ULONG) WriteBoardDescr(BOARD_DESCR &pd, USHORT Ena);
    IFC(ULONG) EnableFlashWrite(USHORT Flag);

    IFC(ULONG)  FillADCParameters(ADC_PAR &sp);
    IFC(ULONG)  FillDACParameters(DAC_PAR &sp);

    ULONG InputTTL(ASYNC_PAR &ap);  //2 in 1 all
    ULONG OutputTTL(ASYNC_PAR &ap);  // in each set channel
    ULONG ConfigTTL(ASYNC_PAR &ap); // 1221 and 1450 780C 791
    ULONG OutputDAC(ASYNC_PAR &ap); //2 in 1
    ULONG InputADC(ASYNC_PAR &ap);

    IFC(HRESULT) QueryInterface(const IID& iid, void** ppv);
    IFC(ULONG) AddRef();
    IFC(ULONG) Release();

    // Common functions
    IFC(HANDLE) Open();
    IFC(ULONG) Close();

    IFC(uint16_t*) GetIOBuffer(ULONG streamID);
    IFC(size_t)    GetIOBufferSize(ULONG streamID);

    IFC(ULONG) SetStreamParameters(DAQ_PAR &sp, ULONG streamID);
    IFC(ULONG) RequestStreamBuffer(ULONG streamID);  // in words

    // two step must be
    IFC(ULONG) InitStart();
    IFC(ULONG) Start();
    IFC(ULONG) Stop();

    IFC(ULONG) LoadBios(char *FileName);

    IFC(ULONG) EnableCorrection(USHORT Ena = 1);

    // Base functions
    IFC(ULONG) GetWord_DM(USHORT Addr, PUSHORT Data);
    IFC(ULONG) PutWord_DM(USHORT Addr, USHORT Data);
    IFC(ULONG) PutWord_PM(USHORT Addr, ULONG Data);
    IFC(ULONG) GetWord_PM(USHORT Addr, PULONG Data);

    IFC(ULONG) GetArray_DM(USHORT Addr, ULONG Count, PUSHORT Data);
    IFC(ULONG) PutArray_DM(USHORT Addr, ULONG Count, PUSHORT Data);
    IFC(ULONG) PutArray_PM(USHORT Addr, ULONG Count, PULONG Data);
    IFC(ULONG) GetArray_PM(USHORT Addr, ULONG Count, PULONG Data);

    IFC(ULONG) SendCommand(USHORT cmd);

    // Service functions
    IFC(ULONG) Test();
    IFC(ULONG) GetSlotParam(SLOT_PAR &slPar);
    void CopyDACtoWDAQ(PDAC_PAR dac, PWDAC_PAR sp);
    void CopyADCtoWDAQ(PADC_PAR adc, PWADC_PAR sp);

    DaqL780(ULONG Slot = 0)
    {
        m_cRef.counter = 0;
        m_Slot = Slot;
        hVxd = INVALID_HANDLE_VALUE;
        hEvent = 0;
        DataBuffer = nullptr;
        DataSize = 0;

        map_inSize = 0;
        map_inBuffer = nullptr;
        map_outSize = 0;
        map_outBuffer = nullptr;
    }

    virtual ~DaqL780() {}

private:
    atomic_t m_cRef;
    ULONG    m_Slot;

protected:
    //  this is DEV_ALL
    HANDLE      hVxd;

    HANDLE      hEvent; // for ovelapped DIOC_START under NT

    SLOT_PAR sl;

    ADC_PAR adc_par;  // to fill with FillDAQparam
    DAC_PAR dac_par;

    // add for C-style driver in Linux
    WDAQ_PAR wadc_par;
    WDAQ_PAR wdac_par;

    BOARD_DESCR_U pdu;

    ULONG *DataBuffer; // pointer for data buffer for busmaster boards in windows
    ULONG DataSize;    // size of buffer

    // size and pointers for data buffers in Linux
    size_t map_inSize;
    void *map_inBuffer;
    size_t map_outSize;
    void *map_outBuffer;
};
