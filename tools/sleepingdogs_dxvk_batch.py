"""Opt-in small-hint batching on the preserved Sleeping Dogs DXVK build."""
from pathlib import Path
from f1_overlay import exact

FILES = {
    'src/util/util_flush.h', 'src/util/util_flush.cpp',
    'src/d3d11/d3d11_options.h', 'src/d3d11/d3d11_options.cpp',
    'src/d3d11/d3d11_context_imm.h', 'src/d3d11/d3d11_context_imm.cpp',
    'version.h.in',
}
BUILD = 'sleepingdogs-dxvk-sdbatch1'
MARKER = '[SD-DXVK-BATCH] v1'
OPTION = 'd3d11.sdSubmissionBatching'


def apply(source: Path):
    def edit(name, changes):
        p = source / name
        s = p.read_text()
        for old, new in changes:
            s = exact(s, old, new)
        p.write_text(s, newline='\n')

    edit('src/util/util_flush.h', [
        ('GpuFlushTracker(GpuFlushType maxAllowed);',
         'GpuFlushTracker(GpuFlushType maxAllowed, bool sdBatching = false);'),
        ('  private:\n\n    GpuFlushType', '''    bool sdBatchingEnabled() const { return m_sdBatching; }
    uint64_t sdDeferredHints() const { return m_sdDeferredHints; }

  private:

    bool         m_sdBatching = false;
    uint64_t     m_sdDeferredHints = 0;

    GpuFlushType'''),
    ])
    edit('src/util/util_flush.cpp', [
        ('GpuFlushTracker::GpuFlushTracker(GpuFlushType maxType)\n  : m_maxType(maxType)',
         'GpuFlushTracker::GpuFlushTracker(GpuFlushType maxType, bool sdBatching)\n'
         '  : m_sdBatching(sdBatching), m_maxType(maxType)'),
        ('    switch (flushType) {', '''    // Sleeping Dogs / GM20B experiment: batch only small automatic hints
    // while at least two submissions are still unfinished. Keep the original
    // decision for explicit flushes, read-back synchronization, a draining
    // GPU queue, large batches and the existing cost safety threshold.
    // Required D3D11 flushes also call ExecuteFlush directly and bypass this.
    if (m_sdBatching
     && (flushType == GpuFlushType::ImplicitStrongHint
      || flushType == GpuFlushType::ImplicitWeakHint)
     && uint32_t(m_lastFlushSubmissionId - lastCompleteSubmissionId) >= 2u
     && chunkCount < 12u
     && estimatedCost < GpuCostEstimate::MaxCostPerSubmission) {
      m_sdDeferredHints++;
      return false;
    }

    switch (flushType) {'''),
    ])
    edit('src/d3d11/d3d11_options.h', [
        ('    D3D11Options(const Config& config);',
         '    D3D11Options(const Config& config);\n\n'
         '    /// Sleeping Dogs Switch experiment; disabled by default.\n'
         '    bool sdSubmissionBatching = false;'),
    ])
    edit('src/d3d11/d3d11_options.cpp', [
        ('  D3D11Options::D3D11Options(const Config& config) {',
         '  D3D11Options::D3D11Options(const Config& config) {\n'
         '    this->sdSubmissionBatching = config.getOption<bool>("'+OPTION+'", false);'),
    ])
    edit('src/d3d11/d3d11_context_imm.h', [
        ('    GpuFlushTracker         m_flushTracker;',
         '    GpuFlushTracker         m_flushTracker;\n'
         '    uint64_t                m_sdFlushes = 0;\n'
         '    uint64_t                m_sdFlushTypes[4] = { };'),
    ])
    edit('src/d3d11/d3d11_context_imm.cpp', [
        ('    m_flushTracker(GetMaxFlushType(pParent, Device)),',
         '    m_flushTracker(GetMaxFlushType(pParent, Device),\n'
         '      pParent->GetOptions()->sdSubmissionBatching\n'
         '      && !pParent->GetOptions()->reproducibleCommandStream\n'
         '      && Device->adapter()->matchesDriver(VK_DRIVER_ID_MESA_NVK)),') ,
        ('    m_destructionNotifier(this) {',
         '    m_destructionNotifier(this) {\n'
         '    Logger::info(str::format("'+MARKER+' enabled=", m_flushTracker.sdBatchingEnabled(),\n'
         '      " hint_chunks=12 min_pending=2; explicit/map/query/present flush paths retained"));'),
        ('    m_hasPendingUnresolvedPass = false;\n\n    // Unbind unused resources',
         '''    // One aggregate line per 256 non-empty context flushes, in both
    // A/B modes. No per-draw logging, timestamp sampling or extra GPU waits.
    m_sdFlushes++;
    if (uint32_t(FlushType) < 4u)
      m_sdFlushTypes[uint32_t(FlushType)]++;
    if ((m_sdFlushes & 255u) == 0u) {
      Logger::info(str::format("''' + MARKER + ''' enabled=", m_flushTracker.sdBatchingEnabled(),
        " flushes=", m_sdFlushes, " explicit=", m_sdFlushTypes[0],
        " sync=", m_sdFlushTypes[1], " strong=", m_sdFlushTypes[2],
        " weak=", m_sdFlushTypes[3], " deferred_hints=", m_flushTracker.sdDeferredHints(),
        "; cumulative, deferred hints are requests not eliminated submissions"));
    }

    m_hasPendingUnresolvedPass = false;

    // Unbind unused resources'''),
    ])
    edit('version.h.in', [('-sdrecycle1', '-sdbatch1')])
