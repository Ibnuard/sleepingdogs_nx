"""Compose conservative deferred-context overlap with a Compact/Inline bridge.

The generated source remains ABI-compatible. Only Present drops the global
registry gate, with an independent native reference. No asynchronous requests
or guest pointer retention are introduced. An active Present admits only
methods on verified deferred contexts and their BindMap/AbortMap lifecycle;
shutdown and all other objects wait.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HEADER=ROOT/'src/native_dxvk_com/present_overlap.h'


def once(text,before,after):
    assert text.count(before)==1,repr(before)
    return text.replace(before,after)


def native(text):
    text=once(text,'#include "com_protocol.h"',
              '#include "com_protocol.h"\n#include "present_overlap.h"')
    text=once(text,'    std::recursive_mutex mutex;',
              '    std::recursive_mutex mutex;\n    SdPresentOverlap present_overlap;')
    text=once(text,'Context state;', '''Context state;
thread_local std::unique_lock<std::recursive_mutex>* present_dispatch_lock=nullptr;
thread_local unsigned present_dispatch_depth=0;
struct PresentDispatchScope {
    std::unique_lock<std::recursive_mutex>* previous;
    explicit PresentDispatchScope(std::unique_lock<std::recursive_mutex>& lock)
      :previous(present_dispatch_lock){present_dispatch_lock=&lock;++present_dispatch_depth;}
    ~PresentDispatchScope(){--present_dispatch_depth;present_dispatch_lock=previous;}
};
bool present_overlap_deferred(Context& c,const sd_com_packet& p) {
    if(!p.interface_id && (p.method==SD_COM_BIND_MAP || p.method==SD_COM_ABORT_MAP)) {
        auto found=c.maps.find(p.args[0]);
        return found!=c.maps.end() && found->second.context->GetType()==D3D11_DEVICE_CONTEXT_DEFERRED;
    }
    if(p.interface_id!=SD_COM_IF_ID3D11DeviceContext || p.method<3)return false;
    // Query the native object's actual kind while its registry slot is locked.
    // Invalid/stale tokens take the normal checked dispatcher failure path.
    try {
        auto context=c.object<ID3D11DeviceContext>(p.object,SD_COM_IF_ID3D11DeviceContext);
        return context && context->GetType()==D3D11_DEVICE_CONTEXT_DEFERRED;
    } catch(const Fault&) {return false;}
}''')
    text=once(text,'''    std::lock_guard<std::recursive_mutex> guard(state.mutex);
    progress.waiting.fetch_sub(1);''', '''    std::unique_lock<std::recursive_mutex> guard(state.mutex);
    progress.waiting.fetch_sub(1);
    PresentDispatchScope present_scope(guard);''')
    text=once(text,'    ProgressCall watch;\n    uintptr_t address=',
              '    uintptr_t address=')
    text=once(text,'        ++state.calls;', '''        if(state.present_overlap.active) {
            bool deferred=present_overlap_deferred(state,p);
            if(!deferred)progress.waiting.fetch_add(1);
            bool admitted=state.present_overlap.admit(guard,deferred,present_dispatch_depth>1);
            if(!deferred)progress.waiting.fetch_sub(1);
            if(!admitted)return int32_t(0xc000000du); // Do not deadlock nested Present callbacks.
        }
        ProgressCall watch;
        ++state.calls;''')
    text=once(text,'void sd_com_shutdown(){std::lock_guard<std::recursive_mutex> guard(state.mutex);state.shutdown();}',
              '''void sd_com_shutdown(){
    std::unique_lock<std::recursive_mutex> guard(state.mutex);
    if(!state.present_overlap.admit(guard,false,present_dispatch_depth!=0))return;
    state.shutdown();
}''')
    # A deferred worker may publish its own snapshot while Present is unlocked.
    # The adapter restores the presenting caller's snapshot before its result.
    marker='        wine_nx_runtime_trace(line);\n    }\n    void abort_map'
    text=once(text,marker,'''        wine_nx_runtime_trace(line);
        std::snprintf(line,sizeof(line),"[SD-NDX-OVERLAP] v1 released=%llu deferred_admitted=%llu serialized_waits=%llu; real FPS requires hardware validation",
            (unsigned long long)present_overlap.released,(unsigned long long)present_overlap.admitted,
            (unsigned long long)present_overlap.waited);
        wine_nx_runtime_trace(line);
    }
    void abort_map''')
    return text


def adapters(text):
    return once(text,'''template<typename T> void custom_IDXGISwapChain_Present(Context& c,T* object,sd_com_packet& p) {
    p.ret=object->Present(p.args[0],p.args[1]);''', '''template<typename T> void custom_IDXGISwapChain_Present(Context& c,T* object,sd_com_packet& p) {
    if(!object)throw Fault(E_INVALIDARG);
    if(present_dispatch_lock && present_dispatch_depth==1 && entered_multithread.empty() &&
       !c.present_overlap.active && !(p.args[1]&DXGI_PRESENT_TEST)) {
        auto presenting_snapshot=progress_values;
        try {
            p.ret=c.present_overlap.invoke(*present_dispatch_lock,object,[&] {
                return object->Present(p.args[0],p.args[1]);
            });
        } catch(...) {progress_values=presenting_snapshot;throw;}
        progress_values=presenting_snapshot;
    } else p.ret=object->Present(p.args[0],p.args[1]);''')


def prepare(source):
    source=Path(source)
    (source/'com_native.cpp').write_text(native((source/'com_native.cpp').read_text()),newline='\n')
    (source/'com_native_adapters.inc').write_text(adapters((source/'com_native_adapters.inc').read_text()),newline='\n')
    (source/'present_overlap.h').write_bytes(HEADER.read_bytes())
