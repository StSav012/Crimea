#ifndef _PCICMD_H
#define _PCICMD_H

// Working with PCI PLX boards


// Internal variables
#define  CONTROL_TABLE_PLX                 0x8A00

#define  SCALE_PLX                         0x8D00
#define  ZERO_PLX                          0x8D04

#define  CONTROL_TABLE_LENGHT_PLX          0x8D08

#define  BOARD_REVISION_PLX                0x8D3F
#define  READY_PLX                         0x8D40
#define  TMODE1_PLX                        0x8D41
#define  TMODE2_PLX                        0x8D42
#define  DAC_IRQ_SOURCE_PLX                0x8D43
#define  DAC_ENABLE_IRQ_VALUE_PLX          0x8D44
#define  DAC_IRQ_FIFO_ADDRESS_PLX          0x8D45
#define  DAC_IRQ_STEP_PLX                  0x8D46
#define  ENABLE_TTL_OUT_PLX                0x8D47
#define  DSP_TYPE_PLX                      0x8D48
#define  COMMAND_PLX                       0x8D49
#define  FIRST_SAMPLE_DELAY_PLX            0x8D4A
#define  TTL_OUT_PLX                       0x8D4C
#define  TTL_IN_PLX                        0x8D4D
#define  DAC_FIFO_PTR_PLX                  0x8D4F
#define  FIFO_PTR_PLX                      0x8D50
#define  TEST_LOAD_PLX                     0x8D52
#define  ADC_RATE_PLX                      0x8D53
#define  INTER_KADR_DELAY_PLX              0x8D54
#define  DAC_RATE_PLX                      0x8D55
#define  DAC_VALUE_PLX                     0x8D56
#define  ENABLE_IRQ_PLX                    0x8D57
#define  IRQ_STEP_PLX                      0x8D58
#define  IRQ_FIFO_ADDRESS_PLX              0x8D5A
#define  ENABLE_IRQ_VALUE_PLX              0x8D5B
#define  ADC_SAMPLE_PLX                    0x8D5C
#define  ADC_CHANNEL_PLX                   0x8D5D
#define  DAC_SCLK_DIV_PLX                  0x8D5E
#define  CORRECTION_ENABLE_PLX             0x8D60

#define  ADC_ENABLE_PLX                    0x8D62
#define  ADC_FIFO_BASE_ADDRESS_PLX         0x8D63
#define  ADC_FIFO_BASE_ADDRESS_INDEX_PLX   0x8D64
#define  ADC_FIFO_LENGTH_PLX               0x8D65
#define  ADC_NEW_FIFO_LENGTH_PLX           0x8D66

#define  DAC_ENABLE_STREAM_PLX             0x8D67
#define  DAC_FIFO_BASE_ADDRESS_PLX         0x8D68
#define  DAC_FIFO_LENGTH_PLX               0x8D69
#define  DAC_NEW_FIFO_LENGTH_PLX           0x8D6A
#define  DAC_ENABLE_IRQ_PLX                0x8D6B

#define  SYNCHRO_TYPE_PLX                  0x8D70
#define  SYNCHRO_AD_CHANNEL_PLX            0x8D73
#define  SYNCHRO_AD_POROG_PLX              0x8D74
#define  SYNCHRO_AD_MODE_PLX               0x8D75
#define  SYNCHRO_AD_SENSITIVITY_PLX        0x8D76
#define  DAC                               0x8F00


// command defines
#define cmTEST_PLX                  0
#define cmLOAD_CONTROL_TABLE_PLX    1
#define cmADC_ENABLE_PLX            2
#define cmADC_FIFO_CONFIG_PLX       3
#define cmSET_ADC_KADR_PLX          4
#define cmENABLE_DAC_STREAM_PLX     5
#define cmDAC_FIFO_CONFIG_PLX       6
#define cmSET_DAC_RATE_PLX          7
#define cmADC_SAMPLE_PLX            8
#define cmTTL_IN_PLX                9
#define cmTTL_OUT_PLX               10
#define cmSYNCHRO_CONFIG_PLX        11
#define cmENABLE_IRQ_PLX            12
#define cmIRQ_TEST_PLX              13
#define cmSET_DSP_TYPE_PLX          14
#define cmENABLE_TTL_OUT_PLX        15

#endif
