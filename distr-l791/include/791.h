#include <stdint.h>

class DaqL791
{
public:
   // Base functions
   IFC(ULONG) ReadFlashWord(USHORT Addr, PUSHORT Data);
   IFC(ULONG) WriteFlashWord(USHORT Addr, USHORT Data);
   IFC(ULONG) ReadBoardDescr(BOARD_DESCR_L791 &pd);
   IFC(ULONG) WriteBoardDescr(BOARD_DESCR_L791 &pd, USHORT Ena);
   IFC(ULONG) EnableFlashWrite(USHORT Flag);

   IFC(ULONG)  FillADCParameters(ADC_PAR &sp);
   IFC(ULONG)  FillDACParameters(DAC_PAR &sp);

   ULONG InputTTL(PDAQ_PAR sp);  //2 in 1 all
   ULONG OutputTTL(PDAQ_PAR sp);  // in each set channel
   ULONG ConfigTTL(PDAQ_PAR sp); // 1221 and 1450 780C 791
   ULONG OutputDAC(PDAQ_PAR sp); //2 in 1
   ULONG InputADC(PDAQ_PAR sp);

   IFC(HRESULT) QueryInterface(const IID& iid, void** ppv);
   IFC(ULONG) AddRef();
   IFC(ULONG) Release();

   // Service functions
   IFC(ULONG) GetSlotParam(PSLOT_PAR slPar);

   // Common functions
   IFC(HANDLE) Open();
   IFC(ULONG) Close();

   IFC(uint16_t*) GetIOBuffer(ULONG streamID);
   IFC(size_t)    GetIOBufferSize(ULONG streamID);
   IFC(uint32_t*) GetRegBuffer();
   IFC(size_t)    GetRegBufferSize();

   IFC(ULONG) SetStreamParameters(DAQ_PAR &sp, ULONG streamID);
   IFC(ULONG) RequestStreamBuffer(ULONG streamID);  // in words

// two step must be
   IFC(ULONG) InitStart();
   IFC(ULONG) Start();
   IFC(ULONG) Stop();

   IFC(ULONG) IoAsync(PDAQ_PAR sp);  // collect all async io operations

   IFC(ULONG) SetEvent(HANDLE hEvent, ULONG EventId = STREAM_ADC);

   DaqL791(ULONG Slot = 0)
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

   virtual ~DaqL791() {}

// service function
   void CopyDACtoWDAQ(PDAC_PAR dac, PWDAC_PAR sp);
   void CopyADCtoWDAQ(PADC_PAR adc, PWADC_PAR sp);

private:
   atomic_t m_cRef;
   ULONG    m_Slot;

protected:
   //  this is DEV_ALL
   HANDLE      hVxd;

   HANDLE      hEvent; // for ovelapped DIOC_START under NT
   OVERLAPPED  ov;

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
   size_t map_regSize;
   void *map_regBuffer;
};
