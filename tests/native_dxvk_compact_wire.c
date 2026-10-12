/* Exercise the actual shared decoder with poisoned omitted bytes. */
#include <assert.h>
#include <stdio.h>
#include "com_compact.h"
int main(void){
    unsigned methods=0,checks=0;
    for(unsigned m=0;m<200;m++){
        int n=sd_com_compact_count(SD_COM_IF_ID3D11DeviceContext,m);
        if(n<0)continue;++methods;
        for(unsigned seed=0;seed<256;seed++){
            struct sd_com_packet w,p,copy;
            memset(&w,seed,sizeof(w));w.abi=SD_COM_ABI;w.interface_id=SD_COM_IF_ID3D11DeviceContext;w.method=m;
            w.reserved=SD_COM_COMPACT_MAGIC|(unsigned)n;
            for(int i=0;i<n;i++)w.args[i]=seed*111+i;
            assert(sd_com_wire_decode(&p,&w));
            for(int i=0;i<16;i++){assert(p.args[i]==(i<n?w.args[i]:0));assert(!p.high[i]);}
            copy=w;p.ret=123;p.aux=456;p.fault=0x80004003;
            sd_com_wire_encode(&w,&p);copy.ret=p.ret;copy.aux=p.aux;copy.fault=p.fault;
            assert(!memcmp(&copy,&w,sizeof(w)));++checks;
            for(unsigned bad=0;bad<32;bad++)if(bad!=(unsigned)n){
                w.reserved=SD_COM_COMPACT_MAGIC|bad;assert(!sd_com_wire_decode(&p,&w));++checks;
            }
            w.reserved=0;assert(sd_com_wire_decode(&p,&w));assert(!memcmp(&p,&w,sizeof(p)));
            w.reserved=SD_COM_COMPACT_MAGIC|(unsigned)n;w.interface_id=0;assert(!sd_com_wire_decode(&p,&w));
            w.interface_id=SD_COM_IF_ID3D11DeviceContext;w.abi=5;assert(!sd_com_wire_decode(&p,&w));
        }
    }
    assert(methods==46);printf("PASS: %u methods, %u compact validation/round-trip cases\n",methods,checks);
}
