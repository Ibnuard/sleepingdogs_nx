/* LGPL-2.1-or-later. Install matching x86 D3D9/D3D11/DXGI before loading Wine. */
#ifndef FEXTENDO_RENDERERS_H
#define FEXTENDO_RENDERERS_H
static const char *const fx_renderer_ids[2]={"dxvk-3.1.1","dxvk-2.7.1-async"};
static const char *const fx_renderer_names[2]={"DXVK 3.1.1","DXVK 2.7.1 async"};
/* Keep the first five entries identical to the old journal's bit layout. */
static const char *const fx_renderer_targets[7]={
    "/drive_c/F1_2013/d3d9.dll","/drive_c/dxvk/d3d9.dll",
    "/drive_c/F1_2013/dxvk.conf","/launcher/presets/dxvk.conf","/launcher/renderer.txt",
    "/drive_c/F1_2013/d3d11.dll","/drive_c/F1_2013/dxgi.dll"};
static const char *const fx_renderer_sources[4]={"d3d9.dll","dxvk.conf","d3d11.dll","dxgi.dll"};
static const int fx_renderer_source_index[7]={0,0,1,1,-1,2,3};
static char fx_renderer_error_text[192],fx_renderer_error_detail[1024];
static int fx_renderer_reject(const char *reason,const char *path) {
    int error=errno;const char *name=strrchr(path,'/');
    snprintf(fx_renderer_error_text,sizeof(fx_renderer_error_text),"%s: %s",reason,name?name+1:path);
    snprintf(fx_renderer_error_detail,sizeof(fx_renderer_error_detail),"%s path=%s errno=%d",reason,path,error);
    return 0;
}
static int fx_renderer_selected(const char *root) {
    char p[768],b[2];snprintf(p,sizeof(p),"%s/launcher/renderer-choice.txt",root);
    return fx_read(p,b,2)==2&&b[0]=='1'&&b[1]=='\n';
}
static int fx_renderer_save(const char *root,int selected) {
    char p[768],b[2]={(char)('0'+selected),'\n'};
    if(selected<0||selected>1)return 0;
    snprintf(p,sizeof(p),"%s/launcher/renderer-choice.txt",root);
    return fx_write(p,b,2);
}
static int fx_renderer_recover_journal(const char *root,const char *name,int count) {
    char journal[768],p[768],old[800],tmp[800];unsigned char mask,bytes[2];
    snprintf(journal,sizeof(journal),"%s/launcher/%s",root,name);
    if(access(journal,F_OK))return errno==ENOENT;
    if(fx_read(journal,bytes,2)!=1)return 0;
    mask=bytes[0];if(mask&~((1u<<count)-1))return 0;
    for(int i=0;i<count;i++){
        snprintf(p,sizeof(p),"%s%s",root,fx_renderer_targets[i]);
        snprintf(old,sizeof(old),"%s.fxr-old",p);snprintf(tmp,sizeof(tmp),"%s.fxr-new",p);
        if(!access(old,F_OK)){
            if(unlink(p)&&errno!=ENOENT)return 0;
            if(rename(old,p))return 0;
        }else if(!(mask&(1u<<i))&&unlink(p)&&errno!=ENOENT)return 0;
        else if((mask&(1u<<i))&&access(p,F_OK))return 0;
        unlink(tmp);
    }
    return !unlink(journal);
}
static int fx_renderer_recover(const char *root) {
    /* Old versions used five bits. A separate journal avoids deleting the new
     * D3D11 pair while recovering a transaction interrupted before this update. */
    return fx_renderer_recover_journal(root,"renderer.txn",5)&&
           fx_renderer_recover_journal(root,"renderer-dx11.txn",7);
}
static int fx_files_equal(const char *a,const char *b) {
    unsigned char x[16384],y[16384];size_t nx,ny;int same=0;
    FILE *fa=fopen(a,"rb"),*fb=fopen(b,"rb");
    if(fa&&fb)do{
        nx=fread(x,1,sizeof(x),fa);ny=fread(y,1,sizeof(y),fb);
        if(nx!=ny||memcmp(x,y,nx)||ferror(fa)||ferror(fb))break;
        if(nx<sizeof(x)){same=1;break;}
    }while(1);
    if(fa)fclose(fa);if(fb)fclose(fb);return same;
}
static int fx_copy_file(const char *source,const char *target) {
    unsigned char buffer[16384];size_t n;int ok=0;
    FILE *in=fopen(source,"rb"),*out=NULL;if(!in)return 0;
    out=fopen(target,"wb");if(!out){fclose(in);return 0;}
    while((n=fread(buffer,1,sizeof(buffer),in)))if(fwrite(buffer,1,n,out)!=n)goto done;
    ok=!ferror(in)&&!fflush(out)&&!fsync(fileno(out));
done:
    fclose(in);if(fclose(out))ok=0;return ok;
}
static int fx_renderer_space(char c) {return c==' '||c=='\t'||c=='\r';}
static int fx_renderer_option(const char *config,const char *key,const char *value) {
    size_t key_len=strlen(key),value_len=strlen(value);int matches=0;
    /* Text editors and Windows packaging can produce CRLF and a UTF-8 BOM.
     * Compare effective option values, not a particular newline encoding. */
    if(!strncmp(config,"\xef\xbb\xbf",3))config+=3;
    while(*config){
        const char *line=config,*end=strchr(config,'\n'),*eq,*comment,*key_end,*val;
        if(!end)end=config+strlen(config);
        config=*end?end+1:end;
        comment=memchr(line,'#',(size_t)(end-line));if(comment)end=comment;
        while(line<end&&fx_renderer_space(*line))line++;
        while(end>line&&fx_renderer_space(end[-1]))end--;
        eq=memchr(line,'=',(size_t)(end-line));if(!eq)continue;
        key_end=eq;while(key_end>line&&fx_renderer_space(key_end[-1]))key_end--;
        if((size_t)(key_end-line)!=key_len||memcmp(line,key,key_len))continue;
        val=eq+1;while(val<end&&fx_renderer_space(*val))val++;
        /* The final assignment wins, as in DXVK's config parser. */
        matches=(size_t)(end-val)==value_len&&!memcmp(val,value,value_len);
    }
    return matches;
}
static int fx_renderer_valid(const char *dll,const char *conf,int selected) {
    unsigned char head[64],pe[26];char config[4096];struct stat st;
    if(stat(dll,&st))return fx_renderer_reject("Cannot read renderer DLL",dll);
    if(st.st_size<1024*1024||st.st_size>32*1024*1024){errno=0;return fx_renderer_reject("Invalid renderer DLL size",dll);}
    FILE *f=fopen(dll,"rb");if(!f)return fx_renderer_reject("Cannot open renderer DLL",dll);
    int ok=fread(head,1,64,f)==64&&head[0]=='M'&&head[1]=='Z';
    if(ok){uint32_t offset=fx_u32(head+60);
        ok=offset<=(uint64_t)st.st_size-26&&!fseek(f,(long)offset,SEEK_SET)&&
            fread(pe,1,26,f)==26&&!memcmp(pe,"PE\0\0\x4c\x01",6)&&pe[24]==0x0b&&pe[25]==1;}
    fclose(f);if(!ok){errno=0;return fx_renderer_reject("Invalid x86 renderer DLL",dll);}
    size_t n=fx_read(conf,config,sizeof(config)-1);config[n]=0;
    if(!n)return fx_renderer_reject("Cannot read renderer config",conf);
    if(memchr(config,0,n)||!fx_renderer_option(config,"d3d9.presentInterval","1")||
       (selected==1&&!fx_renderer_option(config,"dxvk.enableAsync","True"))){
        errno=0;return fx_renderer_reject("Invalid renderer config",conf);
    }
    return 1;
}
static int fx_apply_renderer(const char *root,int selected) {
    char source[4][768],p[7][768],tmp[7][800],old[7][800],journal[768],journal_tmp[800];
    unsigned char mask=0;char choice[2]={(char)('0'+selected),'\n'};int same=1;
    snprintf(fx_renderer_error_text,sizeof(fx_renderer_error_text),"Cannot install renderer. Check SD space and fex-runtime.log.");
    snprintf(fx_renderer_error_detail,sizeof(fx_renderer_error_detail),"Renderer transaction failed before guest startup");
    if(selected<0||selected>1)return fx_renderer_reject("Invalid renderer selection","");
    if(!fx_renderer_recover(root)||!fx_recover(root))return fx_renderer_reject("Cannot recover renderer transaction","renderer journal");
    for(int i=0;i<4;i++)
        snprintf(source[i],sizeof(source[i]),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[selected],fx_renderer_sources[i]);
    for(int i=0;i<4;i++)if(i!=1&&!fx_renderer_valid(source[i],source[1],selected))return 0;
    for(int i=0;i<7;i++){
        int src=fx_renderer_source_index[i];
        snprintf(p[i],sizeof(p[i]),"%s%s",root,fx_renderer_targets[i]);
        snprintf(tmp[i],sizeof(tmp[i]),"%.*s.fxr-new",767,p[i]);snprintf(old[i],sizeof(old[i]),"%.*s.fxr-old",767,p[i]);
        if(!fx_mkdir_parents(p[i]))return 0;
        if(!access(p[i],F_OK))mask|=1u<<i;
        if(src>=0){if(!fx_files_equal(source[src],p[i]))same=0;}
        else {char b[2];if(fx_read(p[i],b,2)!=2||memcmp(b,choice,2))same=0;}
    }
    if(same)return 1; /* Read-only verification, no repeated multi-MB writes. */
    for(int i=0;i<7;i++){
        int src=fx_renderer_source_index[i];
        if(src>=0){if(!fx_copy_file(source[src],tmp[i])||!fx_files_equal(source[src],tmp[i]))goto failed;}
        else if(!fx_write(tmp[i],choice,2))goto failed;
    }
    for(int i=0;i<7;i++)if(unlink(old[i])&&errno!=ENOENT)goto failed;
    snprintf(journal,sizeof(journal),"%s/launcher/renderer-dx11.txn",root);
    snprintf(journal_tmp,sizeof(journal_tmp),"%s.tmp",journal);
    if(!fx_write(journal_tmp,&mask,1)||rename(journal_tmp,journal)){unlink(journal_tmp);goto failed;}
    for(int i=0;i<7;i++){
        if((mask&(1u<<i))&&rename(p[i],old[i]))goto rollback;
        if(rename(tmp[i],p[i]))goto rollback;
    }
    if(unlink(journal))goto rollback;
    for(int i=0;i<7;i++)unlink(old[i]);
    return 1;
rollback:
    fx_renderer_recover(root);return 0;
failed:
    for(int i=0;i<7;i++)unlink(tmp[i]);
    return 0;
}
#endif
