// DXBC compiler from PancakeTAS/dxbc (DXVK); host-only conversion utility.
// Bind original D3D registers to the GPL LSFG-VK 2.0 backend layout.
#include <dxbc_module.h>
#include <dxbc_reader.h>
#include <dxbc_modinfo.h>
#include <thirdparty/spirv.hpp>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>
#include <unordered_map>

int main(int argc, char **argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: lsfg_translate input.dxbc output.spv");
        std::ifstream input(argv[1], std::ios::binary);
        std::vector<char> bytes((std::istreambuf_iterator<char>(input)), {});
        if (bytes.size() < 32) throw std::runtime_error("missing/truncated DXBC input");
        dxvk::DxbcReader reader(bytes.data(), bytes.size());
        dxvk::DxbcModule module(reader);
        auto code = module.compile(dxvk::DxbcModuleInfo{}, "CS");
        if (module.icbInfo().size) throw std::runtime_error("external immediate constant buffer unsupported");
        // DXVK assigns separate binding ranges for each D3D register type.
        // Resolve the exact compiler mapping, never infer declaration order.
        std::unordered_map<uint32_t, uint32_t> bindings;
        auto stage = dxvk::DxbcProgramType::ComputeShader;
        for (uint32_t i = 0; i < 16; ++i) {
            bindings.emplace(dxvk::computeConstantBufferBinding(stage, i), i);
            bindings.emplace(dxvk::computeSamplerBinding(stage, i), 16 + i);
            bindings.emplace(dxvk::computeSrvBinding(stage, i), 32 + i);
            bindings.emplace(dxvk::computeUavBinding(stage, i), 48 + i);
        }
        for (auto ins : code) {
            if (ins.opCode() == spv::OpDecorate && ins.arg(2) == spv::DecorationBinding) {
                auto it = bindings.find(ins.arg(3));
                if (it == bindings.end()) throw std::runtime_error("unmapped descriptor binding");
                code.data()[ins.offset() + 3] = it->second;
            }
            if (ins.opCode() == spv::OpDecorate && ins.arg(2) == spv::DecorationDescriptorSet)
                code.data()[ins.offset() + 3] = 0;
        }
        std::ofstream output(argv[2], std::ios::binary);
        output.write(reinterpret_cast<const char*>(code.data()), code.size());
        if (!output) throw std::runtime_error("SPIR-V output write failed");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
