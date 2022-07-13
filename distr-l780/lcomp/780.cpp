#include <stdio.h>
#include <string.h>

#include "../include/stubs.h"
#include "../include/ioctl.h"
#include "../include/ifc_ldev.h"
#include "../include/780.h"
#include "../include/780cmd.h"

HRESULT __stdcall DaqL780::QueryInterface(const IID& iid, void** ppv)
{
    if (iid == IID_IUnknown || iid == IID_ILDEV) {
        *ppv = static_cast<DaqL780*>(this);
    } else {
        *ppv = nullptr;
        return E_NO_INTERFACE;
    }
    reinterpret_cast<DaqL780*>(*ppv)->AddRef();
    return S_OK;
}

ULONG __stdcall DaqL780::AddRef()
{
    ++m_cRef.counter;
    return m_cRef.counter;
}

ULONG __stdcall DaqL780::Release()
{
    --m_cRef.counter;
    if (m_cRef.counter == 0) {
        delete this;
        return 0;
    }
    return m_cRef.counter;
}

// COMMON FUNCTIONS //////////////////////////////////////
FDF(ULONG) DaqL780::GetSlotParam(SLOT_PAR &slPar)
{
    memcpy(&slPar, &sl, sizeof(SLOT_PAR));
    return 0;
}

FDF(HANDLE) DaqL780::Open()
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
    return hVxd;
}

FDF(ULONG) DaqL780::Close()
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
    return status;
}

// uni stream interface
FDF(ULONG) DaqL780::RequestStreamBuffer(ULONG streamID)  //in words
{
    ULONG cbRet;
    ULONG size = 128 * 2048;
    ULONG status = ERROR;
    ULONG DiocCode;
    ULONG pb = size;
    switch(streamID)
    {
        case STREAM_ADC :
        {
            DiocCode = DIOC_SET_BUFFER_ADC;
        } break;
        case STREAM_DAC :
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
            if (map_inBuffer == MAP_FAILED) {
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

FDF(uint16_t*) DaqL780::GetIOBuffer(ULONG streamID)
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

FDF(size_t) DaqL780::GetIOBufferSize(ULONG streamID)
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

FDF(ULONG) DaqL780::SetStreamParameters(DAQ_PAR &sp, ULONG streamID)
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
    ULONG tPages    = (ULONG)OutBuf[0];
    ULONG tFIFO     = (ULONG)OutBuf[1];
    ULONG tIrqStep  = (ULONG)OutBuf[2];
    sp.Pages = tPages;    // update properties to new real values
    sp.FIFO = tFIFO;
    sp.IrqStep = tIrqStep;
    return status;
}

// end of uni stream interface
FDF(ULONG) DaqL780::InitStart()
{
    ULONG cbRet, InBuf, OutBuf, status = ERROR;
    status = !IoControl(hVxd, DIOC_INIT_SYNC,
                        &InBuf, sizeof(ULONG),
                        &OutBuf, sizeof(ULONG),
                        &cbRet);
    return status;
}

FDF(ULONG) DaqL780::Start()
{
ULONG cbRet, InBuf, status = ERROR;
    status = !IoControl(hVxd, DIOC_START,
                        &InBuf, sizeof(ULONG),
                        DataBuffer, DataSize, // here we send data buffer parameters to lock in driver
                        &cbRet);
    return status;
}

FDF(ULONG) DaqL780::Stop()
{
ULONG cbRet, InBuf, OutBuf;
ULONG status = ERROR;
    status = !IoControl(hVxd, DIOC_STOP,
                        &InBuf, sizeof(ULONG),
                        &OutBuf, sizeof(ULONG),
                        &cbRet);
    return status;
}

void DaqL780::CopyDACtoWDAQ(PDAC_PAR dac, PWDAC_PAR sp)
{
    sp->s_Type = dac->s_Type;
    sp->FIFO = dac->FIFO;
    sp->IrqStep = dac->IrqStep;
    sp->Pages = dac->Pages;
    sp->AutoInit = dac->AutoInit;
    sp->dRate = dac->dRate;
    sp->Rate = dac->Rate;
    sp->DacNumber = dac->DacNumber;
    sp->DacEna = dac->DacEna;
    sp->IrqEna = dac->IrqEna;
}

void DaqL780::CopyADCtoWDAQ(PADC_PAR adc, PWADC_PAR sp)
{
    sp->s_Type = adc->s_Type;
    sp->FIFO = adc->FIFO;
    sp->IrqStep = adc->IrqStep;
    sp->Pages = adc->Pages;
    sp->AutoInit = adc->AutoInit;
    sp->dRate = adc->dRate;
    sp->dFrame = adc->dFrame;
    sp->dScale = adc->dScale;
    sp->Rate = adc->Rate;
    sp->Frame = adc->Frame;
    sp->Scale = adc->Scale;
    sp->FPDelay = adc->FPDelay;
    sp->SynchroType = adc->SynchroType;
    sp->SynchroSensitivity = adc->SynchroSensitivity;
    sp->SynchroMode = adc->SynchroMode;
    sp->SyncChannel = adc->SyncChannel;
    sp->SyncThreshold = adc->SyncThreshold;
    sp->NCh = adc->NCh;
    for (int i = 0; i < 128; ++i) {
        sp->Chn[i] = adc->Chn[i];
    }
    sp->AdcEna = adc->AdcEna;
    sp->IrqEna = adc->IrqEna;
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
FDF(ULONG) DaqL780::ReadBoardDescr(BOARD_DESCR &pd)
{
    USHORT d;
    for (size_t i = 0; i < sizeof(BOARD_DESCR_U) / 2; ++i) {
        if (ReadFlashWord(i, &d)) {
            return ERROR;
        }
        pdu.wi.data[i] = (UCHAR)d;
    }
    memcpy(&pd, &pdu, sizeof(BOARD_DESCR_U));
// ??? insert crc check
    return SUCCESS;
}

FDF(ULONG) DaqL780::WriteBoardDescr(BOARD_DESCR &pd, USHORT Ena)
{
    memcpy(&pdu, &pd, sizeof(BOARD_DESCR_U));

// ??? insert crc check

    if (EnableFlashWrite(1)) {
        return ERROR;
    }
    for (size_t i = (size_t)(Ena ? 32 : 0); i < sizeof(BOARD_DESCR_U) / 2; ++i) {
        if (WriteFlashWord(i, pdu.wi.data[i])) {
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
FDF(ULONG) DaqL780::ReadFlashWord(USHORT Addr, PUSHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_READ_FLASH_WORD, //DIOC_GET_DM_W,
                      &par, sizeof(par),
                      Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL780::WriteFlashWord(USHORT Addr, USHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_WRITE_FLASH_WORD, //DIOC_PUT_DM_W,
                      &par, sizeof(par),
                      &Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL780::EnableFlashWrite(USHORT Flag)
{
    ULONG cbRet;
    USHORT par = 0; // addr not use
    return !IoControl(hVxd, DIOC_ENABLE_FLASH_WRITE, //DIOC_UT_DM_W,
                      &par, sizeof(par),
                      &Flag, sizeof(USHORT),
                      &cbRet);
}

ULONG DaqL780::FillADCParameters(ADC_PAR &ap)
{
    if (ap.s_Type != ADC_PARAM) {
        return ERROR;
    }

    // Type of board
    enum { L761, L780, L783 };
    int BN;
    if (pdu.par.BrdName[0] != 'L' || pdu.par.BrdName[4] != 0) {
        return ERROR;
    }
    if (pdu.par.BrdName[1] != '7') {
        return NOT_SUPPORTED;
    }
    if (pdu.par.BrdName[2] == '6' && pdu.par.BrdName[3] == '1') {
        BN = L761;
    }
    else if (pdu.par.BrdName[2] == '8' && pdu.par.BrdName[3] == '0') {
        BN = L780;
    }
    else if (pdu.par.BrdName[2] == '8' && pdu.par.BrdName[3] == '3') {
        BN = L783;
    }
    else {
        return NOT_SUPPORTED;
    }

    if (ap.dRate < 0) {
        return ERROR;
    }
    if (ap.dFrame < 0) {
        return ERROR;
    }
    double max_rate[] = { 125.0, 400.0, 3300.0 };
    if (ap.dRate > max_rate[BN]) {
        ap.dRate = max_rate[BN];
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
    double QUARTZ_FREQUENCY = pdu.par.Quartz / 1000.0; // частота в кГц
    double DSP_CLOCK_OUT_PLX = 2.0 * QUARTZ_FREQUENCY;
    if (DSP_CLOCK_OUT_PLX <= 0) {
        return ERROR;
    }
    if (ap.dRate < 0.1) {
        ap.dRate = 0.1;
    }
    double delayBetweenFrames;
    const double delta_rate = 0.1;          // частота с точностью 0.1 мкс
    switch (BN)
    {
        case L780:
        case L783:
        {
            double SCLOCK_DIV;
            // частота сбора в единицах SCLOCK_DIV SPORT DSP
            SCLOCK_DIV = DSP_CLOCK_OUT_PLX / (2.0 * ap.dRate) - 0.5;
            if (SCLOCK_DIV > 65500.0) {
                SCLOCK_DIV = 65500.0;
            }
            adc_par.Rate = (USHORT)SCLOCK_DIV;
            ap.dRate = DSP_CLOCK_OUT_PLX / (2.0 * (adc_par.Rate + 1));
            adc_par.FPDelay = (USHORT)(DSP_CLOCK_OUT_PLX / ap.dRate + 50.0 * delta_rate + 0.5);  // WTF?
            // величина задержки в единицах SCLOCK SPORT DSP
            if (ap.dRate > 1000.0) {
                ap.dFrame = 0; //  no interframe at freq up 1000 kHz
            }
            if (1.0 / ap.dRate > ap.dFrame) {
                ap.dFrame = 1.0 / ap.dRate;
            }
            //
            delayBetweenFrames = ap.dFrame * ap.dRate - 0.5;
            if (delayBetweenFrames > 65500.0) {
                delayBetweenFrames = 65500.0;
            }
            adc_par.Frame = (USHORT)delayBetweenFrames;
            ap.dFrame = (adc_par.Frame + 1) / (ap.dRate);
        } break;
        case L761:
        {
            // частота сбора в единицах delta_rate
            double rate = 1000. / (ap.dRate * delta_rate) + 0.5;
            if (rate > 65500.0) {
                rate = 65500.0;
            }
            adc_par.Rate = (USHORT)rate;
            ap.dRate = 1000.0 / (adc_par.Rate * delta_rate);
            adc_par.FPDelay = (USHORT)(DSP_CLOCK_OUT_PLX / ap.dRate + 50.0 * delta_rate + 0.5);  // WTF?
            // установим величину межкадровой задержки в мс
            if (1.0 / ap.dRate > ap.dFrame) {
                ap.dFrame = 1.0 / ap.dRate;
            }
            if (ap.dFrame > delta_rate * 65535.0 / 1000.0) {
                ap.dFrame = delta_rate * 65535.0 / 1000.0;
            }
            delayBetweenFrames = 1000.0 * (ap.dFrame) / delta_rate + 0.5;     // величина задержки  в единицах delta_rate
            adc_par.Frame = (USHORT)delayBetweenFrames;
            ap.dFrame = adc_par.Frame * delta_rate / 1000.0; //-1./(*Rate);
        } break;
        default:
        {
            return ERROR;
        }
    }
    adc_par.Scale = 0;
    // More
    adc_par.SynchroType = ap.SynchroType;
    adc_par.SynchroSensitivity = ap.SynchroSensitivity;
    adc_par.SynchroMode = ap.SynchroMode;
    adc_par.SyncChannel = ap.SyncChannel;
    adc_par.SyncThreshold = ap.SyncThreshold;
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
    // make a copy of adc_par in wadc_par for C-style interface to driver in linux ////////
    CopyADCtoWDAQ(&adc_par, &wadc_par.adc_par);
    return SUCCESS;
}

ULONG DaqL780::FillDACParameters(DAC_PAR &dp)
{
    if (dp.s_Type != DAC_PARAM) {
        return ERROR;
    }

    USHORT d1;
    if (GetWord_DM(DAC_SCLK_DIV_PLX, &d1)) {
        return ERROR;
    }
    double DSP_CLOCK_OUT_PLX = 2.0 * pdu.par.Quartz / 1000.0;
    double SCLK = DSP_CLOCK_OUT_PLX/(2. * (1. + d1));
    dp.dRate = l_fabs(dp.dRate);
    if (dp.dRate > 125.0) {
        dp.dRate = 125.0;
    }
    if (dp.dRate < SCLK / 65535.0) {
        dp.dRate = SCLK / 65535.0;
    }
    USHORT RFS_DIV = (USHORT)(SCLK / dp.dRate - 0.5);
    dp.dRate = SCLK / (RFS_DIV + 1.0);
    dac_par.dRate = dp.dRate;
    dac_par.Rate = RFS_DIV;
    dac_par.FIFO = dp.FIFO;
    dac_par.IrqStep = dp.FIFO;  // WTF? Why not IrqStep?
    dac_par.Pages = (dp.Pages < 2) ? 2 : dp.Pages;
    dac_par.AutoInit = dp.AutoInit;
    dac_par.DacEna = dp.DacEna;
    dac_par.DacNumber = dp.DacNumber;
    dac_par.IrqEna = dp.IrqEna;
    // make a copy for C style in linux
    CopyDACtoWDAQ(&dac_par, &wdac_par.dac_par);
    return SUCCESS;
}

// TTL lines, move it into driver
ULONG DaqL780::ConfigTTL(ASYNC_PAR &ap)
{
    if (sl.BoardType != PCIC) {
        return NOT_SUPPORTED;
    }
    if (PutWord_DM(ENABLE_TTL_OUT_PLX, (USHORT)ap.Mode)) {
        return ERROR;
    }
    if (SendCommand(cmENABLE_TTL_OUT_PLX)) {
        return ERROR;
    }
    return SUCCESS;
}

ULONG DaqL780::InputTTL(ASYNC_PAR &ap)
{
    USHORT data;
    if (SendCommand(cmTTL_IN_PLX)) {
        return ERROR;
    }
    if (GetWord_DM(TTL_IN_PLX, &data)) {
        return ERROR;
    }
    ap.Data[0] = data;
    return SUCCESS;
}

ULONG DaqL780::OutputTTL(ASYNC_PAR &ap)
{
    if (PutWord_DM(TTL_OUT_PLX, (USHORT)ap.Data[0])) {
        return ERROR;
    }
    if (SendCommand(cmTTL_OUT_PLX)) {
        return ERROR;
    }
    return SUCCESS;
}

ULONG DaqL780::InputADC(ASYNC_PAR &ap)
{
    USHORT data;
    if (PutWord_DM(ADC_CHANNEL_PLX, (USHORT)ap.Chn[0])) {
        return ERROR;
    }
    if (SendCommand(cmADC_SAMPLE_PLX)) {
        return ERROR;
    }
    if (GetWord_DM(ADC_SAMPLE_PLX, &data)) {
        return ERROR;
    }
    ap.Data[0] = data;
    return SUCCESS;
}

ULONG DaqL780::OutputDAC(ASYNC_PAR &ap)
{
    if (ap.Mode > 1) {
        return ERROR;
    }
    USHORT dac_value = (USHORT)((ap.Data[0])&0xFFF);
    dac_value |= (ap.Mode<<12);
    dac_value |= (1<<15); // for 783
    if (PutWord_DM(DAC_VALUE_PLX, dac_value)) {
        return ERROR;
    }
    if (!strcmp(pdu.par.BrdName, "L783")) {
        if (SendCommand(0)) {
            return ERROR;
        }
    }
    USHORT tmp;
    ULONG TO = 1000000; // timeout
    do {
        if (GetWord_DM(DAC_VALUE_PLX, &tmp)) {
            return ERROR;
        }
    }
    while ((tmp&(1<<15)) && TO--);
    if (TO) {
        return SUCCESS;
    }
    else {
        return ERROR;
    }
}

// IDMA with  PLX9050 PCI chip /////////////////////////////////////////////////
FDF(ULONG) DaqL780::SendCommand(USHORT Cmd)
{
    ULONG cbRet;
    USHORT data = 0;
    USHORT par = Cmd;
    return !IoControl(hVxd, DIOC_COMMAND_PLX,
                      &par, sizeof(par),
                      &data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL780::GetWord_DM(USHORT Addr, PUSHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_GET_DM_A, //DIOC_GET_DM_W,
                      &par, sizeof(par),
                      Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL780::PutWord_DM(USHORT Addr, USHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_PUT_DM_A, //DIOC_PUT_DM_W,
                      &par, sizeof(par),
                      &Data, sizeof(USHORT),
                      &cbRet);
}

FDF(ULONG) DaqL780::PutWord_PM(USHORT Addr, ULONG Data)  // unused
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_PUT_PM_A,
                      &par, sizeof(par),
                      &Data, sizeof(ULONG),
                      &cbRet);
}

FDF(ULONG) DaqL780::GetWord_PM(USHORT Addr, PULONG Data)  // unused
{
    ULONG cbRet;
    USHORT par = Addr;
    return !IoControl(hVxd, DIOC_GET_PM_A,
                      &par, sizeof(par),
                      Data, sizeof(ULONG),
                      &cbRet);
}

FDF(ULONG) DaqL780::PutArray_DM(USHORT Addr, ULONG Count, PUSHORT Data)
{
    ULONG cbRet;
    USHORT par = Addr;
    ULONG len = 1024;
    int status;
    do
    {
        if (Count < len) {
            len = Count;
        }
        status = IoControl(hVxd, DIOC_PUT_DM_A,
                           &par, sizeof(par),
                           Data, len * sizeof(USHORT),
                           &cbRet);
        if (!status) {
            break;
        }
        Data += len;
        par += (USHORT)len;
        Count -= len;
    } while(Count);
    return !status;
}

FDF(ULONG) DaqL780::GetArray_DM(USHORT Addr, ULONG Count, PUSHORT Data)  // unused
{
    ULONG cbRet;
    USHORT par = Addr;
    ULONG len = 1024;
    int status;
    do
    {
        if (Count < len) {
            len = Count;
        }
        status = IoControl(hVxd, DIOC_GET_DM_A,
                           &par, sizeof(par),
                           Data, len * sizeof(USHORT),
                           &cbRet);
        if (!status) {
            break;
        }
        Data += len;
        par += (USHORT)len;
        Count -= len;
    } while(Count);
    return !status;
}

FDF(ULONG) DaqL780::PutArray_PM(USHORT Addr, ULONG Count, PULONG Data)  // unused
{
    ULONG cbRet;
    USHORT par = Addr;
    ULONG len = 1024;
    int status;
    do
    {
        if (Count < len) len = Count;
        status = IoControl(hVxd, DIOC_PUT_PM_A,
                           &par, sizeof(par),
                           Data, len * sizeof(ULONG),
                           &cbRet);
        if (!status) {
            break;
        }
        Data+= len;
        par+= (USHORT)len;
        Count-= len;
    } while(Count);
    return !status;
}

FDF(ULONG) DaqL780::GetArray_PM(USHORT Addr, ULONG Count, PULONG Data)  // unused
{
    ULONG cbRet;
    USHORT par = Addr;
    ULONG len = 1024;
    int status;
    do
    {
        if (Count < len) len = Count;
        status = IoControl(hVxd, DIOC_GET_PM_A,
                           &par, sizeof(par),
                           Data, len * sizeof(ULONG),
                           &cbRet);
        if (!status) {
            break;
        }
        Data+= len;
        par+= (USHORT)len;
        Count-= len;
    } while(Count);
    return !status;
}

FDF(ULONG) DaqL780::Test()
{
    USHORT d1;
    if (GetWord_DM(TMODE1_PLX, &d1)) {
        return ERROR;
    }
    USHORT d2;
    if (GetWord_DM(TMODE2_PLX, &d2)) {
        return ERROR;
    }
    if ((d1 != 0x5555)||(d2 != 0xAAAA)) {
        return ERROR;
    }
    else
    {
        if (PutWord_DM(TEST_LOAD_PLX, 0x77bb)) {
            return ERROR;
        }
        int TO = 10000000; //////////TimeOUT; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        do
        {
            if (GetWord_DM(READY_PLX, &d1)) {
                return ERROR;
            }
        } while(!d1 && (TO--));
        if (TO == -1) {
            return ERROR;
        }
        if (SendCommand(cmTEST_PLX)) {
            return ERROR;
        }
        if (GetWord_DM(TEST_LOAD_PLX, &d1)) {
            return ERROR;
        }
        if (d1 != 0xAA55) {
            return ERROR;
        }
    }
    return SUCCESS;
}

FDF(ULONG) DaqL780::EnableCorrection(USHORT Ena)
{
// load
    if (PutArray_DM(ZERO_PLX, 4, &(pdu.par.ADCFactor[0]))) {
        return ERROR;
    }
    if (PutArray_DM(SCALE_PLX, 4, &(pdu.par.ADCFactor[4]))) {
        return ERROR;
    }
    // enable or disable
    if (PutWord_DM(CORRECTION_ENABLE_PLX, Ena)) {
        return ERROR;
    }
    return SUCCESS;
}

FDF(ULONG) DaqL780::LoadBios(char *FileName)
{
    USHORT *LCBios;
    FILE   *BiosFile;
    size_t  NBytes;
    PUCHAR  BiosCode = nullptr;
    USHORT *Tmp;
    USHORT  Count;
    CHAR    FName[255];
    ULONG   cbRet;

    if (!FileName) {
        BOARD_DESCR pd;
        ReadBoardDescr(pd);
        snprintf(FName, 255, "%s.bio", pd.BrdName);
    }
    else {
        snprintf(FName, 255, "%s.bio", FileName);
    }
    printf("loading %s\n", FName);

    int status = ERROR;
    do {  // single shot
        BiosFile = fopen(FName, "rb");
        if (!BiosFile) {
            break;
        }
        fseek(BiosFile, 0, SEEK_END);
        NBytes = ftell(BiosFile);
        rewind(BiosFile);

        BiosCode = new UCHAR[NBytes + 2];
        if (fread(BiosCode, 1, NBytes, BiosFile) != NBytes) {
            break;
        }
        LCBios = (PUSHORT)BiosCode;

        // RESET для ADSP-218x // переписать как ioctl
        if (!IoControl(hVxd, DIOC_RESET_PLX, NULL, 0, NULL, 0, &cbRet)) {
            break;
        }

        // Load DSP DM word
        Tmp = LCBios + LCBios[0] + 1; // calculate DM address &LCBios[0]+LCBios[0]
        Count = *Tmp++;           // counter

        if (PutArray_DM(0x2000, Count, Tmp)) {
            break;
        }
        if (PutWord_DM(BOARD_REVISION_PLX, (USHORT)(sl.BoardType == PCIC ? 'C' : 'B'))) {
            break;  // revision
        }
        // Load DSP PM word
        Tmp = LCBios + 3;
        Count = (USHORT)(LCBios[0]-2);
        if (PutArray_PM(0x0001, Count / 2, (PULONG)Tmp)) {
            break;
        }
        // Load last DSP PM word
        ULONG d2 = *((PULONG)&LCBios[1]);
        if (PutWord_PM(0x0000, d2)) {
            break;
        }
        // rewrite изменил драйвера пришлось переписать ()
        if (Test() != SUCCESS) {
            break;
        }
        if (!IoControl(hVxd, DIOC_SET_DSP_TYPE, NULL, 0, NULL, 0, &cbRet)) {
            break; // (SUCCESS)
        }
        if (PutWord_DM(ADC_ENABLE_PLX,0)) {
            break; // stop adc...
        }
        status = SUCCESS;
    } while (status == ERROR);
    // освободим память и выйдем из функции
    if (BiosCode) {
        delete[] BiosCode;
    }
    if (BiosFile) {
        fclose(BiosFile);
    }
    return status;
}
