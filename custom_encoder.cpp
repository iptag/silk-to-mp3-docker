#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "SKP_Silk_SDK_API.h"

#define MAX_BYTES_PER_FRAME     250  // Same as node-silk (peak bitrate of 100 kbps)
#define MAX_INPUT_FRAMES        5
#define FRAME_LENGTH_MS         20
#define MAX_API_FS_KHZ          48   // Same as node-silk

int main( int argc, char* argv[] )
{
    if ( argc != 4 ) {
        fprintf( stderr, "Usage: %s <sample_rate_hz> <input.pcm> <output.silk>\n", argv[ 0 ] );
        return 1;
    }

    int API_fs_Hz = atoi( argv[ 1 ] );
    char *fin_name = argv[ 2 ];
    char *fout_name = argv[ 3 ];

    size_t    counter;
    SKP_int32 ret;
    SKP_int16 nBytes;
    SKP_uint8 payload[ MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES ];
    SKP_int16 in[ ( FRAME_LENGTH_MS * MAX_API_FS_KHZ ) * MAX_INPUT_FRAMES ];
    FILE      *fin, *fout;
    SKP_int32 encSizeBytes;
    void      *psEnc;

    /* default settings (matching node-silk) */
    SKP_int32 packetSize_ms = 20;
    SKP_int32 targetRate_bps = 24000;  // Same as node-silk
    SKP_int32 complexity_mode = 2;
    SKP_int32 useInBandFEC = 0;
    SKP_int32 useDTX = 0;
    SKP_int32 packetLoss_perc = 0;

    SKP_SILK_SDK_EncControlStruct encStatus = { 0 };  // Struct for status of encoder
    SKP_SILK_SDK_EncControlStruct encControl = { 0 }; // Struct for input to encoder

    fin = fopen( fin_name, "rb" );
    if ( fin == NULL ) {
        fprintf( stderr, "Error: could not open input file %s\n", fin_name );
        return 1;
    }

    fout = fopen( fout_name, "wb" );
    if ( fout == NULL ) {
        fprintf( stderr, "Error: could not open output file %s\n", fout_name );
        fclose( fin );
        return 1;
    }

    /* Add Silk header (exactly like node-silk) */
    static const char silk_header[] = "\x02#!SILK_V3";
    fwrite( silk_header, sizeof( char ), 10, fout );

    // ==================== CORRECTED ENCODER INITIALIZATION ====================

    // 1. GET ENCODER SIZE
    ret = SKP_Silk_SDK_Get_Encoder_Size( &encSizeBytes );
    if( ret ) {
        fprintf( stderr, "SKP_Silk_SDK_Get_Encoder_Size returned %d\n", ret );
        fclose(fin);
        fclose(fout);
        return 1;
    }
    psEnc = malloc( encSizeBytes );

    // 2. SET CONFIGURATION PARAMETERS (like node-silk)
    SKP_int32 max_internal_fs_Hz = 0;
    if (max_internal_fs_Hz == 0) {
        max_internal_fs_Hz = 24000;
        if (API_fs_Hz < max_internal_fs_Hz) {
            max_internal_fs_Hz = API_fs_Hz;
        }
    }

    // Configure encControl for encoding calls (exactly like node-silk)
    encControl.API_sampleRate        = API_fs_Hz;
    encControl.maxInternalSampleRate = max_internal_fs_Hz;
    encControl.packetSize            = ( packetSize_ms * API_fs_Hz ) / 1000;
    encControl.bitRate               = (targetRate_bps > 0 ? targetRate_bps : 0);
    encControl.packetLossPercentage  = packetLoss_perc;
    encControl.complexity            = complexity_mode;
    encControl.useInBandFEC          = useInBandFEC;
    encControl.useDTX                = useDTX;

    // Configure encoder parameters

    // 5. INITIALIZE THE ENCODER WITH CONFIGURED PARAMETERS
    ret = SKP_Silk_SDK_InitEncoder( psEnc, &encStatus );
    if( ret ) {
        fprintf( stderr, "SKP_Silk_SDK_InitEncoder returned %d\n", ret );
        fclose(fin);
        fclose(fout);
        free(psEnc);
        return 1;
    }

    // ====================================================================


    // ==================== NODE-SILK COMPATIBLE ENCODING LOOP ====================
    SKP_int32 frameSizeReadFromFile_ms = 20;  // Same as node-silk
    SKP_int32 smplsSinceLastPacket = 0;

    // Initialize payload buffer
    memset( payload, 0, sizeof( payload ) );



    while( 1 ) {
        /* Read input (exactly like node-silk) */
        counter = (frameSizeReadFromFile_ms * API_fs_Hz) / 1000;

        // Read exactly counter samples (not bytes)
        size_t samples_read = fread( in, sizeof(SKP_int16), counter, fin );

        if( samples_read < counter ) {
            if( samples_read == 0 ) {
                break;  // End of file
            }
            // Handle partial read (like node-silk)
            memset( &in[samples_read], 0x00, (counter - samples_read) * sizeof(SKP_int16) );
            counter = samples_read;  // Update counter to actual samples read
        }

#ifdef _SYSTEM_IS_BIG_ENDIAN
        // Handle endianness (like node-silk)
        for( int i = 0; i < counter; i++ ) {
            SKP_int16 tmp = in[i];
            SKP_uint8* p1 = (SKP_uint8*)&in[i];
            SKP_uint8* p2 = (SKP_uint8*)&tmp;
            p1[0] = p2[1];
            p1[1] = p2[0];
        }
#endif

        /* max payload size (like node-silk) */
        nBytes = MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES;

        /* Silk Encoder (exactly like node-silk - no error checking!) */
        SKP_Silk_SDK_Encode( psEnc, &encControl, in, (SKP_int16)counter, payload, &nBytes );

        /* Get packet size (like node-silk) */
        SKP_int32 current_packetSize_ms = (SKP_int)((1000 * (SKP_int32)encControl.packetSize) / encControl.API_sampleRate);

        smplsSinceLastPacket += (SKP_int)counter;
        if (((1000 * smplsSinceLastPacket) / API_fs_Hz) == current_packetSize_ms) {
            /* Write payload size (like node-silk) */
            fwrite( &nBytes, sizeof( SKP_int16 ), 1, fout );
            /* Write payload */
            fwrite( payload, sizeof( SKP_uint8 ), nBytes, fout );

            smplsSinceLastPacket = 0;
        }
    }
    // =================================================================================

    fclose( fin );
    fclose( fout );
    free( psEnc );

    return 0;
}
