#ifndef __VXDAPI_IOCTL
#define __VXDAPI_IOCTL 1

// Board Type macro definitions
#define NONE  0 // no board in slot
#define PCIA  5 // PCI rev A board
#define PCIB  6 // PCI rev B board
#define PCIC 14

// ERROR CODES
#define SUCCESS 0
#define NOT_SUPPORTED 1
#define ERROR 2
#define ERROR_NO_BOARD 3
#define ERROR_IN_USE 4

// define s_Type for FillDAQParameters
#define ADC_PARAM 1
#define DAC_PARAM 2

#define ASYNC_ADC_CFG 3
#define ASYNC_TTL_CFG 4
#define ASYNC_DAC_CFG 5

#define ASYNC_ADC_INP 6
#define ASYNC_TTL_INP 7

#define ASYNC_TTL_OUT 8
#define ASYNC_DAC_OUT 9

#define STREAM_ADC 1
#define STREAM_DAC 2
#define STREAM_TTLIN 3
#define STREAM_TTLOUT 4

#define EVENT_ADC_BUF 1
#define EVENT_DAC_BUF 2

#define EVENT_ADC_OVF 3
#define EVENT_ADC_FIFO 4
#define EVENT_DAC_USER 5
#define EVENT_DAC_UNF 6
#define EVENT_PWR_OVR 7

#pragma pack(1)

// internal
typedef struct _PORT_PARAM_
{
    ULONG port;
    ULONG datatype;
} PORT_PAR, *PPORT_PAR;

// exported
typedef struct __SLOT_PARAM
{
    ULONG Base;
    ULONG BaseL;
    ULONG Base1;
    ULONG BaseL1;
    ULONG Mem;
    ULONG MemL;
    ULONG Mem1;
    ULONG MemL1;
    ULONG Irq;
    ULONG BoardType;
    ULONG DSPType;
    ULONG Dma;
    ULONG DmaDac;
    ULONG DTA_REG;
    ULONG IDMA_REG;
    ULONG CMD_REG;
    ULONG IRQ_RST;
    ULONG DTA_ARRAY;
    ULONG RDY_REG;
    ULONG CFG_REG;
} SLOT_PAR, *PSLOT_PAR;


typedef struct _DAQ_PARAM_
{
    ULONG s_Type;
    ULONG FIFO;
    ULONG IrqStep;
    ULONG Pages;
} DAQ_PAR, *PDAQ_PAR;


// descr async i/o routines for adc,dac & ttl
typedef struct _ASYNC_PARAM_: public DAQ_PAR
{
    double dRate;
    ULONG Rate;
    ULONG NCh;
    ULONG Chn[128];
    ULONG Data[128];
    ULONG Mode;
} ASYNC_PAR, *PASYNC_PAR;

typedef struct _DAC_PARAM: public DAQ_PAR
{
    ULONG AutoInit;

    double dRate;
    ULONG Rate;

    ULONG IrqEna;
    ULONG DacEna;
    ULONG DacNumber;
} DAC_PAR, *PDAC_PAR;

typedef struct W_DAC_PARAM
{
    ULONG s_Type;
    ULONG FIFO;
    ULONG IrqStep;
    ULONG Pages;

    ULONG AutoInit;

    double dRate;
    ULONG Rate;

    ULONG IrqEna;
    ULONG DacEna;
    ULONG DacNumber;
} WDAC_PAR, *PWDAC_PAR;

typedef struct _ADC_PARAM: public DAQ_PAR
{
    ULONG AutoInit;

    double dRate;
    double dFrame;
    double dScale;
    ULONG Rate;
    ULONG Frame;
    ULONG Scale;
    ULONG FPDelay;

    ULONG SynchroType;
    ULONG SynchroSensitivity;
    ULONG SynchroMode;
    ULONG SyncChannel;
    ULONG SyncThreshold;

    ULONG NCh;
    ULONG Chn[128];
    ULONG IrqEna;
    ULONG AdcEna;
} ADC_PAR, *PADC_PAR;

typedef struct W_ADC_PARAM
{
    ULONG s_Type;
    ULONG FIFO;
    ULONG IrqStep;
    ULONG Pages;

    ULONG AutoInit;

    double dRate;
    double dFrame;
    double dScale;
    ULONG Rate;
    ULONG Frame;
    ULONG Scale;
    ULONG FPDelay;

    ULONG SynchroType;
    ULONG SynchroSensitivity;
    ULONG SynchroMode;
    ULONG SyncChannel;
    ULONG SyncThreshold;

    ULONG NCh;
    ULONG Chn[128];
    ULONG IrqEna;
    ULONG AdcEna;
} WADC_PAR, *PWADC_PAR;

typedef struct __USHORT_IMAGE
{
    USHORT data[512];
} USHORT_IMAGE, *PUSHORT_IMAGE;


typedef union W_DAQ_PARAM
{
    WDAC_PAR dac_par;
    WADC_PAR adc_par;
} WDAQ_PAR, *PWDAQ_PAR;


typedef struct __BOARD_DESCR
{
    char SerNum[9];
    char BrdName[5];
    char Rev;
    char DspType[5];
    unsigned int Quartz;
    USHORT IsDacPresent;
    USHORT _Reserved[7];
    USHORT ADCFactor[8];
    USHORT DACFactor[4];
    USHORT Custom[32];
} BOARD_DESCR, *PBOARD_DESCR;

typedef struct __WORD_IMAGE
{
    USHORT data[64];
} WORD_IMAGE, *PWORD_IMAGE;

typedef struct __BYTE_IMAGE
{
    UCHAR data[128];
} BYTE_IMAGE, *PBYTE_IMAGE;

typedef union __BOARD_DESCR_U
{
    BOARD_DESCR par;

    WORD_IMAGE wi;
    BYTE_IMAGE bi;
} BOARD_DESCR_U, *PBOARD_DESCR_U;

// ioctl struct for ioctl access...
typedef struct __IOCTL_BUFFER
{
    size_t inSize;  // size in bytes
    size_t outSize; // size in bytes
    unsigned char inBuffer[4096];
    unsigned char outBuffer[4096];
} IOCTL_BUFFER, *PIOCTL_BUFFER;

#pragma pack()

#define DIOC_SETUP                   _IOWR(0x97,  1, IOCTL_BUFFER)
#define DIOC_START                   _IOWR(0x97,  3, IOCTL_BUFFER)
#define DIOC_STOP                    _IOWR(0x97,  4, IOCTL_BUFFER)
#define DIOC_OUTP                    _IOWR(0x97,  5, IOCTL_BUFFER)
#define DIOC_INP                     _IOWR(0x97,  6, IOCTL_BUFFER)
#define DIOC_OUTM                    _IOWR(0x97,  7, IOCTL_BUFFER)
#define DIOC_INM                     _IOWR(0x97,  8, IOCTL_BUFFER)
#define DIOC_SET_BUFFER_ADC          _IOWR(0x97,  9, IOCTL_BUFFER)
#define DIOC_INIT_SYNC               _IOWR(0x97, 12, IOCTL_BUFFER)
#define DIOC_SEND_COMMAND            _IOWR(0x97, 15, IOCTL_BUFFER)
#define DIOC_COMMAND_PLX             _IOWR(0x97, 16, IOCTL_BUFFER)
#define DIOC_PUT_DM_A                _IOWR(0x97, 19, IOCTL_BUFFER)
#define DIOC_GET_DM_A                _IOWR(0x97, 20, IOCTL_BUFFER)
#define DIOC_PUT_PM_A                _IOWR(0x97, 21, IOCTL_BUFFER)
#define DIOC_GET_PM_A                _IOWR(0x97, 22, IOCTL_BUFFER)
#define DIOC_GET_PARAMS              _IOWR(0x97, 23, IOCTL_BUFFER)
#define DIOC_SET_DSP_TYPE            _IOWR(0x97, 24, IOCTL_BUFFER)
#define DIOC_SET_BUFFER_DAC          _IOWR(0x97, 25, IOCTL_BUFFER)
#define DIOC_SETUP_DAC               _IOWR(0x97, 26, IOCTL_BUFFER)
#define DIOC_READ_FLASH_WORD         _IOWR(0x97, 27, IOCTL_BUFFER)
#define DIOC_WRITE_FLASH_WORD        _IOWR(0x97, 28, IOCTL_BUFFER)
#define DIOC_ENABLE_FLASH_WRITE      _IOWR(0x97, 29, IOCTL_BUFFER)
#define DIOC_ADC_SAMPLE              _IOWR(0x97, 35, IOCTL_BUFFER)
#define DIOC_LOAD_BIOS               _IOWR(0x97, 36, IOCTL_BUFFER)

#define DIOC_TTL_IN                  _IOWR(0x97, 37, IOCTL_BUFFER)
#define DIOC_TTL_OUT                 _IOWR(0x97, 38, IOCTL_BUFFER)
#define DIOC_TTL_CFG                 _IOWR(0x97, 39, IOCTL_BUFFER)
#define DIOC_DAC_OUT                 _IOWR(0x97, 40, IOCTL_BUFFER)

#define DIOC_RESET_PLX               _IOWR(0x97, 41, IOCTL_BUFFER)

#define DIOC_WAIT_COMPLETE           _IOWR(0x97, 42, IOCTL_BUFFER)
#define DIOC_WAIT_COMPLETE_DAC       _IOWR(0x97, 43, IOCTL_BUFFER)

#define DIOC_SEND_BIOS               _IOWR(0x97, 44, IOCTL_BUFFER)

#define DIOC_WAIT_COMPLETE_ADC_OVF   _IOWR(0x97, 45, IOCTL_BUFFER)
#define DIOC_WAIT_COMPLETE_ADC_BUF   _IOWR(0x97, 46, IOCTL_BUFFER)
#define DIOC_WAIT_COMPLETE_DAC_UNF   _IOWR(0x97, 47, IOCTL_BUFFER)
#define DIOC_WAIT_COMPLETE_PWR       _IOWR(0x97, 48, IOCTL_BUFFER)
#define DIOC_ENABLE_CORRECTION       _IOWR(0x97, 50, IOCTL_BUFFER)

#endif
