#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <zstd.h>
#include <chrono>

/**
 * Zstd Compression Engine
 * Pro-level implementation supporting file and streaming compression.
 */

class CompressionEngine {
public:
    static bool compressFile(const std::string& inputPath, const std::string& outputPath, int compressionLevel = 3) {
        std::ifstream inFile(inputPath, std::ios::binary);
        if (!inFile) return false;

        std::ofstream outFile(outputPath, std::ios::binary);
        if (!outFile) return false;

        // Get file size
        inFile.seekg(0, std::ios::end);
        size_t srcSize = inFile.tellg();
        inFile.seekg(0, std::ios::beg);

        std::vector<char> srcBuffer(srcSize);
        inFile.read(srcBuffer.data(), srcSize);

        size_t const dstCapacity = ZSTD_compressBound(srcSize);
        std::vector<char> dstBuffer(dstCapacity);

        size_t const cSize = ZSTD_compress(dstBuffer.data(), dstCapacity, srcBuffer.data(), srcSize, compressionLevel);
        if (ZSTD_isError(cSize)) {
            std::cerr << "Compression error: " << ZSTD_getErrorName(cSize) << std::endl;
            return false;
        }

        outFile.write(dstBuffer.data(), cSize);
        return true;
    }

    static bool decompressFile(const std::string& inputPath, const std::string& outputPath) {
        std::ifstream inFile(inputPath, std::ios::binary);
        if (!inFile) return false;

        std::ofstream outFile(outputPath, std::ios::binary);
        if (!outFile) return false;

        inFile.seekg(0, std::ios::end);
        size_t srcSize = inFile.tellg();
        inFile.seekg(0, std::ios::beg);

        std::vector<char> srcBuffer(srcSize);
        inFile.read(srcBuffer.data(), srcSize);

        unsigned long long const rSize = ZSTD_getFrameContentSize(srcBuffer.data(), srcSize);
        if (rSize == ZSTD_CONTENTSIZE_ERROR || rSize == ZSTD_CONTENTSIZE_UNKNOWN) {
            std::cerr << "Invalid compressed file content size." << std::endl;
            return false;
        }

        std::vector<char> dstBuffer(rSize);
        size_t const dSize = ZSTD_decompress(dstBuffer.data(), rSize, srcBuffer.data(), srcSize);
        if (ZSTD_isError(dSize)) {
            std::cerr << "Decompression error: " << ZSTD_getErrorName(dSize) << std::endl;
            return false;
        }

        outFile.write(dstBuffer.data(), dSize);
        return true;
    }

    // Streaming Compression Example (could be expanded)
    static void streamCompress() {
        ZSTD_CStream* const cstream = ZSTD_createCStream();
        ZSTD_initCStream(cstream, 3);

        size_t const buffInSize = ZSTD_CStreamInSize();
        void* const buffIn = malloc(buffInSize);
        size_t const buffOutSize = ZSTD_CStreamOutSize();
        void* const buffOut = malloc(buffOutSize);

        size_t read;
        while ((read = fread(buffIn, 1, buffInSize, stdin))) {
            ZSTD_inBuffer input = { buffIn, read, 0 };
            while (input.pos < input.size) {
                ZSTD_outBuffer output = { buffOut, buffOutSize, 0 };
                ZSTD_compressStream(cstream, &output, &input);
                fwrite(buffOut, 1, output.pos, stdout);
            }
        }

        ZSTD_outBuffer output = { buffOut, buffOutSize, 0 };
        ZSTD_endStream(cstream, &output);
        fwrite(buffOut, 1, output.pos, stdout);

        free(buffIn);
        free(buffOut);
        ZSTD_freeCStream(cstream);
    }
};

int main(int argc, char* argv[]) {
    if (argc < 4) {
        if (argc == 2 && std::string(argv[1]) == "--stream") {
            CompressionEngine::streamCompress();
            return 0;
        }
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
