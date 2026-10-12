"""Host tests for the composable Present gate change, including real DXVK.

Run under WSL. A test-only barrier pauses the raw native Present after the
registry gate has opened; a real deferred Map/BindMap/Unmap/Finish round trip
must finish while immediate/global operations remain blocked. The finished
command list is then executed and its complete upload read back through GPU.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from native_dxvk_present_overlap import prepare

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

HOOK='''
#include <future>
std::atomic<bool> overlap_test_block{false},overlap_test_entered{false},overlap_test_finish{false};
std::atomic<bool> overlap_test_nested{false};
std::atomic<unsigned> overlap_test_nested_checked{0};
uint32_t overlap_test_immediate=0;
extern "C" uint64_t sd_overlap_test_waited();
extern "C" uint64_t sd_overlap_test_released();
extern "C" void sd_overlap_test_hook(){
    if(!overlap_test_block.exchange(false))return;
    overlap_test_entered=true;
    while(!overlap_test_finish.load())std::this_thread::yield();
}
extern "C" void sd_overlap_test_deferred_hook(){
    if(!overlap_test_nested.exchange(false))return;
    Client x(11);*x.packet={SD_COM_ABI,overlap_test_immediate,SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_GetType};
    require(wine_nx_sd_com_wow64_unix_funcs[0](x.packet)==int32_t(0xc000000du),"foreign nested callback must fail without recursive wait");
    ++overlap_test_nested_checked;
}
'''

SCENARIO='''
        uint64_t release_count_before=sd_overlap_test_released();
        auto overlap_mt=query(c,context,__uuidof(ID3D10Multithread));
        c.call(SD_COM_IF_ID3D10Multithread,SD_COM_M_ID3D10Multithread_Enter,overlap_mt);
        require(c.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_Present,swap,{1,0})==S_OK);
        require(sd_overlap_test_released()==release_count_before,"Present inside explicit Enter unexpectedly released gate");
        c.call(SD_COM_IF_ID3D10Multithread,SD_COM_M_ID3D10Multithread_Leave,overlap_mt);c.release(overlap_mt);
        uint32_t deferred_context=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateDeferredContext,device,{0,address(out)},out);
        auto finished=allocate<uint32_t>(),blocked_stats=allocate<uint32_t>(8);
        c.call(SD_COM_IF_IUnknown,1,swap);
        overlap_test_block=true;overlap_test_entered=false;overlap_test_finish=false;
        auto native_present=std::async(std::launch::async,[&]{Client x(5);return x.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_Present,swap,{1,0});});
        auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
        while(!overlap_test_entered){require(std::chrono::steady_clock::now()<deadline,"native Present barrier was not reached");std::this_thread::yield();}
        overlap_test_immediate=context;overlap_test_nested=true;
        auto deferred_upload=std::async(std::launch::async,[&]{
            Client x(6);auto mapped=map(x,deferred_context,dynamic,0,D3D11_MAP_WRITE_DISCARD);
            for(unsigned i=0;i<1024;++i)arena[shadow-base+i]=uint8_t(i*7+19);
            unmap(x,deferred_context,dynamic,0,mapped.id);
            require(x.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_FinishCommandList,deferred_context,{FALSE,address(finished)})==S_OK);
        });
        auto immediate=std::async(std::launch::async,[&]{Client x(7);return x.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_GetType,context);});
        auto global_stats=std::async(std::launch::async,[&]{Client x(8);return x.call(0,SD_COM_STATS,0,{address(blocked_stats)});});
        auto second_present=std::async(std::launch::async,[&]{Client x(9);return x.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_Present,swap,{1,0});});
        auto token_release=std::async(std::launch::async,[&]{Client x(10);return x.call(SD_COM_IF_IUnknown,2,swap);});
        bool upload_ready=deferred_upload.wait_for(std::chrono::seconds(5))==std::future_status::ready;
        deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
        while(sd_overlap_test_waited()<4 && std::chrono::steady_clock::now()<deadline)std::this_thread::yield();
        bool blocked=sd_overlap_test_waited()>=4 && immediate.wait_for(std::chrono::seconds(0))==std::future_status::timeout && global_stats.wait_for(std::chrono::seconds(0))==std::future_status::timeout && second_present.wait_for(std::chrono::seconds(0))==std::future_status::timeout && token_release.wait_for(std::chrono::seconds(0))==std::future_status::timeout;
        overlap_test_finish=true;
        require(native_present.get()==S_OK);deferred_upload.get();
        require(immediate.get()==D3D11_DEVICE_CONTEXT_IMMEDIATE);require(global_stats.get()==S_OK);
        require(second_present.get()==S_OK);require(token_release.get()==1);
        require(upload_ready,"deferred Map/BindMap/Unmap/Finish blocked behind Present");require(blocked,"immediate/global call entered active Present");
        require(overlap_test_nested_checked==1,"native nested deferred callback case was not executed");
        require(*finished!=0);c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_ExecuteCommandList,context,{*finished,TRUE});c.release(*finished);c.release(deferred_context);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{readback,dynamic});
        m=map(c,context,readback,0,D3D11_MAP_READ);
        for(unsigned i=0;i<1024;++i)require(arena[shadow-base+i]==uint8_t(i*7+19),"overlapped deferred GPU readback mismatch");
        unmap(c,context,readback,0,m.id);
'''

def main():
    local=ROOT/'local/native-dxvk-present-overlap-v1';local.mkdir(parents=True,exist_ok=True)
    executable=local/'gate-test'
    command=['g++','-O1','-g','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',str(ROOT/'tests/native_dxvk_present_overlap.cpp'),'-o',str(executable)]
    subprocess.run(command,check=True)
    result=subprocess.run([str(executable)],check=True,capture_output=True,text=True,timeout=20)
    model=json.loads(result.stdout)
    base=ROOT/'local/native-dxvk-compact-v1/source/native_dxvk_com'
    source=local/'source/native_dxvk_com';shutil.copytree(base,source,dirs_exist_ok=True)
    prepare(source)
    # Test barrier instrumentation is isolated, absent from production transform.
    native=source/'com_native.cpp';native_text=native.read_text()
    production_native_hash=hashlib.sha256(native_text.encode()).hexdigest()
    native_text='extern "C" void sd_overlap_test_hook();\nextern "C" void sd_overlap_test_deferred_hook();\n'+native_text
    native_text+='\nextern "C" uint64_t sd_overlap_test_waited(){std::lock_guard<std::recursive_mutex> guard(state.mutex);return state.present_overlap.waited;}\n'
    native_text+='\nextern "C" uint64_t sd_overlap_test_released(){std::lock_guard<std::recursive_mutex> guard(state.mutex);return state.present_overlap.released;}\n'
    native.write_text(native_text)
    adapter=source/'com_native_adapters.inc'
    adapter.write_text(adapter.read_text().replace('return object->Present(p.args[0],p.args[1]);','sd_overlap_test_hook();return object->Present(p.args[0],p.args[1]);').replace('D3D11_MAPPED_SUBRESOURCE native={};p.ret=context->Map','sd_overlap_test_deferred_hook();D3D11_MAPPED_SUBRESOURCE native={};p.ret=context->Map'))
    fixture=local/'host_fixture.cpp';text=(ROOT/'tests/native_dxvk_com_host.cpp').read_text()
    text=text.replace('"../src/','"'+str(ROOT/'src')+'/')
    text=text.replace('int main(int argc,char** argv){',HOOK+'\nint main(int argc,char** argv){')
    marker='        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_ClearState,context);c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Flush,context);'
    assert text.count(marker)==1
    text=text.replace(marker,SCENARIO+marker).replace('stats[2]==60','stats[2]==63').replace('\\"present_calls\\":60','\\"present_calls\\":63')
    fixture.write_text(text)
    runner=(ROOT/'tools/test_native_dxvk_h4_host.py').read_text()
    runner=runner.replace("output=ROOT/'local/native-dxvk-h4-v9'","output=ROOT/'local/native-dxvk-present-overlap-v1'")
    runner=runner.replace("ROOT/'tests/native_dxvk_com_host.cpp'","ROOT/'local/native-dxvk-present-overlap-v1/host_fixture.cpp'")
    runner=runner.replace("ROOT/'src/native_dxvk_com/com_native.cpp'","ROOT/'local/native-dxvk-present-overlap-v1/source/native_dxvk_com/com_native.cpp'")
    ns={'__file__':__file__,'__name__':'present_overlap_fixture'}
    exec(compile(runner,__file__,'exec'),ns);ns['main']()
    report=json.loads((local/'host-test.json').read_text())
    report.update(gate_scenarios=model,real_deferred_upload_during_blocked_present=True,overlapped_gpu_readback_bytes=1024,
                  immediate_and_global_calls_waited=True,production_sources={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/native_dxvk_present_overlap.py',ROOT/'src/native_dxvk_com/present_overlap.h',Path(__file__),ROOT/'tests/native_dxvk_present_overlap.cpp']})
    report['same_swapchain_present_and_release_waited']=True
    report['native_foreign_deferred_worker_nested_dispatch_rejected']=True
    report['native_present_inside_explicit_enter_keeps_gate']=True
    report['candidate_sources']={str(p.relative_to(ROOT)):sha(p) for p in sorted(source.iterdir()) if p.is_file()}
    report['fixture_has_test_only_present_barrier']=True
    report['production_native_before_test_hook_sha256']=production_native_hash
    (local/'test.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'PASS','report':str(local/'test.json'),'present_calls':report['present_calls'],'real_deferred_upload_during_present':True}))

if __name__=='__main__':main()
