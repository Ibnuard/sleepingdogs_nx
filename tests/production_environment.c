#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "environment.h"
static int count(const char *env,size_t bytes,const char *entry) {
    int n=0;for(size_t i=0;i<bytes&&env[i];i+=strlen(env+i)+1)n+=!strcmp(env+i,entry);return n;
}
int main(void) {
    const char input[]="PATH=C:\\windows\0DXVK_LOG_LEVEL=info\0DXVK_LOG_LEVEL=debug\0"
        "DXVK_LOG_PATH=C:\\old\0FEXTENDO_TRACE=1\0WINEDEBUG=+all\0FEX_MAXINST=500\0";
    char out[1024];unsigned checks=0;
    for(int debug=0;debug<2;++debug) {
        size_t n=sd_production_environment(out,sizeof(out),input,sizeof(input),debug);assert(n);
        assert(count(out,n,"DXVK_LOG_LEVEL=info")==debug);
        assert(count(out,n,"DXVK_LOG_LEVEL=none")==!debug);
        assert(count(out,n,"DXVK_LOG_LEVEL=debug")==0);
        assert(count(out,n,"FEXTENDO_TRACE=0")==1&&count(out,n,"WINEDEBUG=-all")==1);
        assert(count(out,n,"PATH=C:\\windows")==1&&count(out,n,"FEX_MAXINST=500")==1);
        assert(out[n-1]==0&&out[n-2]==0);checks+=9;
        for(size_t capacity=0;capacity<n;++capacity) {
            memset(out,0x55,sizeof(out));
            assert(!sd_production_environment(out,capacity,input,sizeof(input),debug));
            for(size_t i=capacity;i<sizeof(out);++i)assert((unsigned char)out[i]==0x55);
            ++checks;
        }
    }
    assert(!sd_production_environment(out,sizeof(out),"NO-NUL",6,0));
    assert(!sd_production_environment(NULL,sizeof(out),input,sizeof(input),0));
    assert(!sd_production_environment(out,sizeof(out),NULL,0,0));
    printf("PASS %u environment/boundary cases\n",checks+3);
}
