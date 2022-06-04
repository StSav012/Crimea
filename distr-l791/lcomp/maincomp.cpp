#include <stdio.h>
#include <errno.h>

#include "../include/stubs.h"
#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/791.h"

void LSetLastError(unsigned long Err)
{
   errno = (int)Err;
}

unsigned long LGetLastError(void)
{
   return errno;
}

extern "C" {

   // main function of dll
   DaqL791* createInstance(ULONG Slot)
   {
      LSetLastError(SUCCESS);
      DaqL791 *pL = new DaqL791(Slot);
      if (pL == nullptr) {
         LSetLastError(ERROR);
         return nullptr;
      }
      HANDLE hVxd = pL->Open();
      if (hVxd == INVALID_HANDLE_VALUE) {
         if (LGetLastError() == ERROR_FILE_NOT_FOUND) {
            LSetLastError(ERROR_NO_BOARD);
         }
         if (LGetLastError() == ERROR_ACCESS_DENIED) {
            LSetLastError(ERROR_IN_USE);
         }
         return nullptr;
      }

      SLOT_PAR sl;
      pL->GetSlotParam(&sl);

      pL->Close();
      delete pL;

      DaqL791* pI;
      switch(sl.BoardType)
      {
         case L791:
         {
            pI = new DaqL791(Slot);
            pI->AddRef();
         } break;
         default:
         {
            pI = nullptr;
            LSetLastError(NOT_SUPPORTED);
         }
      }
      return pI;
   }

   FDF(HANDLE) openBoard(DaqL791* board)
   {
      return board->Open();
   }

   FDF(ULONG) closeBoard(DaqL791* board)
   {
      return board->Close();
   }

   FDF(ULONG) readBoardDescription(DaqL791* board, BOARD_DESCR_L791 &pd)
   {
      return board->ReadBoardDescr(pd);
   }

   FDF(ULONG) requestStreamBuffer(DaqL791* board, ULONG streamID)
   {
      return board->RequestStreamBuffer(streamID);
   }

   FDF(ULONG) fillADCParameters(DaqL791* board, ADC_PAR &ap)
   {
      return board->FillADCParameters(ap);
   }

   FDF(ULONG) fillDACParameters(DaqL791* board, DAC_PAR &dp)
   {
      return board->FillDACParameters(dp);
   }

   FDF(ULONG) setStreamParameters(DaqL791* board, DAQ_PAR &sp, ULONG streamID)
   {
      return board->SetStreamParameters(sp, streamID);
   }

   FDF(uint16_t*) getIOBuffer(DaqL791* board, ULONG streamID)
   {
      return board->GetIOBuffer(streamID);
   }

   FDF(size_t) getIOBufferSize(DaqL791* board, ULONG streamID)
   {
      return board->GetIOBufferSize(streamID);
   }

   FDF(uint32_t*) getRegBuffer(DaqL791* board)
   {
      return board->GetRegBuffer();
   }

   FDF(size_t) getRegBufferSize(DaqL791* board)
   {
      return board->GetRegBufferSize();
   }

   FDF(ULONG) initStart(DaqL791* board)
   {
      return board->InitStart();
   }

   FDF(ULONG) start(DaqL791* board)
   {
      return board->Start();
   }

   FDF(ULONG) stop(DaqL791* board)
   {
      return board->Stop();
   }

}
