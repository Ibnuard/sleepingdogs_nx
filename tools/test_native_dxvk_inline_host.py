"""Actual DXVK/lavapipe plus current-packet permission reuse and fault tests."""
from pathlib import Path
import hashlib,json,subprocess,shutil,runpy
from native_dxvk_inline import ROOT,methods,pointers
LOCAL=ROOT/'local/native-dxvk-inline-v1'

def fixture_source(with_overlap=False):
    source=LOCAL/'source/native_dxvk_com'
    text=(ROOT/'tests/native_dxvk_com_host.cpp').read_text()
    text=text.replace('"../src/native_dxvk_com/','"'+str(source)+'/')
    text=text.replace('"../src/','"'+str(ROOT/'src')+'/')
    text='#include "'+str(source/'com_compact.h')+'"\n'+text
    pack=['void inline_payload(sd_com_packet* p) {',
          '    int n=sd_com_inline_count(p->interface_id,p->method);if(n<0)return;',
          '    struct Slice {unsigned arg;uint64_t words;};Slice slices[3]{};unsigned count=0;',
          '    switch(p->method) {']
    for m in methods():
        pack += [f'    case {m["index"]}:']
        for i,(expr,words) in pointers(m).items():
            expr=expr if expr.isdigit() else 'p->args['+str(next(j for j,x in enumerate(m['params']) if x['name']==expr))+']'
            pack.append(f'        if(uint64_t({expr})>SD_COM_MAX_ARRAY)return;')
            pack.append(f'        slices[count++]={{{i},p->args[{i}]?uint64_t({expr})*{words}:0}};')
        pack.append('        break;')
    pack += ['    default:return;}',
             '    uint64_t total=n;for(unsigned j=0;j<count;++j)total+=slices[j].words;if(total>32||total==unsigned(n))return;',
             '    unsigned at=n;for(unsigned j=0;j<count;++j){auto s=slices[j];',
             '        if(s.words){auto input=p->args[s.arg];std::memmove(p->words+at,(const void*)(uintptr_t)input,size_t(s.words)*4);p->args[s.arg]=address(p->words+at);at+=unsigned(s.words);}',
             '        else p->args[s.arg]=0;',
             '    }p->reserved=SD_COM_INLINE_MAGIC|unsigned(n);','}']
    text=text.replace('struct Client {','\n'.join(pack)+'\nstruct Client {')
    before='        require(wine_nx_sd_com_wow64_unix_funcs[0](packet)==0,"transport dispatch");'
    assert text.count(before)==1
    text=text.replace(before,'''        int compact=sd_com_compact_count(type,method);
        if(compact>=0)packet->reserved=SD_COM_COMPACT_MAGIC|unsigned(compact);
        if(valid)inline_payload(packet);
'''+before)
    marker='int main(int argc,char** argv){'
    extra=r'''
extern "C" void sd_com_test_inline_stats(uint64_t*);
static void inline_fault_cases(Client& c,uint32_t context) {
    auto p=c.packet;uint64_t before[4],after[4];
    auto reset=[&]{*p={};p->abi=SD_COM_ABI;p->object=context;p->interface_id=SD_COM_IF_ID3D11DeviceContext;p->method=10;p->reserved=SD_COM_INLINE_MAGIC|3;p->args[1]=1;};
    auto run=[&]{require(wine_nx_sd_com_wow64_unix_funcs[0](p)==0,"inline fault transport");};
    reset();p->args[2]=address(&p->words[31]);sd_com_test_inline_stats(before);unsigned prior=permissions;
    run();sd_com_test_inline_stats(after);require(!p->fault&&after[1]==before[1]+1&&permissions==prior+1,"inline read did not reuse packet probe");
    reset();p->args[2]=address(&p->ret);sd_com_test_inline_stats(before);prior=permissions;
    run();sd_com_test_inline_stats(after);require(!p->fault&&after[1]==before[1]&&after[3]==before[3]+1&&permissions==prior+2,"packet header must retain independent input probe");
    reset();p->args[2]=address(&p->words[31]);p->args[1]=2;sd_com_test_inline_stats(before);prior=permissions;
    run();sd_com_test_inline_stats(after);require(!p->fault&&after[1]==before[1]&&permissions==prior+2,"partial range overlap reused permission");
    reset();p->args[2]=base+arena_bytes-2;run();require(p->fault==uint32_t(E_POINTER),"out-of-arena input accepted");++rejections;
    reset();p->args[2]=0xfffffffcu;p->args[1]=2;prior=permissions;
    run();require(p->fault==uint32_t(E_POINTER)&&permissions==prior+1,"overflowing read reached probe");++rejections;
    reset();p->args[1]=SD_COM_MAX_ARRAY+1;p->args[2]=address(&p->words[3]);run();require(p->fault==uint32_t(E_INVALIDARG),"poisoned array count accepted");++rejections;
    reset();p->reserved=SD_COM_INLINE_MAGIC|4;require(wine_nx_sd_com_wow64_unix_funcs[0](p)<0,"forged inline argument count accepted");++rejections;
    reset();p->reserved=SD_COM_COMPACT_MAGIC|3;p->args[2]=address(&p->words[31]);sd_com_test_inline_stats(before);prior=permissions;
    run();sd_com_test_inline_stats(after);require(!p->fault&&after[1]==before[1]&&permissions==prior+2,"legacy packet reused inline range");
    reset();p->args[2]=address(&p->words[31]);deny_write=address(p)&~4095u;prior=permissions;
    require(wine_nx_sd_com_wow64_unix_funcs[0](p)<0&&permissions==prior+1,"packet probe omitted");++rejections;deny_write=0;
    require(!sd_com::current_inline_range().covers(address(&p->words[31]),4),"permission range escaped call");
}
'''
    text=text.replace(marker,extra+'\n'+marker)
    before='        const bool array_bench=argc==2&&!std::strcmp(argv[1],"--array-dispatch-bench");'
    text=text.replace(before,'        inline_fault_cases(c,context);\n'+before)
    text=text.replace('stats[6]==8','stats[6]==11')
    if with_overlap:
        overlap_fixture=runpy.run_path(str(ROOT/'tests/native_dxvk_present_overlap.py'))
        HOOK,SCENARIO=overlap_fixture['HOOK'],overlap_fixture['SCENARIO']
        text=text.replace(marker,HOOK+'\n'+marker)
        cleanup='        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_ClearState,context);c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Flush,context);'
        assert text.count(cleanup)==1
        scenario=SCENARIO.replace('auto finished=allocate<uint32_t>(),blocked_stats=allocate<uint32_t>(8);',
            'auto finished=allocate<uint32_t>(),blocked_stats=allocate<uint32_t>(8);auto overlap_samplers=allocate<uint32_t>(12);')
        scenario=scenario.replace('Client x(6);auto mapped=map(',
            'Client x(6);x.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSSetSamplers,deferred_context,{0,12,address(overlap_samplers)});auto mapped=map(')
        scenario=scenario.replace('Client x(7);return x.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_GetType,context);',
            'Client x(7);return x.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSSetSamplers,context,{0,12,address(overlap_samplers)});')
        text=text.replace(cleanup,scenario+cleanup).replace('stats[2]==60','stats[2]==63').replace('\\"present_calls\\":60','\\"present_calls\\":63')
    return text

def main():
    local=LOCAL;source=local/'source/native_dxvk_com';fixture=local/'host_fixture.cpp'
    with_overlap=(source/'present_overlap.h').exists()
    fixture.write_text(fixture_source(with_overlap))
    tested_source=source
    if with_overlap:
        # The production source stays byte-for-byte identical to its build
        # receipt. Add deterministic blocking hooks only to this test copy.
        tested_source=local/'host-source/native_dxvk_com';shutil.copytree(source,tested_source,dirs_exist_ok=True)
        native_path=tested_source/'com_native.cpp';native_text=native_path.read_text()
        native_text='extern "C" void sd_overlap_test_hook();\nextern "C" void sd_overlap_test_deferred_hook();\n'+native_text
        native_text+='\nextern "C" uint64_t sd_overlap_test_waited(){std::lock_guard<std::recursive_mutex> guard(state.mutex);return state.present_overlap.waited;}\n'
        native_text+='\nextern "C" uint64_t sd_overlap_test_released(){std::lock_guard<std::recursive_mutex> guard(state.mutex);return state.present_overlap.released;}\n'
        native_path.write_text(native_text)
        adapter=tested_source/'com_native_adapters.inc';text=adapter.read_text()
        before='return object->Present(p.args[0],p.args[1]);';assert text.count(before)==1
        text=text.replace(before,'sd_overlap_test_hook();'+before)
        before='D3D11_MAPPED_SUBRESOURCE native={};p.ret=context->Map';assert text.count(before)==1
        text=text.replace(before,'sd_overlap_test_deferred_hook();'+before);adapter.write_text(text)
    # The scope test uses the same production header, including thread-local
    # isolation while a second host thread has a simultaneously active span.
    scope=local/'inline-scope-test'
    cmd=['g++','-O2','-std=c++17','-Wall','-Wextra','-fsanitize=address,undefined','-fno-omit-frame-pointer',
         '-I'+str(source),str(ROOT/'tests/native_dxvk_inline_scope.cpp'),'-pthread','-o',str(scope)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    r=subprocess.run([str(scope)],check=True,capture_output=True,text=True);scope_report=json.loads(r.stdout)
    (local/'scope-test.json').write_text(json.dumps(scope_report,indent=2)+'\n')
    runner=(ROOT/'tools/test_native_dxvk_h4_host.py').read_text()
    runner=runner.replace("output=ROOT/'local/native-dxvk-h4-v9'","output=ROOT/'local/native-dxvk-inline-v1'")
    runner=runner.replace("ROOT/'tests/native_dxvk_com_host.cpp'","ROOT/'local/native-dxvk-inline-v1/host_fixture.cpp'")
    runner=runner.replace("ROOT/'src/native_dxvk_com", "ROOT/'local/native-dxvk-inline-v1/source/native_dxvk_com")
    if with_overlap:
        runner=runner.replace("ROOT/'local/native-dxvk-inline-v1/source/native_dxvk_com/com_native.cpp'",
                              "ROOT/'local/native-dxvk-inline-v1/host-source/native_dxvk_com/com_native.cpp'")
    ns={'__file__':str(ROOT/'tools/test_native_dxvk_inline_host.py'),'__name__':'inline_host_runner'}
    exec(compile(runner,str(ROOT/'tools/test_native_dxvk_h4_host.py'),'exec'),ns);ns['main']()
    report=json.loads((local/'host-test.json').read_text())
    report.update(inline_packets_exercised=True,inline_permission_cases=9,validated_range_scope=scope_report,
        candidate_sources={p.relative_to(local).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((local/'source').rglob('*')) if p.is_file()},
        fixture_generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if with_overlap:
        report.update(present_deferred_overlap=True,real_deferred_upload_during_blocked_present=True,
            overlapped_gpu_readback_bytes=1024,concurrent_inline_scopes_while_present_active=True,
            immediate_and_global_calls_waited=True,same_swapchain_present_and_release_waited=True,
            native_foreign_deferred_worker_nested_dispatch_rejected=True,native_present_inside_explicit_enter_keeps_gate=True,
            fixture_has_test_only_present_barrier=True,
            test_instrumented_sources={p.relative_to(local).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tested_source.iterdir()) if p.is_file()})
    (local/'host-test.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
