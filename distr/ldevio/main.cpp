#define LCOMP_LINUX 1

#define LCOMP_LINUX 1

#include <atomic_ops.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

typedef struct {
	volatile AO_t counter;
} atomic_t;

typedef void* LPVOID;
typedef void* PVOID;
typedef int HANDLE;
typedef void* HMODULE;
typedef void* HINSTANCE;
typedef char CHAR, *PCHAR;
typedef unsigned char UCHAR, *PUCHAR;
typedef unsigned int ULONG, *PULONG;
typedef int LONG, *PLONG;
typedef short SHORT, *PSHORT;
typedef unsigned short USHORT, *PUSHORT;
typedef int BOOL;

typedef LONG HRESULT;

#define TRUE 1
#define FALSE 0
#define INVALID_HANDLE_VALUE (static_cast<HANDLE>(-1))

#define ERROR_FILE_NOT_FOUND 2L
#define ERROR_ACCESS_DENIED 5L

// Board Type macro definitions

//#define LABVIEW_FW

#define PCIA 5 // PCI rev A board
#define PCIB 6 // PCI rev B board
#define PCIC 14

// ERROR CODES
#define L_SUCCESS 0
#define L_NOTSUPPORTED 1
#define L_ERROR 2
#define L_ERROR_NOBOARD 3
#define L_ERROR_INUSE 4

// define s_Type for FillDAQparameters
#define L_ADC_PARAM 1

#define L_ASYNC_ADC_CFG 3

#define L_STREAM_ADC 1

#pragma pack(1)

// internal
typedef struct _PORT_PARAM_ {
	ULONG port;
	ULONG datatype;
} PORT_PAR, *PPORT_PAR;

// exported
typedef struct __SLOT_PARAM {
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

typedef struct _DAQ_PARAM_ {
	ULONG s_Type;
	ULONG FIFO;
	ULONG IrqStep;
	ULONG Pages;
} DAQ_PAR, *PDAQ_PAR;

typedef struct W_DAC_PARAM_U_0 {
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
} WDAC_PAR_0;

typedef struct _ADC_PARAM_ : public DAQ_PAR {
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
	ULONG AdChannel;
	ULONG AdThreshold;

	ULONG NCh;
	ULONG Chn[128];
	ULONG IrqEna;
	ULONG AdcEna;
} ADC_PAR, *PADC_PAR;

typedef struct W_ADC_PARAM_U_0 {
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
	ULONG AdChannel;
	ULONG AdThreshold;
	ULONG NCh;
	ULONG Chn[128];
	ULONG IrqEna;
	ULONG AdcEna;
} WADC_PAR_0, *PWADC_PAR_0;

typedef struct __USHORT_IMAGE {
	USHORT data[512];
} USHORT_IMAGE, *PUSHORT_IMAGE;

typedef union W_DAQ_PARAM_ {
	WDAC_PAR_0 t1;
	WADC_PAR_0 t3;
	USHORT_IMAGE wi;
} WDAQ_PAR, *PWDAQ_PAR;

//exported
typedef struct __PLATA_DESCR {
	char SerNum[9];
	char BrdName[5];
	char Rev;
	char DspType[5];
	unsigned int Quartz;
	USHORT IsDacPresent;
	USHORT Reserv1[7];
	USHORT ADCFactor[8];
	USHORT Custom[36];
} PLATA_DESCR;

typedef struct __WORD_IMAGE {
	USHORT data[64];
} WORD_IMAGE, *PWORD_IMAGE;

typedef struct __BYTE_IMAGE {
	UCHAR data[128];
} BYTE_IMAGE, *PBYTE_IMAGE;

typedef union __PLATA_DESCR_U {
	PLATA_DESCR t1;
	WORD_IMAGE wi;
	BYTE_IMAGE bi;
} PLATA_DESCR_U, *PPLATA_DESCR_U;

// ioctl struct for ioctl access...
typedef struct __IOCTL_BUFFER {
	size_t inSize; // size in bytes
	size_t outSize; // size in bytes
	unsigned char inBuffer[4096];
	unsigned char outBuffer[4096];
} IOCTL_BUFFER, *PIOCTL_BUFFER;

#pragma pack()

#define DIOC_SETUP _IOWR(0x97, 1, IOCTL_BUFFER)
#define DIOC_START _IOWR(0x97, 3, IOCTL_BUFFER)
#define DIOC_STOP _IOWR(0x97, 4, IOCTL_BUFFER)
#define DIOC_SETBUFFER _IOWR(0x97, 9, IOCTL_BUFFER)
#define DIOC_INIT_SYNC _IOWR(0x97, 12, IOCTL_BUFFER)
#define DIOC_COMMAND_PLX _IOWR(0x97, 16, IOCTL_BUFFER)
#define DIOC_PUT_DM_A _IOWR(0x97, 19, IOCTL_BUFFER)
#define DIOC_GET_DM_A _IOWR(0x97, 20, IOCTL_BUFFER)
#define DIOC_PUT_PM_A _IOWR(0x97, 21, IOCTL_BUFFER)
#define DIOC_GET_PM_A _IOWR(0x97, 22, IOCTL_BUFFER)
#define DIOC_GET_PARAMS _IOWR(0x97, 23, IOCTL_BUFFER)
#define DIOC_SET_DSP_TYPE _IOWR(0x97, 24, IOCTL_BUFFER)
#define DIOC_READ_FLASH_WORD _IOWR(0x97, 27, IOCTL_BUFFER)
#define DIOC_WRITE_FLASH_WORD _IOWR(0x97, 28, IOCTL_BUFFER)
#define DIOC_ENABLE_FLASH_WRITE _IOWR(0x97, 29, IOCTL_BUFFER)
#define DIOC_RESET_PLX _IOWR(0x97, 41, IOCTL_BUFFER)

// some math function
#define l_fabs(x) ((x >= 0) ? x : (-(x)))
#define l_ceil(x) ((double)((int)(x) + 1))

static void atomic_inc(atomic_t* v)
{
	AO_fetch_and_add1(&v->counter);
}

static void atomic_dec(atomic_t* v)
{
	AO_fetch_and_sub1(&v->counter);
}

// 0 sucess 1 error

BOOL LCloseHandle(HANDLE hDevice)
{
	return close(hDevice);
}

HANDLE LCreateFile(const char* szDrvName)
{
	return open(szDrvName, O_RDWR);
}

// in linux define handle as int
// maximum read/write size is 4096 byte
// see source for limitations...
BOOL LDeviceIoControl(HANDLE hDevice,
	ULONG dwIoControlCode,
	LPVOID lpInBuffer,
	ULONG nInBufferSize,
	LPVOID lpOutBuffer,
	ULONG nOutBufferSize,
	size_t& lpBytesReturned)
{
	BOOL status = FALSE;
	IOCTL_BUFFER ibuf;
	unsigned int i;
	do {
		if (nInBufferSize > 4096) {
			printf("err");
			break;
		}
		if (nOutBufferSize > 4096) {
			printf("err1");
			break;
		}

		memset(&ibuf, 0, sizeof(ibuf));

		if (lpOutBuffer) {
			ibuf.outSize = nOutBufferSize;
			for (i = 0; i < nOutBufferSize; i++) {
				ibuf.outBuffer[i] = reinterpret_cast<PUCHAR>(lpOutBuffer)[i];
			}
		}

		if (lpInBuffer) {
			for (i = 0; i < nInBufferSize; i++) {
				ibuf.inBuffer[i] = reinterpret_cast<PUCHAR>(lpInBuffer)[i];
			}
			ibuf.inSize = nInBufferSize;
		}

		if (ioctl(static_cast<int>(hDevice), dwIoControlCode, &ibuf)) {
			break;
		}
		if (lpOutBuffer) {
			for (i = 0; i < nOutBufferSize; i++) {
				reinterpret_cast<PUCHAR>(lpOutBuffer)[i] = ibuf.outBuffer[i];
			}
		}
		lpBytesReturned = ibuf.outSize;
		status = TRUE;
	} while (status == FALSE);
	return status;
}

struct LUnknown {
	virtual void QueryInterface(void** ppv) = 0;
	virtual size_t AddRef() = 0;
	virtual size_t Release() = 0;
	virtual ~LUnknown() {}
};

class DaqL780 final : public LUnknown {
public:
	void QueryInterface(void **ppv);
	size_t AddRef();
	size_t Release();

	ULONG GetSlotParam(PSLOT_PAR slPar);

	// Common functions
	HANDLE OpenLDevice();
	LONG CloseLDevice();

	ULONG SetParametersStream(PDAQ_PAR sp, ULONG* UsedSize, USHORT** Data, ULONG** Sync);
	ULONG RequestBufferStream(ULONG* Size); //in words
	ULONG FillDAQparameters(PADC_PAR sp);

	// two step must be
	ULONG InitStartLDevice();
	ULONG StartLDevice();
	ULONG StopLDevice();

	DaqL780(ULONG Slot)
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

	~DaqL780() {}

	// service function
	void CopyDAQtoWDAQ(ADC_PAR* adc_par, WADC_PAR_0* wadc_par_t3);

	// Base functions
	ULONG GetWord_DM(USHORT Addr, PUSHORT Data);
	ULONG PutWord_DM(USHORT Addr, USHORT Data);
	ULONG PutWord_PM(USHORT Addr, ULONG Data);
	ULONG GetWord_PM(USHORT Addr, PULONG Data);

	ULONG GetArray_DM(USHORT Addr, ULONG Count, PUSHORT Data);
	ULONG PutArray_DM(USHORT Addr, ULONG Count, PUSHORT Data);
	ULONG PutArray_PM(USHORT Addr, ULONG Count, PULONG Data);
	ULONG GetArray_PM(USHORT Addr, ULONG Count, PULONG Data);

	ULONG SendCommand(USHORT cmd);

	// Service functions
	ULONG PlataTest();

	ULONG EnableCorrection(USHORT Ena);

	ULONG LoadBios(const char* FileName);

	ULONG ReadFlashWord(USHORT Addr, PUSHORT Data);
	ULONG ReadPlataDescr(LPVOID pd);
	ULONG EnableFlashWrite(USHORT Flag);

	ULONG FillADCparameters(PADC_PAR sp);

private:
	atomic_t m_cRef;
	ULONG m_Slot;

protected:
	//  this is DEV_ALL
	HANDLE hVxd;

	HANDLE hEvent; // for ovelapped DIOC_START under NT

	SLOT_PAR sl;

	ADC_PAR adc_par; // to fill with FillDAQparam

	// add for C-style driver in Linux
	WDAQ_PAR wadc_par;

	PLATA_DESCR_U pdu;

	ULONG* DataBuffer; // pointer for data buffer for busmaster boards in windows
	ULONG DataSize; // size of buffer

	// size and pointers for data buffers in Linux
	size_t map_inSize;
	void* map_inBuffer;
	size_t map_outSize;
	void* map_outBuffer;
};

// Working with PCI PLX boards

// Internal variables
#define L_SCALE_PLX 0x8D00
#define L_ZERO_PLX 0x8D04

#define L_BOARD_REVISION_PLX 0x8D3F
#define L_READY_PLX 0x8D40
#define L_TMODE1_PLX 0x8D41
#define L_TMODE2_PLX 0x8D42
#define L_TEST_LOAD_PLX 0x8D52
#define L_CORRECTION_ENABLE_PLX 0x8D60

#define L_ADC_ENABLE_PLX 0x8D62

// command defines
#define cmTEST_PLX 0

void DaqL780::QueryInterface(void **ppv)
{
	*ppv = this;
	static_cast<LUnknown*>(*ppv)->AddRef();
	return;
}

size_t DaqL780::AddRef()
{
	atomic_inc(&m_cRef);
	return m_cRef.counter;
}

size_t DaqL780::Release()
{
	atomic_dec(&m_cRef);
	if (m_cRef.counter == 0) {
		delete this;
		return 0;
	}
	return m_cRef.counter;
}

// COMMON FUNCTIONS //////////////////////////////////////
ULONG DaqL780::GetSlotParam(PSLOT_PAR slPar)
{
	memcpy(slPar, &sl, sizeof(SLOT_PAR));
	return 0;
}

HANDLE DaqL780::OpenLDevice()
{
	char szDrvName[18];
	ULONG status;
	size_t cbRet;

	sprintf(szDrvName, "/dev/ldev%d", m_Slot);

	hVxd = LCreateFile(szDrvName);

	if (hVxd == INVALID_HANDLE_VALUE) {
		return INVALID_HANDLE_VALUE;
	}
	status = !LDeviceIoControl(hVxd, DIOC_GET_PARAMS,
		nullptr, 0,
		&sl, sizeof(SLOT_PAR),
		cbRet);

	if (status) {
		return INVALID_HANDLE_VALUE; // must be for register config!!!
	}
	hEvent = 0;

	return hVxd;
}

LONG DaqL780::CloseLDevice()
{
	LONG status = L_ERROR;
	if (hVxd == INVALID_HANDLE_VALUE) {
		return status;
	}
	status = LCloseHandle(hVxd);
	hVxd = INVALID_HANDLE_VALUE; ////////////////      !!!!!!!!!!!!!!!!!! close before open

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
ULONG DaqL780::RequestBufferStream(ULONG* Size) //in words
{
	size_t cbRet;
	ULONG OutBuf;
	ULONG status = L_ERROR;
	ULONG DiocCode;

	ULONG pb = *Size;
	DiocCode = DIOC_SETBUFFER;

	status = !LDeviceIoControl(hVxd, DiocCode,
		&pb, sizeof(ULONG),
		&OutBuf, sizeof(ULONG),
		cbRet);
	*Size = OutBuf;
	// in linux 128*2048

	// +2048 for mapping pagecount page
	// in ldevpcibm for correct -1 page returned from driver

	if (map_inBuffer) {
		munmap(map_inBuffer, map_inSize * sizeof(short));
	}
	map_inSize = *Size + 2048;
	map_inBuffer = mmap(nullptr, map_inSize * sizeof(short), PROT_READ, MAP_SHARED /*|MAP_LOCKED*/, hVxd, 0x1000); //may be correct 0x1*sysconf(_SC_PAGE_SIZE));
	if (map_inBuffer == MAP_FAILED) {
		map_inBuffer = nullptr;
		status = L_ERROR;
	}

	return status;
}

ULONG DaqL780::SetParametersStream(PDAQ_PAR sp, PULONG UsedSize, USHORT** Data, ULONG** Sync)
{
	size_t cbRet;
	ULONG OutBuf[4];
	ULONG status = L_ERROR;
	USHORT* d1;

#define ret_val(v) (dp->t1.v)

	PWDAQ_PAR dp;
	ULONG sz;
	void* ptr;
	USHORT tPages, tFIFO, tIrqStep;

	dp = &wadc_par;
	sz = sizeof(WDAQ_PAR);

	status = !LDeviceIoControl(hVxd, DIOC_SETUP,
		dp, sz,
		OutBuf, sizeof(OutBuf[0]) * 4, // sizeof(PVOID) PVOID platform dependent
		cbRet);

	tPages = static_cast<USHORT>(OutBuf[0]);
	tFIFO = static_cast<USHORT>(OutBuf[1]);
	tIrqStep = static_cast<USHORT>(OutBuf[2]);

	ret_val(Pages) = tPages;
	ret_val(FIFO) = tFIFO;
	ret_val(IrqStep) = tIrqStep;
	*UsedSize = tPages * tIrqStep;

	ptr = map_inBuffer;
	if (ptr == nullptr) {
		return L_ERROR;
	}
	*Sync = reinterpret_cast<PULONG>(ptr);
	d1 = reinterpret_cast<PUSHORT>(ptr);
	*Data = &d1[2048];

	if (sp != nullptr) {
		sp->Pages = tPages; // update properties to new real values;
		sp->FIFO = tFIFO;
		sp->IrqStep = tIrqStep;
	}

	return status;
}

ULONG DaqL780::FillDAQparameters(PADC_PAR sp)
{
	if (sp == nullptr || sp->s_Type != L_ADC_PARAM) {
		return L_ERROR;
	}
	return FillADCparameters(sp);
}

// end of uni stream interface

ULONG DaqL780::InitStartLDevice()
{
	size_t cbRet;
	ULONG InBuf, OutBuf, status = L_ERROR;
	status = !LDeviceIoControl(hVxd, DIOC_INIT_SYNC,
		&InBuf, sizeof(ULONG),
		&OutBuf, sizeof(ULONG),
		cbRet);
	return status;
}

ULONG DaqL780::StartLDevice()
{
	size_t cbRet;
	ULONG InBuf, status = L_ERROR;

	status = !LDeviceIoControl(hVxd, DIOC_START,
		&InBuf, sizeof(ULONG),
		DataBuffer, DataSize, // here we send data buffer parameters to lock in driver
		cbRet);

	return status;
}

ULONG DaqL780::StopLDevice()
{
	size_t cbRet;
	ULONG InBuf, OutBuf;
	ULONG status = L_ERROR;
	status = !LDeviceIoControl(hVxd, DIOC_STOP,
		&InBuf, sizeof(ULONG),
		&OutBuf, sizeof(ULONG),
		cbRet);
	return status;
};

void DaqL780::CopyDAQtoWDAQ(ADC_PAR* adc_par, WADC_PAR_0* wadc_par_t3)
{
	wadc_par_t3->s_Type = adc_par->s_Type;
	wadc_par_t3->FIFO = adc_par->FIFO;
	wadc_par_t3->IrqStep = adc_par->IrqStep;
	wadc_par_t3->Pages = adc_par->Pages;
	wadc_par_t3->AutoInit = adc_par->AutoInit;
	wadc_par_t3->dRate = adc_par->dRate;
	wadc_par_t3->dFrame = adc_par->dFrame;
	wadc_par_t3->dScale = adc_par->dScale;
	wadc_par_t3->Rate = adc_par->Rate;
	wadc_par_t3->Frame = adc_par->Frame;
	wadc_par_t3->Scale = adc_par->Scale;
	wadc_par_t3->FPDelay = adc_par->FPDelay;

	wadc_par_t3->SynchroType = adc_par->SynchroType;
	wadc_par_t3->SynchroSensitivity = adc_par->SynchroSensitivity;
	wadc_par_t3->SynchroMode = adc_par->SynchroMode;
	wadc_par_t3->AdChannel = adc_par->AdChannel;
	wadc_par_t3->AdThreshold = adc_par->AdThreshold;
	wadc_par_t3->NCh = adc_par->NCh;
	for (int i = 0; i < 128; ++i) {
		wadc_par_t3->Chn[i] = adc_par->Chn[i];
	}
	wadc_par_t3->AdcEna = adc_par->AdcEna;
	wadc_par_t3->IrqEna = adc_par->IrqEna;
}

// IDMA with  PLX9050 PCI chip /////////////////////////////////////////////////
ULONG DaqL780::GetWord_DM(USHORT Addr, PUSHORT Data)
{
	size_t cbRet;
	USHORT par = Addr;
	return !LDeviceIoControl(hVxd, DIOC_GET_DM_A, //DIOC_GET_DM_W,
		&par, sizeof(par),
		Data, sizeof(USHORT),
		cbRet);
}

ULONG DaqL780::PutWord_DM(USHORT Addr, USHORT Data)
{
	size_t cbRet;
	USHORT par = Addr;
	return !LDeviceIoControl(hVxd, DIOC_PUT_DM_A, //DIOC_PUT_DM_W,
		&par, sizeof(par),
		&Data, sizeof(USHORT),
		cbRet);
}

ULONG DaqL780::SendCommand(USHORT Cmd)
{
	size_t cbRet;
	USHORT data = 0;
	USHORT par = Cmd;
	return !LDeviceIoControl(hVxd, DIOC_COMMAND_PLX,
		&par, sizeof(par),
		&data, sizeof(USHORT),
		cbRet);
}

ULONG DaqL780::PutWord_PM(USHORT Addr, ULONG Data)
{
	size_t cbRet;
	USHORT par = Addr;
	return !LDeviceIoControl(hVxd, DIOC_PUT_PM_A,
		&par, sizeof(par),
		&Data, sizeof(ULONG),
		cbRet);
}

ULONG DaqL780::GetWord_PM(USHORT Addr, PULONG Data)
{
	size_t cbRet;
	USHORT par = Addr;
	return !LDeviceIoControl(hVxd, DIOC_GET_PM_A,
		&par, sizeof(par),
		Data, sizeof(ULONG),
		cbRet);
}

ULONG DaqL780::PutArray_DM(USHORT Addr, ULONG Count, PUSHORT Data)
{
	size_t cbRet;
	USHORT par = Addr;
	ULONG len = 1024;
	int status;
	do {
		if (Count < len) {
			len = Count;
		}
		status = LDeviceIoControl(hVxd, DIOC_PUT_DM_A,
			&par, sizeof(par),
			Data, len * sizeof(USHORT),
			cbRet);
		if (!status) {
			break;
		}
		Data += len;
		par += static_cast<USHORT>(len);
		Count -= len;
	} while (Count);
	return !status;
}

ULONG DaqL780::GetArray_DM(USHORT Addr, ULONG Count, PUSHORT Data)
{
	size_t cbRet;
	USHORT par = Addr;
	ULONG len = 1024;
	int status;
	do {
		if (Count < len) {
			len = Count;
		}
		status = LDeviceIoControl(hVxd, DIOC_GET_DM_A,
			&par, sizeof(par),
			Data, len * sizeof(USHORT),
			cbRet);
		if (!status) {
			break;
		}
		Data += len;
		par += static_cast<USHORT>(len);
		Count -= len;
	} while (Count);
	return !status;
}

ULONG DaqL780::PutArray_PM(USHORT Addr, ULONG Count, PULONG Data)
{
	size_t cbRet;
	USHORT par = Addr;
	ULONG len = 1024;
	int status;
	do {
		if (Count < len) {
			len = Count;
		}
		status = LDeviceIoControl(hVxd, DIOC_PUT_PM_A,
			&par, sizeof(par),
			Data, len * sizeof(ULONG),
			cbRet);
		if (!status) {
			break;
		}
		Data += len;
		par += static_cast<USHORT>(len);
		Count -= len;
	} while (Count);
	return !status;
}

ULONG DaqL780::GetArray_PM(USHORT Addr, ULONG Count, PULONG Data)
{
	size_t cbRet;
	USHORT par = Addr;
	ULONG len = 1024;
	int status;

	do {
		if (Count < len) {
			len = Count;
		}
		status = LDeviceIoControl(hVxd, DIOC_GET_PM_A,
			&par, sizeof(par),
			Data, len * sizeof(ULONG),
			cbRet);
		if (!status) {
			break;
		}
		Data += len;
		par += static_cast<USHORT>(len);
		Count -= len;
	} while (Count);
	return !status;
}

ULONG DaqL780::PlataTest()
{
	USHORT d1;
	if (GetWord_DM(L_TMODE1_PLX, &d1)) {
		return L_ERROR;
	}
	USHORT d2;
	if (GetWord_DM(L_TMODE2_PLX, &d2)) {
		return L_ERROR;
	}
	if ((d1 != 0x5555) || (d2 != 0xAAAA)) {
		return L_ERROR;
	} else {
		if (PutWord_DM(L_TEST_LOAD_PLX, 0x77bb)) {
			return L_ERROR;
		}
		int timeOut = 10000000;
		do {
			if (GetWord_DM(L_READY_PLX, &d1)) {
				return L_ERROR;
			}
		} while (!d1 && (timeOut--));
		if (timeOut == -1) {
			return L_ERROR;
		}
		if (SendCommand(cmTEST_PLX)) {
			return L_ERROR;
		}
		if (GetWord_DM(L_TEST_LOAD_PLX, &d1)) {
			return L_ERROR;
		}
		if (d1 != 0xAA55) {
			return L_ERROR;
		}
	}
	return L_SUCCESS;
}

ULONG DaqL780::FillADCparameters(PADC_PAR ap)
{
	const double max_rate = 3300.0;
	ULONG i;
	double QF;
	double DSP_CLOCK_OUT_PLX;
	double SCLOCK_DIV;
	double framedelay;

	if (ap->dRate < 0) {
		return L_ERROR;
	}
	if (ap->dFrame < 0) {
		return L_ERROR;
	}
	if (ap->FIFO == 0) {
		return L_ERROR;
	}
	if (ap->Pages == 0) {
		return L_ERROR;
	}
	if (ap->IrqStep == 0) {
		return L_ERROR;
	}
	QF = pdu.t1.Quartz / 1000.0;
	DSP_CLOCK_OUT_PLX = 2.0 * QF;
	if (DSP_CLOCK_OUT_PLX < 1e-6) {
		return L_ERROR;
	}
	if (ap->dRate < 0.1) {
		ap->dRate = 0.1;
	}
	if (ap->dRate > max_rate) {
		ap->dRate = max_rate;
	}
	// частота сбора в единицах SCLOCK_DIV SPORT DSP
	SCLOCK_DIV = DSP_CLOCK_OUT_PLX / (2.0 * (ap->dRate)) - 0.5;
	if (SCLOCK_DIV > 65500.0) {
		SCLOCK_DIV = 65500.0;
	}
	adc_par.Rate = static_cast<USHORT>(SCLOCK_DIV);

	ap->dRate = DSP_CLOCK_OUT_PLX / (2.0 * (adc_par.Rate + 1));

	adc_par.FPDelay = static_cast<USHORT>(DSP_CLOCK_OUT_PLX / (ap->dRate) + 5.5);

	// величина задержки в единицах SCLOCK SPORT DSP
	if (ap->dRate > 1000.0) {
		ap->dFrame = 0; //  no inter-frame at freq 1000 kHz and above
	}
	if ((1.0 / (ap->dRate)) > (ap->dFrame)) {
		ap->dFrame = 1.0 / (ap->dRate);
	}
	//
	framedelay = (ap->dFrame) * (ap->dRate) - 0.5;
	if (framedelay > 65500.0) {
		framedelay = 65500.0;
	}
	adc_par.Frame = static_cast<USHORT>(framedelay);

	ap->dFrame = (adc_par.Frame + 1) / (ap->dRate);

	adc_par.Scale = 0;

	// More
	adc_par.s_Type = ap->s_Type;
	adc_par.SynchroType = ap->SynchroType;
	adc_par.SynchroSensitivity = ap->SynchroSensitivity;
	adc_par.SynchroMode = ap->SynchroMode;
	adc_par.AdChannel = ap->AdChannel;
	adc_par.AdThreshold = ap->AdThreshold;

	adc_par.FIFO = ap->FIFO;
	adc_par.IrqStep = ap->IrqStep;
	adc_par.Pages = ap->Pages;
	if (ap->NCh > 128) {
		ap->NCh = 128;
	}
	adc_par.NCh = ap->NCh;
	for (i = 0; i < ap->NCh; i++) {
		adc_par.Chn[i] = ap->Chn[i];
	}
	adc_par.AutoInit = ap->AutoInit;
	adc_par.IrqEna = ap->IrqEna;
	adc_par.AdcEna = ap->AdcEna;

	// make a copy  of adc_par in wadc_par for C-style interface to driver ////////
	CopyDAQtoWDAQ(&adc_par, &wadc_par.t3);
	return L_SUCCESS;
}

ULONG DaqL780::ReadPlataDescr(LPVOID pd)
{
	for (USHORT i = 0; i < sizeof(PLATA_DESCR_U) / 2; i++) {
		if (ReadFlashWord(i, &pdu.wi.data[i])) {
			return L_ERROR;
		}
	}
	memcpy(pd, &pdu, sizeof(PLATA_DESCR_U));
	return L_SUCCESS;
}

ULONG DaqL780::EnableCorrection(USHORT Ena)
{
	// load
	if (PutArray_DM(L_ZERO_PLX, 4, &(pdu.t1.ADCFactor[0]))) {
		return L_ERROR;
	}
	if (PutArray_DM(L_SCALE_PLX, 4, &(pdu.t1.ADCFactor[4]))) {
		return L_ERROR;
	}
	// enable or disable
	if (PutWord_DM(L_CORRECTION_ENABLE_PLX, Ena)) {
		return L_ERROR;
	}
	return L_SUCCESS;
}

////////////////////////////////////////////////////////////////////////////////
// Процедура чтения слова из пользовательского ППЗУ
////////////////////////////////////////////////////////////////////////////////
ULONG DaqL780::ReadFlashWord(USHORT FlashAddress, PUSHORT Data)
{
	size_t cbRet;
	USHORT par = FlashAddress;
	return !LDeviceIoControl(hVxd, DIOC_READ_FLASH_WORD, //DIOC_GET_DM_W,
		&par, sizeof(par),
		Data, sizeof(USHORT),
		cbRet);
}

ULONG DaqL780::EnableFlashWrite(USHORT Flag)
{
	size_t cbRet;
	USHORT par = 0; // addr not use
	return !LDeviceIoControl(hVxd, DIOC_ENABLE_FLASH_WRITE, //DIOC_PUT_DM_W,
		&par, sizeof(par),
		&Flag, sizeof(USHORT),
		cbRet);
}

ULONG DaqL780::LoadBios(const char* FileName)
{
	USHORT* LCBios;
	FILE* BiosFile;
	size_t NBytes;
	PUCHAR BiosCode = nullptr;
	USHORT* Tmp;
	USHORT Count;
	CHAR FName[255];
	size_t cbRet;

	ULONG status = L_ERROR;
	do {
		strcpy(FName, FileName);
		strcat(FName, ".bio");
		BiosFile = fopen(FName, "rb");
		if (!BiosFile) {
			break;
		}
		fseek(BiosFile, 0, SEEK_END);
		NBytes = static_cast<size_t>(ftell(BiosFile));
		rewind(BiosFile);

		BiosCode = new UCHAR[NBytes + 2];
		if (fread(BiosCode, 1, NBytes, BiosFile) != NBytes) {
			break;
		}
		LCBios = reinterpret_cast<PUSHORT>(BiosCode);

		// RESET для ADSP-218x // переписать как ioctl
		if (!LDeviceIoControl(hVxd, DIOC_RESET_PLX, nullptr, 0, nullptr, 0, cbRet)) {
			break;
		}
		// Load DSP DM word
		Tmp = LCBios + LCBios[0] + 1; // calculate DM address &LCBios[0]+LCBios[0]
		Count = *Tmp++; // counter

		if (PutArray_DM(0x2000, Count, Tmp)) {
			break;
		}
		if (PutWord_DM(L_BOARD_REVISION_PLX, static_cast<USHORT>(sl.BoardType == PCIC ? 'C' : 'B'))) {
			break; // revision
		}
		// Load DSP PM word
		Tmp = &LCBios[3]; //LCBios+3;
		Count = static_cast<USHORT>(LCBios[0] - 2);
		if (PutArray_PM(0x0001, Count / 2, reinterpret_cast<PULONG>(Tmp))) {
			break;
		}
		// Load last DSP PM word
		ULONG d2;
		if (NBytes + 1 >= sizeof(ULONG)) {
			d2 = *reinterpret_cast<PULONG>(LCBios + 1);
		} else {
			break;
		}
		if (PutWord_PM(0x0000, d2)) {
			break;
		}
		// rewrite изменил драйвера пришлось переписать ()
		if (PlataTest() != L_SUCCESS) {
			break;
		}
		if (!LDeviceIoControl(hVxd, DIOC_SET_DSP_TYPE, nullptr, 0, nullptr, 0, cbRet)) {
			break; //(L_SUCCESS)
		}
		if (PutWord_DM(L_ADC_ENABLE_PLX, 0)) {
			break; // stop adc...
		}
		status = L_SUCCESS;
	} while (status == L_ERROR);
	// освободим память и выйдем из функции
	if (BiosCode)
		delete[] BiosCode;
	if (BiosFile)
		fclose(BiosFile);
	return status;
}

void LSetLastError(int Err)
{
	errno = Err;
}

int LGetLastError(void)
{
	return errno;
}

// add class for new board here.
// main function of dll
LUnknown* CreateInstance(ULONG Slot)
{
	LUnknown* pI;

	LSetLastError(L_SUCCESS);
	SLOT_PAR sl;
	DaqL780* pL = new DaqL780(Slot);
	if (pL == nullptr) {
		LSetLastError(L_ERROR);
		return nullptr;
	}
	HANDLE hVxd = pL->OpenLDevice();
	if (hVxd == INVALID_HANDLE_VALUE) {
		if (LGetLastError() == ERROR_FILE_NOT_FOUND)
			LSetLastError(L_ERROR_NOBOARD);
		if (LGetLastError() == ERROR_ACCESS_DENIED)
			LSetLastError(L_ERROR_INUSE);
		return nullptr;
	}

	pL->GetSlotParam(&sl);

	pL->CloseLDevice();
	delete pL;

	switch (sl.BoardType) {
	case PCIA:
	case PCIB:
	case PCIC:
		pI = static_cast<DaqL780*>(new DaqL780(Slot));
		pI->AddRef();
		break;

	default:
		pI = nullptr;
		LSetLastError(L_NOTSUPPORTED);
	}
	return pI;
}

using namespace std;

int compare(const double* a, const double* b)
{
	if (*a < *b) {
		return -1;
	} else if (*a > *b) {
		return 1;
	}
	return 0;
}

int main(int argc, char** argv)
{
	PUSHORT p;
	PULONG pp;

	PLATA_DESCR_U pd;
	ADC_PAR adcPar;
	ULONG size;
	void* handle = nullptr;
	char const* deviceName = "L783";

	LUnknown* pIUnknown = CreateInstance(0);
	if (pIUnknown == nullptr) {
		return 3;
	}

	DaqL780* pI;
	pIUnknown->QueryInterface(reinterpret_cast<void**>(&pI));
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

	size = 36864;

	pI->RequestBufferStream(&size);

	adcPar.s_Type = L_ADC_PARAM;
	adcPar.AutoInit = 1; // 1 = in loop
	adcPar.dRate = 100.0; // kHz
	adcPar.dFrame = 0;
	adcPar.dScale = 0;
	adcPar.SynchroType = 3;
	adcPar.SynchroSensitivity = 0;
	adcPar.SynchroMode = 0;
	adcPar.AdChannel = 0;
	adcPar.AdThreshold = 0;
	adcPar.NCh = 2;
	if (argc > 1 && argv[1][0] >= '0' && argv[1][0] <= '9') {
		unsigned int idx = static_cast<unsigned int>(atoi(argv[1]));
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
	adcPar.FIFO = adcPar.IrqStep = 1024;
	adcPar.Pages = 256;
	adcPar.IrqEna = 1;
	adcPar.AdcEna = 1;

	pI->FillDAQparameters(&adcPar);
	pI->SetParametersStream(&adcPar, &size, &p, &pp);

	pI->EnableCorrection(1);
	pI->InitStartLDevice();
	pI->StartLDevice();

	size_t idx;
	do {
		cin >> idx;
		idx *= 2;
		if (idx < adcPar.NCh) {
			// copy voltages and calculate median
			size_t count = (size - idx + 1) / adcPar.NCh;
			double* data = new double[count];
			for (size_t i = idx, j = 0; i < size && j < count; i += adcPar.NCh) {
				data[j++] = static_cast<double>(static_cast<SHORT>(p[i]));
			}
			qsort(data, count, sizeof(double), reinterpret_cast<int (*)(const void*, const void*)>(&compare));
			double s;
			if (count & 1) {
				s = data[count / 2];
			} else {
				s = 0.5 * data[count / 2] + 0.5 * data[count / 2 - 1];
			}
			delete[] data;
			s *= 10. / (1 << 12); // scaling
			cout << (idx >> 1) << '\t' << s << endl;
		}
	} while (idx < 16);

	pI->StopLDevice();
	pI->CloseLDevice();
	pI->Release();

	if (handle) {
		dlclose(handle);
	}
	return 0;
}