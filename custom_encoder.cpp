#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "SKP_Silk_SDK_API.h"

#define MAX_BYTES_PER_FRAME     250
#define MAX_INPUT_FRAMES        5
#define FRAME_LENGTH_MS         20
#define MAX_API_FS_KHZ          48

int main( int argc, char* argv[] )
{
    if ( argc != 4 ) {
        fprintf( stderr, "Usage: %s <sample_rate_hz> <input.pcm> <output.silk>\n", argv[ 0 ] );
        return 1;
    }

    int API_fs_Hz = atoi( argv[ 1 ] );
    char *fin_name = argv[ 2 ];
    char *fout_name = argv[ 3 ];

    // Use working settings from custom_encoder_origin.cpp
    SKP_int32 max_internal_fs_Hz = 0;  // Will be set according to official logic
    SKP_int32 targetRate_bps = 24000;  // Same as working version
    SKP_int32 packetSize_ms = 20;
    SKP_int32 frameSizeReadFromFile_ms = 20;
    SKP_int32 packetLoss_perc = 0;
    SKP_int32 complexity_mode = 2;
    SKP_int32 DTX_enabled = 0;
    SKP_int32 INBandFEC_enabled = 0;

    size_t    counter;
    SKP_int32 ret;
    SKP_int16 nBytes;
    SKP_uint8 payload[ MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES ];
    SKP_int16 in[ FRAME_LENGTH_MS * MAX_API_FS_KHZ * MAX_INPUT_FRAMES ];
    FILE      *fin = NULL, *fout = NULL;
    SKP_int32 encSizeBytes;
    void      *psEnc = NULL;
    SKP_int32 smplsSinceLastPacket = 0;

    // Control structures (exactly like official example)
    SKP_SILK_SDK_EncControlStruct encControl; // Input to encoder
    SKP_SILK_SDK_EncControlStruct encStatus;  // Output from encoder

    fprintf( stderr, "Official SILK Encoder - Rate: %d Hz, Target: %d bps\n", API_fs_Hz, targetRate_bps );

    // Validate API sampling rate (official check)
    if( API_fs_Hz > MAX_API_FS_KHZ * 1000 || API_fs_Hz < 0 ) {
        fprintf( stderr, "Error: API sampling rate = %d out of range, valid range 8000 - 48000\n", API_fs_Hz );
        return 1;
    }

    // Official max_internal_fs_Hz logic
    if( max_internal_fs_Hz == 0 ) {
        max_internal_fs_Hz = 24000;
        if( API_fs_Hz < max_internal_fs_Hz ) {
            max_internal_fs_Hz = API_fs_Hz;
        }
    }

    fprintf( stderr, "Using maxInternalSampleRate: %d Hz\n", max_internal_fs_Hz );

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

    // Add Silk header (exactly like working version - 10 bytes with \x02 prefix)
    static const char silk_header[] = "\x02#!SILK_V3";
    fwrite( silk_header, sizeof( char ), 10, fout );

    // Create Encoder (official sequence)
    ret = SKP_Silk_SDK_Get_Encoder_Size( &encSizeBytes );
    if( ret ) {
        fprintf( stderr, "SKP_Silk_SDK_Get_Encoder_Size returned %d\n", ret );
        goto cleanup;
    }
    fprintf( stderr, "Encoder size: %d bytes\n", encSizeBytes );

    psEnc = malloc( encSizeBytes );
    if ( psEnc == NULL ) {
        fprintf( stderr, "Error: could not allocate memory for encoder\n" );
        goto cleanup;
    }

    // Reset Encoder (CRITICAL: pass encStatus, not encControl!)
    ret = SKP_Silk_SDK_InitEncoder( psEnc, &encStatus );
    if( ret ) {
        fprintf( stderr, "SKP_Silk_SDK_InitEncoder returned %d\n", ret );
        goto cleanup;
    }
    fprintf( stderr, "Encoder initialized successfully\n" );

    // Set Encoder parameters (official way)
    encControl.API_sampleRate        = API_fs_Hz;
    encControl.maxInternalSampleRate = max_internal_fs_Hz;
    encControl.packetSize            = ( packetSize_ms * API_fs_Hz ) / 1000;
    encControl.packetLossPercentage  = packetLoss_perc;
    encControl.useInBandFEC          = INBandFEC_enabled;
    encControl.useDTX                = DTX_enabled;
    encControl.complexity            = complexity_mode;
    encControl.bitRate               = ( targetRate_bps > 0 ? targetRate_bps : 0 );

    fprintf( stderr, "Encoder config: API_sampleRate=%d, maxInternalSampleRate=%d, packetSize=%d, bitRate=%d\n",
             encControl.API_sampleRate, encControl.maxInternalSampleRate,
             encControl.packetSize, encControl.bitRate );

    // Encoding loop (based on working version)
    while( 1 ) {
        // Read input from file (like working version)
        SKP_int32 expected_samples = ( frameSizeReadFromFile_ms * API_fs_Hz ) / 1000;
        size_t samples_read = fread( in, sizeof( SKP_int16 ), expected_samples, fin );

        if( samples_read < expected_samples ) {
            if( samples_read == 0 ) {
                break;  // End of file
            }
            // Handle partial read (like working version)
            memset( &in[samples_read], 0x00, (expected_samples - samples_read) * sizeof(SKP_int16) );
            counter = samples_read;  // Update counter to actual samples read
        } else {
            counter = samples_read;
        }

#ifdef _SYSTEM_IS_BIG_ENDIAN
        // Handle endianness (like working version)
        for( size_t i = 0; i < counter; i++ ) {
            SKP_int16 tmp = in[i];
            SKP_uint8* p1 = (SKP_uint8*)&in[i];
            SKP_uint8* p2 = (SKP_uint8*)&tmp;
            p1[0] = p2[1];
            p1[1] = p2[0];
        }
#endif

        // max payload size
        nBytes = MAX_BYTES_PER_FRAME * MAX_INPUT_FRAMES;

        // Silk Encoder (with minimal error checking)
        ret = SKP_Silk_SDK_Encode( psEnc, &encControl, in, (SKP_int16)counter, payload, &nBytes );
        if( ret ) {
            fprintf( stderr, "Warning: SKP_Silk_SDK_Encode returned %d, continuing...\n", ret );
            // Continue processing instead of aborting (like working version)
        }

        // Get packet size (like working version)
        SKP_int32 current_packetSize_ms = (SKP_int)((1000 * (SKP_int32)encControl.packetSize) / encControl.API_sampleRate);

        smplsSinceLastPacket += (SKP_int)counter;

        if (((1000 * smplsSinceLastPacket) / API_fs_Hz) == current_packetSize_ms) {
            // Write payload size (like working version)
            fwrite( &nBytes, sizeof( SKP_int16 ), 1, fout );
            // Write payload
            fwrite( payload, sizeof( SKP_uint8 ), nBytes, fout );

            smplsSinceLastPacket = 0;
        }
    }

    // Don't write terminator (like working version)

    fprintf( stderr, "\nEncoding completed successfully\n" );

    // Success cleanup
    if ( fin ) fclose( fin );
    if ( fout ) fclose( fout );
    if ( psEnc ) free( psEnc );
    return 0;

cleanup:
    // Error cleanup
    if ( fin ) fclose( fin );
    if ( fout ) fclose( fout );
    if ( psEnc ) free( psEnc );
    return 1;
}
