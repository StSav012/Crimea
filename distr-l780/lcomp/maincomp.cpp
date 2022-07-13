#include <stdio.h>
#include <errno.h>

#include "../include/stubs.h"
#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/780.h"

void LSetLastError(int err)
{
    errno = err;
}

unsigned long LGetLastError(void)
{
    return errno;
}

extern "C" {

    // main function of dll
    DaqL780* createInstance(ULONG Slot)
    {
        LSetLastError(SUCCESS);
        DaqL780 *pL = new DaqL780(Slot);

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
        pL->GetSlotParam(sl);

        pL->Close();
        if (sl.BoardType != PCIA && sl.BoardType != PCIB && sl.BoardType != PCIC) {
            delete pL;
            pL = nullptr;
            LSetLastError(NOT_SUPPORTED);
        }
        else {
            pL->AddRef();
        }

        return pL;
    }

    FDF(HANDLE) openBoard(DaqL780* board)
    {
        return board->Open();
    }

    FDF(ULONG) closeBoard(DaqL780* board)
    {
        return board->Close();
    }

    FDF(ULONG) readBoardDescription(DaqL780* board, BOARD_DESCR &pd)
    {
        return board->ReadBoardDescr(pd);
    }

    FDF(ULONG) requestStreamBuffer(DaqL780* board, ULONG streamID)
    {
        return board->RequestStreamBuffer(streamID);
    }

    FDF(ULONG) fillADCParameters(DaqL780* board, ADC_PAR &ap)
    {
        return board->FillADCParameters(ap);
    }

    FDF(ULONG) fillDACParameters(DaqL780* board, DAC_PAR &dp)
    {
        return board->FillDACParameters(dp);
    }

    FDF(ULONG) setStreamParameters(DaqL780* board, DAQ_PAR &sp, ULONG streamID)
    {
        return board->SetStreamParameters(sp, streamID);
    }

    FDF(uint16_t*) getIOBuffer(DaqL780* board, ULONG streamID)
    {
        return board->GetIOBuffer(streamID);
    }

    FDF(size_t) getIOBufferSize(DaqL780* board, ULONG streamID)
    {
        return board->GetIOBufferSize(streamID);
    }

    FDF(ULONG) initStart(DaqL780* board)
    {
        return board->InitStart();
    }

    FDF(ULONG) start(DaqL780* board)
    {
        return board->Start();
    }

    FDF(ULONG) stop(DaqL780* board)
    {
        return board->Stop();
    }

    FDF(ULONG) loadFirmware(DaqL780* board, char firmwareFileName[] = nullptr)
    {
        return board->LoadBios(firmwareFileName);
    }

    FDF(ULONG) getSlotParameters(DaqL780* board, SLOT_PAR &slPar)
    {
        return board->GetSlotParam(slPar);
    }

    FDF(ULONG) test(DaqL780* board)
    {
        return board->Test();
    }
}
