#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <zstd.h>
#include <chrono>
#include <thread>

class CompressionEngine {
public:
    static bool compressFile(const std::string& inputPath, const std::string& outputPath, int compressionLevel = 3) {
        std::ifstream inFile(inputPath, std::ios::binary);
        if (!inFile) return false;

        std::ofstream outFile(outputPath, std::ios::binary);
        if (!outFile) return false;

        ZSTD_CCtx* const cctx = ZSTD_createCCtx();
        if (cctx == nullptr) return false;

        ZSTD_CCtx_setParameter(cctx, ZSTD_c_compressionLevel, compressionLevel);
        ZSTD_CCtx_setParameter(cctx, ZSTD_c_checksumFlag, 1);
        
        unsigned int hw_concur = std::thread::hardware_concurrency();
        ZSTD_CCtx_setParameter(cctx, ZSTD_c_nbWorkers, hw_concur == 0 ? 4 : hw_concur);
        
        if (compressionLevel >= 5) {
            ZSTD_CCtx_setParameter(cctx, ZSTD_c_enableLongDistanceMatching, 1);
        }

        size_t const buffInSize = ZSTD_CStreamInSize() * 16;
        std::vector<char> buffIn(buffInSize);
        size_t const buffOutSize = ZSTD_CStreamOutSize() * 16;
        std::vector<char> buffOut(buffOutSize);

        while (inFile) {
            inFile.read(buffIn.data(), buffIn.size());
            size_t const readSize = inFile.gcount();
            if (readSize == 0) break;

            ZSTD_inBuffer input = { buffIn.data(), readSize, 0 };
            while (input.pos < input.size) {
                ZSTD_outBuffer output = { buffOut.data(), buffOutSize, 0 };
                size_t const remaining = ZSTD_compressStream2(cctx, &output, &input, ZSTD_e_continue);
                if (ZSTD_isError(remaining)) {
                    ZSTD_freeCCtx(cctx);
                    return false;
                }
                outFile.write(buffOut.data(), output.pos);
            }
        }

        ZSTD_inBuffer input = { nullptr, 0, 0 };
        size_t remaining = 1;
        while (remaining != 0) {
            ZSTD_outBuffer output = { buffOut.data(), buffOutSize, 0 };
            remaining = ZSTD_compressStream2(cctx, &output, &input, ZSTD_e_end);
            if (ZSTD_isError(remaining)) {
                ZSTD_freeCCtx(cctx);
                return false;
            }
            outFile.write(buffOut.data(), output.pos);
        }

        ZSTD_freeCCtx(cctx);
        return true;
    }

    static bool decompressFile(const std::string& inputPath, const std::string& outputPath) {
        std::ifstream inFile(inputPath, std::ios::binary);
        if (!inFile) return false;

        std::ofstream outFile(outputPath, std::ios::binary);
        if (!outFile) return false;

        ZSTD_DCtx* const dctx = ZSTD_createDCtx();
        if (dctx == nullptr) return false;

        size_t const buffInSize = ZSTD_DStreamInSize() * 16;
        std::vector<char> buffIn(buffInSize);
        size_t const buffOutSize = ZSTD_DStreamOutSize() * 16;
        std::vector<char> buffOut(buffOutSize);

        while (inFile) {
            inFile.read(buffIn.data(), buffIn.size());
            size_t const readSize = inFile.gcount();
            if (readSize == 0) break;

            ZSTD_inBuffer input = { buffIn.data(), readSize, 0 };
            while (input.pos < input.size) {
                ZSTD_outBuffer output = { buffOut.data(), buffOutSize, 0 };
                size_t const ret = ZSTD_decompressStream(dctx, &output, &input);
                if (ZSTD_isError(ret)) {
                    ZSTD_freeDCtx(dctx);
                    return false;
                }
                outFile.write(buffOut.data(), output.pos);
            }
        }

        ZSTD_freeDCtx(dctx);
        return true;
    }
};

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <mode:c|d> <input> <output> [level:1-22]" << std::endl;
        return 1;
    }

    std::string mode = argv[1];
    std::string input = argv[2];
    std::string output = argv[3];
    int level = (argc > 4) ? std::stoi(argv[4]) : 3;

    auto start = std::chrono::high_resolution_clock::now();

    bool success = false;
    if (mode == "c") {
        success = CompressionEngine::compressFile(input, output, level);
    } else if (mode == "d") {
        success = CompressionEngine::decompressFile(input, output);
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff = end - start;

    if (success) {
        std::cout << "SUCCESS|" << diff.count() << std::endl;
    } else {
        std::cerr << "FAILURE" << std::endl;
        return 1;
    }

    return 0;
}
