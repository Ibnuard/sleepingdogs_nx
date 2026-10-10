/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <unordered_map>
#include <vector>

// A bounded, checksummed SPIR-V pack made from the user's own LSFG 3.1 DLL.
// The DLL is never loaded as executable code. All disk input is checked before
// reaching the shader patcher or Vulkan driver.
inline std::unordered_map<uint32_t,std::vector<uint8_t>> sd_lsfg_read_pack(
        const std::filesystem::path& path) {
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if (!in) throw std::runtime_error("shader pack missing: lsfg/lsfg-3.1.sdp");
    const auto size=in.tellg();
    if (size<48 || size>16*1024*1024) throw std::runtime_error("invalid shader pack size");
    std::vector<uint8_t> data(static_cast<size_t>(size));
    in.seekg(0);in.read(reinterpret_cast<char*>(data.data()),size);
    if (!in) throw std::runtime_error("cannot read shader pack");
    auto u32=[&](size_t n) {
        if (n>data.size()-4) throw std::runtime_error("truncated shader pack");
        return uint32_t(data[n])|(uint32_t(data[n+1])<<8)|
               (uint32_t(data[n+2])<<16)|(uint32_t(data[n+3])<<24);
    };
    static const uint8_t expected_dll[32]={0x8b,0x7d,0xbc,0x11,0xb2,0xea,0x54,0x46,
        0x50,0xaf,0x2e,0xd4,0xff,0xc9,0x2d,0xa3,0xab,0xd8,0x8e,0xc5,0xaf,0xa0,0x9c,0x36,
        0x48,0x4c,0x06,0x0f,0xbc,0x84,0x88,0x34};
    if (std::memcmp(data.data(),"SDLSFG15",8) || u32(8)!=1 || u32(12)!=45 ||
        std::memcmp(data.data()+16,expected_dll,32))
        throw std::runtime_error("unsupported shader pack version");
    std::unordered_map<uint32_t,std::vector<uint8_t>> result;
    size_t offset=48;
    for (unsigned i=0;i<45;++i) {
        if (offset>data.size()-12) throw std::runtime_error("truncated shader record");
        uint32_t id=u32(offset),n=u32(offset+4),checksum=u32(offset+8);offset+=12;
        if (id<354 || id>399 || id==377 || result.count(id) || n<20 || n%4 || n>1024*1024 || n>data.size()-offset)
            throw std::runtime_error("invalid shader record");
        uint32_t hash=2166136261u;
        for (size_t j=offset;j<offset+n;++j) hash=(hash^data[j])*16777619u;
        if (hash!=checksum || u32(offset)!=0x07230203 || u32(offset+16))
            throw std::runtime_error("corrupt shader record");
        for (size_t j=20;j<n;) {
            uint32_t words=u32(offset+j)>>16;
            if (!words || words>(n-j)/4) throw std::runtime_error("invalid SPIR-V instruction");
            j+=words*4;
        }
        result.emplace(id,std::vector<uint8_t>(data.begin()+offset,data.begin()+offset+n));
        offset+=n;
    }
    if (offset!=data.size()) throw std::runtime_error("unexpected shader pack data");
    return result;
}
