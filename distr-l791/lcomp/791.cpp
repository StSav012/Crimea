#include <stdio.h>
#include <string.h>
#include "../include/stubs.h"
#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/791.h"
#include "../include/791cmd.h"

HRESULT __stdcall DaqL791::QueryInterface(const IID& iid, void** ppv)
{
    if (iid == IID_IUnknown || iid == IID_ILDEV) {
        *ppv = static_cast<DaqL791*>(this);
    } else {
        *ppv = nullptr;
        return E_NO_INTERFACE;
    }
    reinterpret_cast<DaqL791*>(*ppv)->AddRef();
    return S_OK;
}

ULONG __stdcall DaqL791::AddRef()
{
    ++m_cRef.counter;
    return m_cRef.counter;
}

ULONG __stdcall DaqL791::Release()
{
    --m_cRef.counter;
    if (m_cRef.counter == 0) {
        delete this;
        return 0;
    }
    return m_cRef.counter;
}

// COMMON FUNCTIONS //////////////////////////////////////
FDF(ULONG) DaqL791::GetSlotParam(PSLOT_PAR slPar)
{
    memcpy(slPar, &sl, sizeof(SLOT_PAR));
    return 0;
}

FDF(HANDLE) DaqL791::Open()
{
    char szDrvName[18];
    snprintf(szDrvName, 18, "/dev/ldev%d", m_Slot);
    hVxd = CreateFile(szDrvName);
    if (hVxd == INVALID_HANDLE_VALUE) {
        return INVALID_HANDLE_VALUE;
    }
    ULONG cbRet;
    ULONG status = !IoControl(hVxd, DIOC_GET_PARAMS,
                              NULL, 0,
                              &sl, sizeof(SLOT_PAR),
                              &cbRet);
    if (status) {
        return INVALID_HANDLE_VALUE; // must be for register config!!!
    }
    hEvent = 0;
    map_regSize = 4096;  // page size
    map_regBuffer = (uint32_t*)mmap(0, map_regSize, PROT_READ|PROT_WRITE, MAP_SHARED/*|MAP_LOCKED*/, hVxd, 0x3000);  //0x3* sysconf(_SC_PAGE_SIZE));
    if (map_regBuffer == nullptr) {
        return INVALID_HANDLE_VALUE;
    }
    return hVxd;
}

FDF(ULONG) DaqL791::Close()
{
    ULONG status = ERROR;
    if (hVxd == INVALID_HANDLE_VALUE) {
        return status;
    }
    status = CloseHandle(hVxd);
    hVxd = INVALID_HANDLE_VALUE;     ////////////////        !!!!!!!!!!!!!!!!!! close before open
    if (map_inBuffer) {
        munmap(map_inBuffer, map_inSize * sizeof(short));
        map_inBuffer = nullptr;
        map_inSize = 0;
    }
    if (map_outBuffer) {
        munmap(map_outBuffer, map_outSize * sizeof(short));
        map_outBuffer = nullptr;
        map_outSize = 0;
    }
    if (map_regBuffer) {
        munmap(map_regBuffer, map_regSize);
        map_regBuffer = nullptr;
        map_regSize = 0;
    }
    return status;
}

// uni stream interface
FDF(ULONG) DaqL791::RequestStreamBuffer(ULONG streamID)  //in words
{
    ULONG cbRet;
    ULONG size = 128 * 2048;
    ULONG status = ERROR;
    ULONG DiocCode;
    ULONG pb = size;
    switch(streamID)
    {
        case STREAM_ADC:
        {
            DiocCode = DIOC_SET_BUFFER_ADC;
        } break;
        case STREAM_DAC:
        {
            DiocCode = DIOC_SET_BUFFER_DAC;
        } break;
        default:
        {
            return ERROR;
        }
    }
    status = !IoControl(hVxd, DiocCode,
                        &pb, sizeof(ULONG),
                        &size, sizeof(ULONG),
                        &cbRet);
    // for L791, size is 512*1024 16-bit words, in linux 128*2048
    size += 2048;    // +2048 for mapping pagecount page
    // in ldevpcibm for correct -1 page returned from driver
    switch(streamID)
    {
        case STREAM_ADC:
        {
            if (map_inBuffer) {
                munmap(map_inBuffer, map_inSize*sizeof(uint16_t));
            }
            map_inSize = size;
            map_inBuffer = mmap(0, map_inSize*sizeof(uint16_t), PROT_READ, MAP_SHARED/*|MAP_LOCKED*/, hVxd, 0x1000); //may be correct 0x1*sysconf(_SC_PAGE_SIZE));
            if(map_inBuffer == MAP_FAILED) {
                map_inBuffer = nullptr;
                status = ERROR;
            }
        } break;
        case STREAM_DAC:
        {
            if (map_outBuffer) {
                munmap(map_outBuffer, map_outSize*sizeof(uint16_t));
            }
            map_outSize = size;
            map_outBuffer = mmap(0, map_outSize*sizeof(uint16_t), PROT_READ | PROT_WRITE, MAP_SHARED/*|MAP_LOCKED*/, hVxd, 0x2000); //may be correct 0x2*sysconf(_SC_PAGE_SIZE));
            if (map_outBuffer == MAP_FAILED) {
                map_outBuffer = nullptr;
                status = ERROR;
            }
        } break;
        default:
        {
            return ERROR;
        }
    }
    return status; // in linux alloc memory in driver...
}

FDF(uint16_t*) DaqL791::GetIOBuffer(ULONG streamID)
{
    switch(streamID)
    {
        case STREAM_ADC:
        {
            return (uint16_t*)map_inBuffer;
        } break;
        case STREAM_DAC:
        {
            return (uint16_t*)map_outBuffer;
        } break;
        default:
        {
            return nullptr;
        }
    }
}

FDF(size_t) DaqL791::GetIOBufferSize(ULONG streamID)
{
    switch(streamID)
    {
        case STREAM_ADC:
        {
            return map_inSize / sizeof(uint16_t);
        } break;
        case STREAM_DAC:
        {
            return map_outSize / sizeof(uint16_t);
        } break;
        default:
        {
            return 0;
        }
    }
}

FDF(uint32_t*) DaqL791::GetRegBuffer()
{
    return (uint32_t*)map_regBuffer;
}

FDF(size_t) DaqL791::GetRegBufferSize()
{
    return map_regSize / sizeof(uint32_t);
}

FDF(ULONG) DaqL791::SetStreamParameters(DAQ_PAR &sp, ULONG streamID)
{
    ULONG cbRet;
    ULONG status = ERROR;
    ULONG DiocCode;
    PWDAQ_PAR dp;
    switch(streamID)
    {
        case STREAM_ADC:
        {
            DiocCode = DIOC_SETUP;
            dp = (PWDAQ_PAR)&wadc_par;
        } break;
        case STREAM_DAC:
        {
            DiocCode = DIOC_SETUP_DAC;
            dp = (PWDAQ_PAR)&wdac_par;
        } break;
        default:
        {
            return status;
        }
    };
    ULONG32 OutBuf[4];
    status = !IoControl(hVxd, DiocCode,
                        dp, sizeof(WDAQ_PAR),
                        OutBuf, sizeof(OutBuf), // sizeof(PVOID) PVOID is platform dependent
                        &cbRet);
    ULONG tPages   = (ULONG)OutBuf[0];
    ULONG tFIFO    = (ULONG)OutBuf[1];
    ULONG tIrqStep = (ULONG)OutBuf[2];
    sp.Pages = tPages;    // update properties to new real values
    sp.FIFO = tFIFO;
    sp.IrqStep = tIrqStep;
    return status;
}

// end of uni stream interface
FDF(ULONG) DaqL791::InitStart()
{
    ULONG cbRet, InBuf, OutBuf, status = ERROR;
    status = !IoControl(hVxd, DIOC_INIT_SYNC,
                        &InBuf, sizeof(ULONG),
                        &OutBuf, sizeof(ULONG),
                        &cbRet);
    return status;
}

FDF(ULONG) DaqL791::Start()
{
    ULONG cbRet, InBuf, status = ERROR;
    status = !IoControl(hVxd, DIOC_START,
                        &InBuf, sizeof(ULONG),
                        DataBuffer, DataSize, // here we send data buffer parameters to lock in driver
                        &cbRet);
    return status;
}

FDF(ULONG) DaqL791::Stop()
{
    ULONG cbRet, InBuf, OutBuf;
    ULONG status = ERROR;
    status = !IoControl(hVxd, DIOC_STOP,
                        &InBuf, sizeof(ULONG),
                        &OutBuf, sizeof(ULONG),
                        &cbRet);
    return status;
}

void DaqL791::CopyDACtoWDAQ(PDAC_PAR dac, PWDAC_PAR sp)
{
    sp->s_Type = dac->s_Type;
    sp->FIFO = dac->FIFO;
    sp->IrqStep = dac->IrqStep;
    sp->Pages = dac->Pages;
    sp->AutoInit = dac->AutoInit;
    sp->dRate = dac->dRate;
    sp->Rate = dac->Rate;
    sp->DacEna = dac->DacEna;
    sp->IrqEna = dac->IrqEna;
}

void DaqL791::CopyADCtoWDAQ(PADC_PAR adc, PWADC_PAR sp)
{
    sp->s_Type = adc->s_Type;
    sp->FIFO = adc->FIFO;
    sp->IrqStep = adc->IrqStep;
    sp->Pages = adc->Pages;
    sp->AutoInit = adc->AutoInit;
    sp->dRate = adc->dRate;
    sp->dFrame = adc->dFrame;
    sp->Reserved1 = adc->Reserved1;
    sp->DigRate = adc->DigRate;
    sp->DM_Ena = adc->DM_Ena;
    sp->Rate = adc->Rate;
    sp->Frame = adc->Frame;
    sp->StartCnt = adc->StartCnt;
    sp->StopCnt = adc->StopCnt;
    sp->SynchroType = adc->SynchroType;
    sp->SynchroMode = adc->SynchroMode;
    sp->SyncThreshold = adc->SyncThreshold;
    sp->SynchroSrc = adc->SynchroSrc;
    sp->AdcIMask = adc->AdcIMask;
    sp->NCh = adc->NCh;
    for (int i = 0; i < 128; ++i) {
        sp->Chn[i] = adc->Chn[i];
    }
    sp->AdcEna = adc->AdcEna;
    sp->IrqEna = adc->IrqEna;
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
FDF(ULONG) DaqL791::ReadBoardDescr(BOARD_DESCR_L791 &pd)
{
    USHORT d;
    for (USHORT i = 0; i < sizeof(BOARD_DESCR_U); ++i) {
        if (ReadFlashWord(i, &d)) {
            return ERROR;
        }
        pdu.bi.data[i] = (UCHAR)d;
    }
    memcpy(&pd, &pdu, sizeof(BOARD_DESCR_U));
// ??? insert crc check
    return SUCCESS;
}

FDF(ULONG) DaqL791::WriteBoardDescr(BOARD_DESCR_L791 &pd, USHORT Ena)
{
    size_t i;
    int j;
    if (!Ena) {
        return ERROR;
    }
    memcpy(&pdu, &pd, sizeof(BOARD_DESCR_U));

    USHORT crc16 = 0;
    for (i = 2; i < sizeof(BOARD_DESCR_U); ++i) {
        crc16 ^= pdu.bi.data[i] << 8;
        for (j = 0; j < 8; j++) {
            if (crc16 & 0x8000) {
                crc16 = (crc16 << 0x1) ^ 0x8005;
            }
            else {
                crc16 <<= 0x1;
            }
        }
    }
    pdu.wi.data[0] = crc16;

    if (EnableFlashWrite(1)) {
        return ERROR;
    }
    for (i = 0; i < sizeof(BOARD_DESCR_U); ++i) {
        if (WriteFlashWord(i, pdu.bi.data[i])) {
            return ERROR;
        }
    }
    if (EnableFlashWrite(0)) {
        return ERROR;
    }
    return SUCCESS;
}

////////////////////////////////////////////////////////////////////////////////
// Процедура чтения слова из пользовательского ППЗУ
////////////////////////////////////////////////////////////////////////////////
FDF(ULONG) DaqL791::ReadFlashWord(USHORT Addr, PUSHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_READ_FLASH_WORD,
                      &par, sizeof(par),
                      Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL791::WriteFlashWord(USHORT Addr, USHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_WRITE_FLASH_WORD,
                      &par, sizeof(par),
                      &Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL791::EnableFlashWrite(USHORT Flag)
{
    ULONG cbRet;
    USHORT par = 0; // addr not use
    return !IoControl(hVxd, DIOC_ENABLE_FLASH_WRITE,
                      &par, sizeof(par),
                      &Flag, sizeof(USHORT),
                      &cbRet);
}

ULONG DaqL791::FillADCParameters(ADC_PAR &ap)
{
    if (ap.s_Type != ADC_PARAM) {
        return ERROR;
    }

    if (ap.dRate < 0) {
        return ERROR;
    }
    if (ap.dFrame < 0) {
        return ERROR;
    }
    double max_rate = 400.0;
    if (ap.dRate > max_rate) {
        ap.dRate = max_rate;
    }
    if (ap.NCh > 128) {
        ap.NCh = 128;
    }
    if (ap.FIFO <= 0) {
        return ERROR;
    }
    if (ap.Pages <= 0) {
        return ERROR;
    }
    if (ap.IrqStep <= 0) {
        return ERROR;
    }
    double CLOCK_OUT_L791 = pdu.par.Quartz / 1000.0; // частота в кГц
    // определим частоту работы АЦП
    double CLOCK_DIV = CLOCK_OUT_L791 / ap.dRate - 50.0;
    if (CLOCK_DIV < 0) {
        CLOCK_DIV = 0;
    }
    adc_par.Rate = (ULONG)CLOCK_DIV;
    ap.dRate = CLOCK_OUT_L791 / (CLOCK_DIV + 50.0);
    if ((1.0/(ap.dRate)) > (ap.dFrame)) {
        ap.dFrame = 1.0 / (ap.dRate);
    }
    // полный период кадра
    double delayBetweenFrames = CLOCK_OUT_L791 * ap.dFrame - 50.0;
    if (delayBetweenFrames < 0) {
        delayBetweenFrames = 0;
    }
    adc_par.Frame = (ULONG)delayBetweenFrames;
    ap.dFrame = (delayBetweenFrames + 50.0) / CLOCK_OUT_L791;
    // More
    adc_par.SynchroType = ap.SynchroType;
    adc_par.SynchroSrc = ap.SynchroSrc;
    adc_par.FIFO = ap.FIFO;
    adc_par.IrqStep = ap.IrqStep;
    adc_par.Pages = ap.Pages;
    adc_par.NCh = ap.NCh;
    for (ULONG i = 0; i < ap.NCh; ++i) {
        adc_par.Chn[i] = ap.Chn[i];
    }
    adc_par.AutoInit = ap.AutoInit;
    adc_par.IrqEna = ap.IrqEna;
    adc_par.AdcEna = ap.AdcEna;
    // make a copy of adc_par in wadc_par for C-style interface to driver in linux////////
    CopyADCtoWDAQ(&adc_par, &wadc_par.adc_par);
    return SUCCESS;
}

ULONG DaqL791::FillDACParameters(DAC_PAR &dp)
{
    if (dp.s_Type != DAC_PARAM) {
        return ERROR;
    }

    double CLOCK_OUT_L791 = pdu.par.Quartz / 1000.0; // частота в кГц
    dp.dRate = l_fabs(dp.dRate);
    if (dp.dRate > 125.0) {
        dp.dRate = 125.0;
    }
    dac_par.Rate = (ULONG)(CLOCK_OUT_L791 / (dp.dRate) - 0.5);
    if (dac_par.Rate > 16777215L) {
        dac_par.Rate = 16777215L; //2^24
    }
    if (dac_par.Rate < 159) {
        dac_par.Rate = 159L;
    }
    dp.dRate = CLOCK_OUT_L791 / (dac_par.Rate + 1.0);
    dac_par.FIFO = dp.FIFO;
    dac_par.IrqStep = dp.IrqStep;
    dac_par.Pages = dp.Pages;
    dac_par.AutoInit = dp.AutoInit;
    dac_par.DacEna = dp.DacEna;
    dac_par.IrqEna = dp.IrqEna;
    // make a copy for C style in linux
    CopyDACtoWDAQ(&dac_par, &wdac_par.dac_par);
    return SUCCESS;
}

// TTL lines, move it into driver
ULONG DaqL791::ConfigTTL(ASYNC_PAR &ap)
{
    ULONG cbRet;
    ULONG status = !IoControl(hVxd, DIOC_TTL_CFG,
                              &ap.Mode, sizeof(ULONG),
                              NULL, 0,
                              &cbRet);
    return status;
}

ULONG DaqL791::InputTTL(ASYNC_PAR &ap)
{
    ULONG cbRet;
    ULONG status = !IoControl(hVxd, DIOC_TTL_IN,
                              NULL, 0,
                              &ap.Data[0], sizeof(ULONG),
                              &cbRet);
    return status;
}

ULONG DaqL791::OutputTTL(ASYNC_PAR &ap)
{
    ULONG cbRet;
    ULONG status = !IoControl(hVxd, DIOC_TTL_OUT,
                              &ap.Data[0], sizeof(ULONG),
                              NULL, 0,
                              &cbRet);
    return status;
}

ULONG DaqL791::InputADC(ASYNC_PAR &ap)
{
    ULONG cbRet;
    ULONG Data;
    if (!IoControl(hVxd, DIOC_ADC_SAMPLE,
                   &ap.Chn[0], sizeof(ULONG),
                   &Data, sizeof(ULONG),
                   &cbRet)) {
        return ERROR;
    }
    ap.Data[0] = Data & 0xFFFF;
    return SUCCESS;
}

ULONG DaqL791::OutputDAC(ASYNC_PAR &ap)
{
    ULONG cbRet;
    ULONG par = (ap.Data[0]&0xFFF)|(ap.Chn[0]<<12)|((ap.Data[1]&0xFFF)<<16)|(ap.Chn[1]<<28)|(1<<30);
    if (!IoControl(hVxd, DIOC_DAC_OUT,
                   &par, sizeof(ULONG),
                   NULL, 0,
                   &cbRet)) {
        return ERROR;
    }
    return SUCCESS;
}

