"""Sleeping Dogs' small shared heap: dense chunks and deferred Map OOM handling.

Apply only on the pinned f1mem2 tree. Resource sizes, memory types, mapping,
command-list ownership and GPU synchronization retain their DXVK semantics.
"""
from pathlib import Path
from dxvk_compact_chunks import COMMIT, replace

FILES = ('src/dxvk/dxvk_memory.cpp', 'src/d3d11/d3d11_context_def.cpp', 'version.h.in')
MARKER = '[SD-DXVK-MEM] v1 pool cap=2 MiB; large chunks=aligned resource'


def apply(source: Path):
    p = source / FILES[0]
    s = p.read_text()
    s = replace(s, 'constexpr VkDeviceSize f1ChunkCap = 8u << 20;',
                '''// Keep unused tail space small before the shared native heap fills.
    // The aligned resource floor below is never capped: a 5 MiB discard
    // buffer still receives all 5 MiB, instead of an 8 MiB backing chunk.
    constexpr VkDeviceSize f1ChunkCap = 2u << 20;''')
    s = replace(s, 'return std::min(VkDeviceSize(8u << 20), std::max(size, DxvkMemoryPool::MinChunkSize));',
                'return std::min(VkDeviceSize(2u << 20), std::max(size, DxvkMemoryPool::MinChunkSize));')
    s = replace(s, '[F1-DXVK-MEM] pool cap=8 MiB; exact aligned floor retry enabled', MARKER)
    s = replace(s, '      type.mappedPool.maxChunkSize = determineMaxChunkSize(type, true);',
                '''      type.mappedPool.maxChunkSize = determineMaxChunkSize(type, true);
      type.devicePool.nextChunkSize = std::min(type.devicePool.nextChunkSize, type.devicePool.maxChunkSize);
      type.mappedPool.nextChunkSize = std::min(type.mappedPool.nextChunkSize, type.mappedPool.maxChunkSize);''')
    s = replace(s, '[F1-DXVK-MEM] small chunk recovered: required=',
                '[SD-DXVK-MEM] compact chunk: required=')
    p.write_text(s)

    p = source / FILES[1]
    s = p.read_text()
    s = replace(s, '''    auto bufferSlice = pBuffer->AllocSlice(&m_allocationCache);
    pMappedResource->pData        = bufferSlice->mapPtr();''', '''    auto bufferSlice = pBuffer->AllocSlice(&m_allocationCache);
    if (unlikely(!bufferSlice)) {
      // Preserve failure as an HRESULT. No command or map-cache entry may
      // refer to an allocation that does not exist.
      *pMappedResource = { };
      Logger::err(str::format("[SD-DXVK-MAP] deferred buffer allocation failed: bytes=",
        pBuffer->Desc()->ByteWidth));
      return E_OUTOFMEMORY;
    }
    pMappedResource->pData        = bufferSlice->mapPtr();''')
    s = replace(s, '''      // The caller validates the map mode, so we can
      // safely ignore the MapBuffer return value here
      D3D11_MAPPED_SUBRESOURCE mapInfo;
      MapBuffer(pDstBuffer, &mapInfo);''', '''      // Valid map mode does not guarantee that a new allocation succeeds.
      // MapBuffer logs OOM; this void update cannot copy from a failed map.
      D3D11_MAPPED_SUBRESOURCE mapInfo;
      if (FAILED(MapBuffer(pDstBuffer, &mapInfo)))
        return;''')
    p.write_text(s)
    p = source / FILES[2]
    p.write_text(replace(p.read_text(), '-f1mem2', '-sdmem1'))
