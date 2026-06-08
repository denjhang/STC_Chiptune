/*
 * VGM Player for STC8H SCC Synth — C++ Win32 Console
 *
 * C++ 控制节拍: 解析 VGM, SCC/AY 命令直接发串口, wait 用 multimedia timer
 * 固件只做 SCC 写入, 不解析 wait
 *
 * Timing: timeSetEvent(1,1) + WaitForSingleObject(mmEvent) + QPC
 * 与 RPFM VGMPlay 模式一致, 1ms 精度
 *
 * Build (MinGW):
 *   g++ -O2 -o vgm_player.exe vgm_player.cpp -lwinmm -lz
 *
 * Usage:
 *   vgm_player.exe --list
 *   vgm_player.exe 1
 *   vgm_player.exe "02 Vampire Killer" --port COM12
 *   vgm_player.exe 3 --speed 0.5 --loop
 *   vgm_player.exe --dump 1
 */

#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <io.h>
#include <fcntl.h>
#include <direct.h>
#include <zlib.h>

/* ========== Constants ========== */
#define SAMPLES_PER_SEC  44100
#define DEFAULT_BAUD    230400
#define MAX_PATH_LEN     1024
#define VGM_DIR_DEFAULT  "..\\vgm"

/* ========== Serial Port ========== */
static HANDLE g_hCom = INVALID_HANDLE_VALUE;

static bool serial_open(const char* port, int baud) {
    char path[32];
    snprintf(path, sizeof(path), "\\\\.\\%s", port);
    g_hCom = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                         OPEN_EXISTING, 0, NULL);
    if (g_hCom == INVALID_HANDLE_VALUE) return false;

    DCB dcb;
    memset(&dcb, 0, sizeof(dcb));
    dcb.DCBlength = sizeof(dcb);
    if (!GetCommState(g_hCom, &dcb)) { CloseHandle(g_hCom); g_hCom = INVALID_HANDLE_VALUE; return false; }
    dcb.BaudRate = baud;
    dcb.ByteSize = 8;
    dcb.StopBits = ONESTOPBIT;
    dcb.Parity = NOPARITY;
    dcb.fOutxCtsFlow = 0;
    dcb.fOutxDsrFlow = 0;
    dcb.fDtrControl = DTR_CONTROL_ENABLE;
    dcb.fRtsControl = RTS_CONTROL_ENABLE;
    if (!SetCommState(g_hCom, &dcb)) { CloseHandle(g_hCom); g_hCom = INVALID_HANDLE_VALUE; return false; }

    COMMTIMEOUTS ct;
    ct.ReadIntervalTimeout = MAXDWORD;
    ct.ReadTotalTimeoutMultiplier = 0;
    ct.ReadTotalTimeoutConstant = 0;
    ct.WriteTotalTimeoutMultiplier = 0;
    ct.WriteTotalTimeoutConstant = 100;
    SetCommTimeouts(g_hCom, &ct);

    PurgeComm(g_hCom, PURGE_TXCLEAR | PURGE_RXCLEAR);
    Sleep(50);
    return true;
}

static void serial_close(void) {
    if (g_hCom != INVALID_HANDLE_VALUE) {
        CloseHandle(g_hCom);
        g_hCom = INVALID_HANDLE_VALUE;
    }
}

static bool serial_write(const uint8_t* data, int len) {
    DWORD written;
    return WriteFile(g_hCom, data, len, &written, NULL) && written == (DWORD)len;
}

/* ========== VGM Command Length Table ========== */
static const uint8_t VGM_CMD_LEN[256] = {
    /* 0x00-0x1F: invalid */
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    /* 0x20: AY8910 type(3) */
    3,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    /* 0x30-0x3F: 4-byte chip writes */
    0,4,4,4,4,4,4,4, 4,4,4,4,4,4,4,4,
    /* 0x40-0x4F: 4E/4F=4byte, rest=5byte */
    5,5,5,5,5,5,5,5, 5,5,5,5,5,5,4,4,
    /* 0x50-0x5F: 4-byte chip writes */
    4,4,4,4,4,4,4,4, 4,4,4,4,4,4,4,4,
    /* 0x60-0x6F: 61=3, 62=1, 63=1, 66=1, 67=special */
    0,3,1,1,0,0,0,0, 0,0,0,0,0,0,0,0,
    /* 0x70-0x7F: short wait (1 byte) */
    1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,
    /* 0x80-0x8F: DAC write+wait (1 byte) */
    1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,
    /* 0x90-0x9F: 1 byte each */
    1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,
    /* 0xA0-0xAF: AY/SCC 3-byte */
    3,3,3,3,3,3,3,3, 3,3,3,3,3,3,3,3,
    /* 0xB0-0xBF: 4-byte */
    4,4,4,4,4,4,4,4, 4,4,4,4,4,4,4,4,
    /* 0xC0-0xCF: 5-byte */
    5,5,5,5,5,5,5,5, 5,5,5,5,5,5,5,5,
    /* 0xD0-0xD3: 4-byte, 0xD4-0xD7: 5-byte, 0xD8-0xDF: 4-byte */
    4,4,4,4,5,5,5,5, 4,4,4,4,4,4,4,4,
    /* 0xE0-0xEF: 5-byte */
    5,5,5,5,5,5,5,5, 5,5,5,5,5,5,5,5,
    /* 0xF0-0xFF: 5-byte */
    5,5,5,5,5,5,5,5, 5,5,5,5,5,5,5,5,
};

/* ========== VGM Data ========== */
static uint8_t* g_vgm = NULL;
static size_t   g_vgm_len = 0;

static uint32_t read_le32(const uint8_t* p) {
    return p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24);
}

static uint16_t read_le16(const uint8_t* p) {
    return p[0] | (p[1] << 8);
}

/* ========== VGM Header ========== */
typedef struct {
    uint32_t version;
    uint32_t eof_offset;
    uint32_t data_offset;
    uint32_t loop_offset;
    uint32_t loop_samples;
    uint32_t total_samples;
    char     gd3_track[256];
    char     gd3_game[256];
} vgm_header_t;

static bool parse_gd3(const uint8_t* data, size_t len, vgm_header_t* hdr) {
    if (len < 0x14 + 4) return false;
    uint32_t gd3_rel = read_le32(data + 0x14);
    uint32_t gd3_off = gd3_rel ? (gd3_rel + 0x14) : 0;
    if (!gd3_off || gd3_off + 12 > len) return false;

    if (memcmp(data + gd3_off, "Gd3 ", 4) != 0) return false;
    uint32_t str_len = read_le32(data + gd3_off + 8);
    if (gd3_off + 12 + str_len > len) return false;

    /* Parse UTF-16LE string fields: Track(JP), Track(EN), Game(JP), Game(EN) */
    const uint8_t* str = data + gd3_off + 12;
    const uint8_t* end = str + str_len;
    int field = 0;
    char buf[256];
    int blen = 0;

    while (str + 1 < end && field < 4) {
        uint16_t ch = str[0] | (str[1] << 8);
        str += 2;
        if (ch == 0) {
            buf[blen] = 0;
            blen = 0;
            if (field == 1 && !hdr->gd3_track[0])
                strncpy(hdr->gd3_track, buf, sizeof(hdr->gd3_track) - 1);
            if (field == 3 && !hdr->gd3_game[0])
                strncpy(hdr->gd3_game, buf, sizeof(hdr->gd3_game) - 1);
            field++;
        } else if (ch < 128 && blen < 255) {
            buf[blen++] = (char)ch;
        }
    }
    return true;
}

static bool parse_vgm_header(const uint8_t* data, size_t len, vgm_header_t* hdr) {
    if (len < 0x40 || memcmp(data, "Vgm ", 4) != 0) return false;

    memset(hdr, 0, sizeof(*hdr));
    hdr->version = read_le32(data + 0x08);
    hdr->eof_offset = read_le32(data + 0x04) + 4;

    if (len > 0x18) hdr->total_samples = read_le32(data + 0x18);
    if (len > 0x1C) {
        uint32_t loop_rel = read_le32(data + 0x1C);
        hdr->loop_offset = loop_rel ? (loop_rel + 0x1C) : 0;
    }
    if (len > 0x20) hdr->loop_samples = read_le32(data + 0x20);

    /* Data offset */
    hdr->data_offset = 0x40;  /* VGM < 1.50 default */
    if (hdr->version >= 0x150 && len > 0x34) {
        uint32_t d = read_le32(data + 0x34);
        if (d > 0) hdr->data_offset = d + 0x34;
    }

    parse_gd3(data, len, hdr);
    return true;
}

/* ========== VGM Stats ========== */
typedef struct {
    int scc, ay, wait, other;
    uint32_t total_wait_samples;
    double duration;
} vgm_stats_t;

static void scan_vgm_stats(const uint8_t* data, size_t len, const vgm_header_t* hdr, vgm_stats_t* stats) {
    memset(stats, 0, sizeof(*stats));
    size_t pos = hdr->data_offset;
    size_t end = hdr->eof_offset < len ? hdr->eof_offset : len;

    while (pos < end) {
        uint8_t b = data[pos++];
        if (b == 0x66) break;
        if (b == 0xD2) { stats->scc++; if (pos + 3 <= end) pos += 3; }
        else if (b == 0xA0) { stats->ay++; if (pos + 2 <= end) pos += 2; }
        else if (b == 0x61 && pos + 2 <= end) {
            stats->total_wait_samples += read_le16(data + pos);
            stats->wait++; pos += 2;
        }
        else if (b == 0x62) { stats->total_wait_samples += 735; stats->wait++; }
        else if (b == 0x63) { stats->total_wait_samples += 882; stats->wait++; }
        else if (b >= 0x70 && b <= 0x7F) { stats->total_wait_samples += (b & 0x0F) + 1; stats->wait++; }
        else if (b >= 0x80 && b <= 0x8F) { stats->total_wait_samples += (b & 0x0F) + 1; stats->wait++; }
        else if (b >= 0x90 && b <= 0x9F) { stats->total_wait_samples += (b & 0x0F) * 2 + 1; stats->wait++; }
        else {
            stats->other++;
            uint8_t skip = VGM_CMD_LEN[b];
            if (skip > 1 && pos + skip - 1 <= end) pos += skip - 1;
        }
    }
    stats->duration = (double)stats->total_wait_samples / SAMPLES_PER_SEC;
}

/* ========== VGM Dump ========== */
static void dump_vgm(const uint8_t* data, size_t len, const vgm_header_t* hdr) {
    size_t pos = hdr->data_offset;
    size_t end = hdr->eof_offset < len ? hdr->eof_offset : len;
    int count = 0;

    while (pos < end && count < 100) {
        uint8_t b = data[pos++];
        if (b == 0x66) { printf("  END\n"); break; }
        else if (b == 0xD2 && pos + 3 <= end) {
            printf("  SCC  port=%02X reg=%02X data=%02X\n", data[pos], data[pos+1], data[pos+2]);
            pos += 3;
        }
        else if (b == 0xA0 && pos + 2 <= end) {
            printf("  AY   reg=%02X data=%02X\n", data[pos], data[pos+1]);
            pos += 2;
        }
        else if (b == 0x61 && pos + 2 <= end) {
            printf("  WAIT %u samples\n", read_le16(data + pos));
            pos += 2;
        }
        else if (b == 0x62) { printf("  WAIT 735 (60Hz)\n"); }
        else if (b == 0x63) { printf("  WAIT 882 (50Hz)\n"); }
        else if (b >= 0x70 && b <= 0x7F) { printf("  WAIT %d\n", (b & 0xF) + 1); }
        else {
            uint8_t skip = VGM_CMD_LEN[b];
            if (skip > 1 && pos + skip - 1 <= end) pos += skip - 1;
        }
        count++;
    }
}

/* ========== Multimedia Timer VGM Playback ========== */
/*
 * RPFM VGMPlay pattern:
 * 1. timeSetEvent(1, 1, callback, mmEvent, TIME_PERIODIC | TIME_CALLBACK_EVENT_SET)
 * 2. Loop: WaitForSingleObject(mmEvent), QPC elapsed → samples to process
 * 3. Process VGM commands until caught up
 * 4. timeKillEvent on exit
 */

static volatile int g_stop = 0;

static void CALLBACK mm_callback(UINT uID, UINT uMsg, DWORD_PTR dwUser, DWORD_PTR dw1, DWORD_PTR dw2) {
    (void)uID; (void)uMsg; (void)dwUser; (void)dw1; (void)dw2;
    HANDLE hEvent = (HANDLE)dwUser;
    if (hEvent) SetEvent(hEvent);
}

static void play_vgm(const vgm_header_t* hdr, const vgm_stats_t* stats, double speed, bool loop) {
    printf("  GD3: %s\n", hdr->gd3_track[0] ? hdr->gd3_track : "?");
    if (hdr->gd3_game[0]) printf("  Game: %s\n", hdr->gd3_game);
    printf("  Duration: %.1fs @44100Hz\n", stats->duration);
    printf("  Data: %u bytes\n", (unsigned)(g_vgm_len - hdr->data_offset));
    printf("  SCC:%d AY:%d Wait:%d\n", stats->scc, stats->ay, stats->wait);
    printf("  Speed: %.1fx%s\n", speed, loop ? " [LOOP]" : "");
    printf("\n");

    /* QPC frequency */
    LARGE_INTEGER perfFreq;
    QueryPerformanceFrequency(&perfFreq);
    double samplesPerTick = (double)SAMPLES_PER_SEC / perfFreq.QuadPart;

    /* Create 1ms periodic multimedia timer */
    HANDLE mmEvent = CreateEvent(NULL, FALSE, FALSE, NULL);
    if (!mmEvent) { printf("Error: CreateEvent failed\n"); return; }

    MMRESULT timerId = timeSetEvent(1, 1, mm_callback, (DWORD_PTR)mmEvent,
                                     TIME_PERIODIC | TIME_CALLBACK_EVENT_SET);
    if (!timerId) {
        printf("Error: timeSetEvent failed (multimedia timer unavailable)\n");
        CloseHandle(mmEvent);
        return;
    }

    LARGE_INTEGER last;
    QueryPerformanceCounter(&last);
    double samplesToProcess = 0.0;

    g_stop = 0;
    uint32_t currentSamples = 0;
    size_t pos = hdr->data_offset;
    size_t end = hdr->eof_offset < g_vgm_len ? hdr->eof_offset : g_vgm_len;
    uint32_t scc_sent = 0, ay_sent = 0;

    while (!g_stop) {
        /* Wait for 1ms tick */
        WaitForSingleObject(mmEvent, INFINITE);

        if (g_stop) break;

        LARGE_INTEGER now;
        QueryPerformanceCounter(&now);
        double elapsed = (double)(now.QuadPart - last.QuadPart);
        samplesToProcess += elapsed * samplesPerTick;
        last = now;

        /* Apply speed: how many VGM samples worth of commands we can send */
        double budget = samplesToProcess / speed;

        /* Process VGM commands until budget exhausted or we hit a wait */
        while (budget >= 1.0 && pos < end && !g_stop) {
            uint8_t b = g_vgm[pos++];

            if (b == 0x66) {
                /* End of data */
                if (loop && hdr->loop_offset > 0) {
                    pos = hdr->loop_offset;
                    continue;
                }
                goto done;
            }

            if (b == 0xD2) {
                /* SCC: [0xD2][port][reg][data] → send all 4 bytes */
                if (pos + 3 <= end) {
                    serial_write(g_vgm + pos - 1, 4);
                    pos += 3;
                }
            }
            else if (b == 0xA0) {
                /* AY: [0xA0][reg][data] → send all 3 bytes */
                if (pos + 2 <= end) {
                    serial_write(g_vgm + pos - 1, 3);
                    pos += 2;
                }
            }
            else if (b == 0x61) {
                /* Wait N samples */
                if (pos + 2 <= end) {
                    uint16_t n = read_le16(g_vgm + pos);
                    pos += 2;
                    budget -= n;
                    currentSamples += n;
                }
            }
            else if (b == 0x62) {
                budget -= 735;
                currentSamples += 735;
            }
            else if (b == 0x63) {
                budget -= 882;
                currentSamples += 882;
            }
            else if (b >= 0x70 && b <= 0x7F) {
                int n = (b & 0x0F) + 1;
                budget -= n;
                currentSamples += n;
            }
            else if (b >= 0x80 && b <= 0x8F) {
                int n = (b & 0x0F) + 1;
                budget -= n;
                currentSamples += n;
            }
            else if (b >= 0x90 && b <= 0x9F) {
                int n = (b & 0x0F) * 2 + 1;
                budget -= n;
                currentSamples += n;
            }
            else if (b == 0x67) {
                /* Data block: skip */
                if (pos + 3 <= end) {
                    uint32_t sz = g_vgm[pos] | (g_vgm[pos+1] << 8) | (g_vgm[pos+2] << 16);
                    pos += 3 + sz;
                }
            }
            else {
                /* Unknown: skip by length */
                uint8_t skip = VGM_CMD_LEN[b];
                if (skip > 1 && pos + skip - 1 <= end) pos += skip - 1;
            }
        }

        /* Remaining budget → carry over as unprocessed samples */
        samplesToProcess = budget * speed;
    }

done:
    timeKillEvent(timerId);
    CloseHandle(mmEvent);

    double elapsedSec = (double)currentSamples / SAMPLES_PER_SEC / speed;
    printf("  [END] %.1fs\n", elapsedSec);
}

/* ========== File Loading ========== */
static bool load_vgm(const char* filepath) {
    if (g_vgm) { free(g_vgm); g_vgm = NULL; g_vgm_len = 0; }

    FILE* f = fopen(filepath, "rb");
    if (!f) { printf("Error: cannot open %s\n", filepath); return false; }

    /* Read header to check for VGZ */
    uint8_t hdr[2];
    if (fread(hdr, 1, 2, f) != 2) { fclose(f); return false; }

    if (hdr[0] == 0x1F && hdr[1] == 0x8B) {
        /* VGZ: decompress with zlib */
        fclose(f);
        f = fopen(filepath, "rb");
        if (!f) return false;

        fseek(f, 0, SEEK_END);
        long fsize = ftell(f);
        fseek(f, 0, SEEK_SET);

        uint8_t* compressed = (uint8_t*)malloc(fsize);
        if (!compressed || (long)fread(compressed, 1, fsize, f) != fsize) {
            free(compressed); fclose(f); return false;
        }
        fclose(f);

        /* zlib inflate (gzip format) */
        z_stream strm;
        memset(&strm, 0, sizeof(strm));
        if (inflateInit2(&strm, 15 + 32) != Z_OK) { free(compressed); return false; }

        size_t cap = fsize * 4;
        g_vgm = (uint8_t*)malloc(cap);
        if (!g_vgm) { inflateEnd(&strm); free(compressed); return false; }

        strm.next_in = compressed;
        strm.avail_in = fsize;

        int ret;
        do {
            if (strm.total_out >= cap) {
                cap *= 2;
                uint8_t* newp = (uint8_t*)realloc(g_vgm, cap);
                if (!newp) { inflateEnd(&strm); free(g_vgm); g_vgm = NULL; free(compressed); return false; }
                g_vgm = newp;
            }
            strm.next_out = g_vgm + strm.total_out;
            strm.avail_out = cap - strm.total_out;
            ret = inflate(&strm, Z_NO_FLUSH);
        } while (ret == Z_OK);

        inflateEnd(&strm);
        free(compressed);

        if (ret != Z_STREAM_END) {
            free(g_vgm); g_vgm = NULL; return false;
        }
        g_vgm_len = strm.total_out;
    } else {
        /* Plain VGM */
        fseek(f, 0, SEEK_END);
        long fsize = ftell(f);
        fseek(f, 0, SEEK_SET);

        g_vgm = (uint8_t*)malloc(fsize);
        if (!g_vgm) { fclose(f); return false; }
        if ((long)fread(g_vgm, 1, fsize, f) != fsize) {
            free(g_vgm); g_vgm = NULL; fclose(f); return false;
        }
        g_vgm_len = fsize;
        fclose(f);
    }
    return true;
}

/* ========== Serial Port Detection ========== */
static bool detect_serial_port(char* port, int bufsize) {
    /* Try COM ports 1-20 */
    for (int i = 1; i <= 20; i++) {
        char name[16];
        snprintf(name, sizeof(name), "\\\\.\\COM%d", i);
        HANDLE h = CreateFileA(name, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                               OPEN_EXISTING, 0, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            CloseHandle(h);
            snprintf(port, bufsize, "COM%d", i);
            return true;
        }
    }
    return false;
}

/* ========== File Browser ========== */
typedef struct {
    char name[256];
    char fullpath[MAX_PATH_LEN];
    bool is_dir;
} file_entry_t;

static int compare_entries(const void* a, const void* b) {
    return _stricmp(((const file_entry_t*)a)->name, ((const file_entry_t*)b)->name);
}

static int find_vgm_files(const char* vgm_dir, file_entry_t** out) {
    int count = 0;
    int cap = 64;
    file_entry_t* entries = (file_entry_t*)malloc(cap * sizeof(file_entry_t));

    /* Helper to add an entry, dedup by name stem (before .vgm/.vgz) */
    auto add_entry = [&](const char* filename) -> void {
        /* Extract name stem (without .vgm/.vgz) for dedup */
        char stem[256];
        strncpy(stem, filename, 255);
        stem[255] = 0;
        char* dot = strrchr(stem, '.');
        if (dot) *dot = 0;

        /* Check dedup */
        for (int i = 0; i < count; i++) {
            char existing_stem[256];
            strncpy(existing_stem, entries[i].name, 255);
            existing_stem[255] = 0;
            char* ed = strrchr(existing_stem, '.');
            if (ed) *ed = 0;
            if (_stricmp(existing_stem, stem) == 0) return; /* duplicate */
        }

        if (count >= cap) {
            cap *= 2;
            file_entry_t* newp = (file_entry_t*)realloc(entries, cap * sizeof(file_entry_t));
            if (!newp) return;
            entries = newp;
        }

        strncpy(entries[count].name, filename, 255);
        entries[count].name[255] = 0;
        snprintf(entries[count].fullpath, MAX_PATH_LEN, "%s\\%s", vgm_dir, filename);
        entries[count].is_dir = false;
        count++;
    };

    /* Scan *.vgm */
    char pattern[MAX_PATH_LEN];
    snprintf(pattern, sizeof(pattern), "%s\\*.vgm", vgm_dir);
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do {
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
            add_entry(fd.cFileName);
        } while (FindNextFileA(h, &fd));
        FindClose(h);
    }

    /* Scan *.vgz */
    snprintf(pattern, sizeof(pattern), "%s\\*.vgz", vgm_dir);
    h = FindFirstFileA(pattern, &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do {
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
            add_entry(fd.cFileName);
        } while (FindNextFileA(h, &fd));
        FindClose(h);
    }

    qsort(entries, count, sizeof(file_entry_t), compare_entries);
    *out = entries;
    return count;
}

/* ========== Ctrl+C Handler ========== */
static BOOL WINAPI ctrl_handler(DWORD type) {
    (void)type;
    g_stop = 1;
    return TRUE;
}

/* ========== Main ========== */
static void usage(void) {
    printf("VGM Player for STC8H SCC Synth\n\n");
    printf("Usage:\n");
    printf("  vgm_player.exe --list                    List songs\n");
    printf("  vgm_player.exe <number|name> [options]    Play a song\n");
    printf("  vgm_player.exe --dump <number>           Dump VGM commands\n\n");
    printf("Options:\n");
    printf("  --port COMx      Serial port (auto-detect)\n");
    printf("  --baud N         Baud rate (default %d)\n", DEFAULT_BAUD);
    printf("  --speed N        Playback speed (default 1.0)\n");
    printf("  --loop           Loop playback\n");
    printf("  --vgm-dir PATH   VGM directory (default: %s)\n", VGM_DIR_DEFAULT);
    printf("  --help           Show this help\n");
}

int main(int argc, char* argv[]) {
    SetConsoleCtrlHandler(ctrl_handler, TRUE);
    SetConsoleOutputCP(65001);

    const char* song_sel = NULL;
    const char* port_arg = NULL;
    int baud = DEFAULT_BAUD;
    double speed = 1.0;
    bool do_list = false;
    bool do_dump = false;
    bool do_loop = false;
    const char* vgm_dir = VGM_DIR_DEFAULT;

    /* Parse args */
    for (int i = 1; i < argc; i++) {
        if (_stricmp(argv[i], "--list") == 0) { do_list = true; }
        else if (_stricmp(argv[i], "--dump") == 0) {
            do_dump = true;
            if (i + 1 < argc) { song_sel = argv[++i]; }
        }
        else if (_stricmp(argv[i], "--port") == 0 && i + 1 < argc) { port_arg = argv[++i]; }
        else if (_stricmp(argv[i], "--baud") == 0 && i + 1 < argc) { baud = atoi(argv[++i]); }
        else if (_stricmp(argv[i], "--speed") == 0 && i + 1 < argc) { speed = atof(argv[++i]); }
        else if (_stricmp(argv[i], "--loop") == 0) { do_loop = true; }
        else if (_stricmp(argv[i], "--vgm-dir") == 0 && i + 1 < argc) { vgm_dir = argv[++i]; }
        else if (_stricmp(argv[i], "--help") == 0) { usage(); return 0; }
        else if (argv[i][0] != '-') { song_sel = argv[i]; }
        else { printf("Unknown option: %s\n\n", argv[i]); usage(); return 1; }
    }

    if (do_list) {
        /* List songs */
        file_entry_t* entries;
        int count = find_vgm_files(vgm_dir, &entries);

        if (count == 0) {
            printf("No .vgm/.vgz files in %s/\n", vgm_dir);
            return 0;
        }

        printf("\n%3s  %-50s %8s  %8s  %s\n", "#", "File", "Size", "Duration", "Info");
        printf("%s\n", "------------------------------------------------------------------------------------------------------");

        for (int i = 0; i < count; i++) {
            /* Get file size */
            DWORD sz = 0;
            HANDLE hf = CreateFileA(entries[i].fullpath, GENERIC_READ, FILE_SHARE_READ,
                                    NULL, OPEN_EXISTING, 0, NULL);
            if (hf != INVALID_HANDLE_VALUE) {
                sz = GetFileSize(hf, NULL);
                CloseHandle(hf);
            }

            /* Parse for stats */
            printf("%3d  %-50s %8d  ", i + 1, entries[i].name, sz);
            if (load_vgm(entries[i].fullpath)) {
                vgm_header_t hdr;
                vgm_stats_t stats;
                if (parse_vgm_header(g_vgm, g_vgm_len, &hdr)) {
                    scan_vgm_stats(g_vgm, g_vgm_len, &hdr, &stats);
                    printf("%6.1fs  SCC:%d AY:%d", stats.duration, stats.scc, stats.ay);
                    if (hdr.gd3_track[0]) {
                        char short_name[50];
                        /* Truncate GD3 for display */
                        strncpy(short_name, hdr.gd3_track, 49);
                        short_name[49] = 0;
                        printf("  [%s]", short_name);
                    }
                } else {
                    printf("    ?     ?");
                }
                free(g_vgm); g_vgm = NULL;
            } else {
                printf("    ?     ?");
            }
            printf("\n");
        }

        free(entries);
        return 0;
    }

    if (!song_sel) {
        usage();
        return 1;
    }

    /* Resolve song */
    file_entry_t* entries;
    int count = find_vgm_files(vgm_dir, &entries);
    const char* filepath = NULL;

    /* Try numeric index */
    int idx = atoi(song_sel);
    if (idx > 0 && idx <= count) {
        filepath = entries[idx - 1].fullpath;
    } else {
        /* Try substring match */
        for (int i = 0; i < count; i++) {
            if (strstr(entries[i].name, song_sel)) {
                filepath = entries[i].fullpath;
                break;
            }
        }
    }

    if (!filepath) {
        printf("Song not found: '%s'\n", song_sel);
        free(entries);
        return 1;
    }

    printf("Loading: %s\n", entries[idx > 0 ? idx - 1 : 0].name);

    free(entries);

    /* Load VGM */
    if (!load_vgm(filepath)) {
        printf("Error: failed to load VGM\n");
        return 1;
    }

    vgm_header_t hdr;
    if (!parse_vgm_header(g_vgm, g_vgm_len, &hdr)) {
        printf("Error: not a VGM file\n");
        free(g_vgm);
        return 1;
    }

    vgm_stats_t stats;
    scan_vgm_stats(g_vgm, g_vgm_len, &hdr, &stats);

    if (do_dump) {
        dump_vgm(g_vgm, g_vgm_len, &hdr);
        free(g_vgm);
        return 0;
    }

    /* Open serial port */
    char port[16];
    if (port_arg) {
        strncpy(port, port_arg, 15);
        port[15] = 0;
    } else if (!detect_serial_port(port, sizeof(port))) {
        printf("Error: no serial port found. Use --port COMx\n");
        free(g_vgm);
        return 1;
    }

    printf("Serial: %s @ %d baud\n", port, baud);

    if (!serial_open(port, baud)) {
        printf("Error: cannot open %s\n", port);
        free(g_vgm);
        return 1;
    }

    /* Play */
    play_vgm(&hdr, &stats, speed, do_loop);

    serial_close();
    free(g_vgm);
    return 0;
}
