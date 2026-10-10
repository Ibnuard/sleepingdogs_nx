"""Check the production shader transformations without claiming a GPU benchmark."""
from pathlib import Path
import json
import re
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_mesa_shader_v14 import WORK, PREVIOUS, BASE, RUSTC, prepare, FILES
from port_common import sha,write_json


def block(text, needle):
    start=text.index(needle);opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]


RUST_TYPES=r'''
#![allow(dead_code,unused_variables,private_interfaces)]
use std::fmt;
#[derive(Clone,Copy,PartialEq)] enum MemSpace { Global(u8), Local, Shared }
struct MemAccess { space:MemSpace }
struct Load { access:MemAccess }
struct ShaderModelInfo { model:u8, scoreboard:bool }
impl ShaderModelInfo {
 fn sm(&self)->u8 { self.model }
 fn op_needs_scoreboard(&self,_op:&Op)->bool { self.scoreboard }
}
impl fmt::Display for Op { fn fmt(&self,f:&mut fmt::Formatter<'_>)->fmt::Result {write!(f,"op")} }
#[derive(PartialEq,Clone,Copy)] enum FRndMode { NearestEven, NegInf, PosInf, Zero }
enum RegFile { GPR }
enum SrcType { F32 }
#[derive(Clone,Copy)] enum SrcRef { Zero, Reg(u32), Imm32(u32), CBuf(u32) }
impl fmt::Display for SrcRef { fn fmt(&self,f:&mut fmt::Formatter<'_>)->fmt::Result {write!(f,"src")} }
#[derive(Clone,Copy)] struct Src {src_ref:SrcRef}
impl Src {
 fn is_unmodified(&self)->bool {true}
 AS_IMM
}
struct LegalizeBuilder { copied:Option<u32> }
impl LegalizeBuilder {
 fn copy_alu_src_if_not_reg(&mut self,s:&mut Src,_r:RegFile,_t:SrcType) {assert!(matches!(s.src_ref,SrcRef::Reg(_)));}
 fn copy_alu_src(&mut self,s:&mut Src,_r:RegFile,_t:SrcType) {
   if let SrcRef::Imm32(v)=s.src_ref {self.copied=Some(v);} else {panic!("expected immediate");}
   s.src_ref=SrcRef::Reg(7);
 }
}
fn swap_srcs_if_not_reg(a:&mut Src,b:&mut Src,_r:RegFile) {
 if !matches!(a.src_ref,SrcRef::Reg(_)) {std::mem::swap(a,b);}
}
struct OpFAdd {srcs:[Src;2],dst:u32,rnd_mode:FRndMode,saturate:bool,ftz:bool}
struct SM50Encoder<'a> {opcode:u32,bits:u64,p:std::marker::PhantomData<&'a ()>}
impl SM50Encoder<'_> {
 fn set_opcode(&mut self,x:u32) {self.opcode=x;}
 fn set_dst(&mut self,_x:&u32){}
 fn set_reg_fmod_src(&mut self,_r:std::ops::Range<usize>,_a:u8,_b:u8,_s:&Src){}
 fn set_src_imm32(&mut self,_r:std::ops::Range<usize>,_v:u32){}
 fn set_src_imm_f20(&mut self,_r:std::ops::Range<usize>,_b:u8,_v:u32){}
 fn set_cb_fmod_src(&mut self,_r:std::ops::Range<usize>,_a:u8,_b:u8,_s:&Src){}
 fn set_rnd_mode(&mut self,_r:std::ops::Range<usize>,_x:FRndMode){}
 fn set_bit(&mut self,b:usize,v:bool) {if v {self.bits|=1<<b;} else {self.bits&=!(1<<b);}}
}
trait SM50Op {
 fn legalize(&mut self,b:&mut LegalizeBuilder);
 fn encode(&self,e:&mut SM50Encoder<'_>);
}
'''

RUST_MAIN=r'''
fn main() {
 let mut cases=0;
 for sm in [30,50,52,53,60,70,75,80,90] {
  for scoreboard in [false,true] {
   let s=ShaderModelInfo{model:sm,scoreboard};
   for op in [Op::Tex(()),Op::Tld(()),Op::Tld4(()),Op::Tmml(()),Op::Txd(()),Op::Txq(())] {
    assert_eq!(candidate_latency(&s,&op),if !scoreboard {0} else if sm==53 {200} else {32});cases+=1;
   }
   for space in [MemSpace::Global(32),MemSpace::Global(64),MemSpace::Shared,MemSpace::Local] {
    let op=Op::Ld(Load{access:MemAccess{space}});
    assert_eq!(candidate_latency(&s,&op),if !scoreboard {0} else if sm==53 && matches!(space,MemSpace::Global(_)) {200} else {32});cases+=1;
   }
   for op in [Op::St(()),Op::Ipa(()),Op::ALd(()),Op::MemBar(()),Op::Atom(()),Op::SuLd(()),Op::Ldc(()),Op::MuFu(())] {
    assert_eq!(candidate_latency(&s,&op),baseline_latency(&s,&op));cases+=1;
   }
  }
 }
 for imm in [0u32,0x3f000000,0xbecccccd,0x3eaaaaab,0x3f800001,0xc0000001,0x7f800000,0x80000000] {
  for sat in [false,true] {
   for round in [FRndMode::NearestEven,FRndMode::NegInf,FRndMode::PosInf,FRndMode::Zero] {
    let mut op=OpFAdd{srcs:[Src{src_ref:SrcRef::Reg(1)},Src{src_ref:SrcRef::Imm32(imm)}],dst:0,rnd_mode:round,saturate:sat,ftz:false};
    let mut b=LegalizeBuilder{copied:None};op.legalize(&mut b);
    let mut e=SM50Encoder{opcode:0,bits:0,p:std::marker::PhantomData};op.encode(&mut e);
    if sat {assert!(e.opcode!=0x0800 && e.bits&(1<<50)!=0);}
    if imm&0xfff!=0 && (sat || round!=FRndMode::NearestEven) {assert_eq!(b.copied,Some(imm));assert_eq!(e.opcode,0x5c58);}
    if imm&0xfff!=0 && !sat && round==FRndMode::NearestEven {assert!(b.copied.is_none());assert_eq!(e.opcode,0x0800);}
    cases+=1;
   }
  }
 }
 // Regression: saturate(x - 0.4) must not become unclamped FADD32I.
 // Production legalization and encoding above determine the operation form.
 let imm=(-0.4f32).to_bits();
 let mut op=OpFAdd{srcs:[Src{src_ref:SrcRef::Reg(1)},Src{src_ref:SrcRef::Imm32(imm)}],dst:0,rnd_mode:FRndMode::NearestEven,saturate:true,ftz:false};
 let mut b=LegalizeBuilder{copied:None};op.legalize(&mut b);
 let mut e=SM50Encoder{opcode:0,bits:0,p:std::marker::PhantomData};op.encode(&mut e);
 for i in -10000..10000 {
  let x=i as f32/1000.0;let raw=x+f32::from_bits(imm);
  let emitted=if e.opcode!=0x0800 && e.bits&(1<<50)!=0 {raw.clamp(0.0,1.0)} else {raw};
  assert_eq!(emitted,raw.clamp(0.0,1.0));cases+=1;
 }
 println!("PASS {} scheduler and FADD legalization/encoding cases",cases);
}
'''

NIR_TEST=r'''
#include <assert.h>
#include <stdio.h>
#include "compiler/glsl_types.h"
#include "nir_builder.h"
#include "nir_control_flow.h"
static unsigned branch_count(nir_shader *s) {
 unsigned n=0;
 nir_foreach_function_impl(impl,s) {
  nir_foreach_block(b,impl) {if (nir_block_get_following_if(b)) n++;}
 }
 return n;
}
static void check(unsigned sm,unsigned ops,bool side_effect,bool flatten) {
 const nir_shader_compiler_options opts={0};
 nir_builder b=nir_builder_init_simple_shader(MESA_SHADER_FRAGMENT,&opts,"v14-select");
 nir_def *x=nir_load_input(&b,1,32,nir_imm_int(&b,0),.base=0,.component=0);
 nir_def *cond=nir_flt(&b,x,nir_imm_float(&b,0.5));
 nir_push_if(&b,cond);
 nir_def *yes=x;
 for(unsigned i=0;i<ops;i++) yes=nir_fadd(&b,yes,nir_imm_float(&b,0.1));
 if(side_effect) nir_store_output(&b,yes,nir_imm_int(&b,0),.base=1,.write_mask=1);
 nir_push_else(&b,NULL);
 nir_def *no=nir_fmul(&b,x,nir_imm_float(&b,2.0));
 nir_pop_if(&b,NULL);
 nir_def *v=nir_if_phi(&b,yes,no);
 nir_store_output(&b,v,nir_imm_int(&b,0),.base=0,.write_mask=1);
 assert(branch_count(b.shader)==1);
 const struct {unsigned sm;} nc={sm}; const __typeof__(nc) *nak=&nc;
 nir_opt_peephole_select_options options={.limit=PRODUCTION_LIMIT,.discard_ok=true};
 nir_opt_peephole_select(b.shader,&options);
 assert(branch_count(b.shader)==(flatten?0:1));
 ralloc_free(b.shader);
}
int main(void) {
 glsl_type_singleton_init_or_ref();
 check(53,1,false,true);check(53,7,false,true);check(53,8,false,false);
 check(53,1,true,false);check(53,20,false,false);
 check(50,1,false,false);check(70,1,false,false);
 glsl_type_singleton_decref();
 puts("PASS 7 actual NIR branch transforms: small ALU flattening, limits, side effects, architecture scope");
 return 0;
}
'''


def main():
    prepared=prepare();out=WORK/'tests';out.mkdir(exist_ok=True)
    src=WORK/'source';base=PREVIOUS/'source'
    latency=block((src/FILES[0]).read_text(),'pub fn estimate_variable_latency')
    old=block((base/FILES[0]).read_text(),'pub fn estimate_variable_latency')
    variants=sorted(set(re.findall(r'Op::(\w+)',latency)))
    enum='enum Op {'+','.join(n+('(Load)' if n=='Ld' else '(())') for n in variants)+'}'
    as_imm=block((base/'src/nouveau/compiler/nak/ir.rs').read_text(),'pub fn as_imm_not_f20')
    fadd=block((src/FILES[1]).read_text(),'impl SM50Op for OpFAdd')
    rust=RUST_TYPES.replace('AS_IMM',as_imm)+'\n'+enum+'\n'+latency.replace('estimate_variable_latency','candidate_latency')+'\n'+old.replace('estimate_variable_latency','baseline_latency')+'\n'+fadd+'\n'+RUST_MAIN
    (out/'shader.rs').write_text(rust)
    subprocess.run([str(RUSTC),'--edition=2021',str(out/'shader.rs'),'-o',str(out/'shader')],check=True)
    rust_result=subprocess.check_output([str(out/'shader')],text=True).strip()
    print(rust_result,flush=True)
    limit=re.search(r'peephole_select_options = \{.*?\.limit = ([^,]+)',(src/FILES[2]).read_text(),re.S)[1]
    (out/'nir.c').write_text(NIR_TEST.replace('PRODUCTION_LIMIT',limit))
    native=BASE/'mesa-vulkan/native'
    entries=json.loads((native/'compile_commands.json').read_text())
    recipe=next(e for e in entries if e['file'].endswith('/nir_opt_peephole_select.c'))
    args=shlex.split(recipe['command']);filtered=[];i=0
    while i<len(args):
        if args[i] in ('-o','-MF','-MQ','-c'):i+=2;continue
        if args[i] in ('-MD','-DNDEBUG'):i+=1;continue
        filtered.append(args[i]);i+=1
    filtered += ['-UNDEBUG','-fsanitize=address,undefined',str(out/'nir.c'),'-o',str(out/'nir'),'-Wl,--start-group']
    libs=['src/compiler/nir/libnir.a','src/compiler/libcompiler.a','src/util/libmesa_util.a',
          'src/util/libmesa_util_simd.a','src/util/libmesa_util_clflush.a','src/util/libmesa_util_clflushopt.a',
          'src/util/blake3/libblake3.a','src/c11/impl/libmesa_util_c11.a']
    filtered += [str(native/n) for n in libs]+['-Wl,--end-group','-lzstd','-lz','-lm','-lpthread','-ldl','-lstdc++']
    with (out/'nir-build.log').open('w') as log:
        subprocess.run(filtered,cwd=native,stdout=log,stderr=subprocess.STDOUT,check=True)
    nir_result=subprocess.check_output([str(out/'nir')],text=True).strip();print(nir_result,flush=True)
    unchanged=['src/nouveau/compiler/nak/calc_instr_deps.rs','src/nouveau/compiler/nak/opt_instr_sched_prepass.rs',
               'src/nouveau/compiler/nak/opt_instr_sched_postpass.rs','src/nouveau/compiler/nak.h','src/nouveau/compiler/nak_private.h']
    old_manifest=json.loads((PREVIOUS/'prepared.json').read_text())['source_files']
    for n in unchanged:
        assert sha(base/n)==old_manifest[n]
        if (src/n).exists():assert sha(src/n)==old_manifest[n]
    write_json(ROOT/'reports/mesa-v14-shader-host.json',dict(status='PASS',changed_sources=prepared['changed'],
        rust_result=rust_result,nir_result=nir_result,hardware_tested=False,
        limitation='Rust extraction exercises production decision/encoding methods with operand adapters; not the full shader compiler or a GPU execution test. NIR tests execute the real pass.',
        unchanged_dependency_barriers_and_reg_pressure={n:old_manifest[n] for n in unchanged},
        native_nir_libraries={n:sha(native/n) for n in libs},
        generated_tests={p.name:sha(p) for p in (out/'shader.rs',out/'nir.c')},
        sources={'tests/check_mesa_shader_v14.py':sha(Path(__file__))}))


if __name__=='__main__':main()
