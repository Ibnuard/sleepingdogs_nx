#ifdef __SWITCH__
static const WCHAR f1_dialog_class[]={'#','3','2','7','7','0',0};
/* GDI startup dialogs are hidden while the launcher owns the framebuffer.
 * Capture text without sending guest messages or accepting the dialog. */
static void f1_dialog_utf8(char *out,size_t cap,const WCHAR *in)
{
    size_t n=0;
    if(!cap)return;
    while(*in){
        unsigned c=*in++,bytes;
        if(c>=0xd800&&c<=0xdbff){
            if(*in>=0xdc00&&*in<=0xdfff)c=0x10000+((c-0xd800)<<10)+(*in++-0xdc00);
            else c=0xfffd;
        }else if(c>=0xdc00&&c<=0xdfff)c=0xfffd;
        bytes=c<0x80?1:c<0x800?2:c<0x10000?3:4;
        if(bytes>=cap-n)break;
        if(bytes==1)out[n++]=(c<32)?' ':(char)c;
        else{
            out[n++]=(char)((bytes==2?0xc0:bytes==3?0xe0:0xf0)|(c>>(6*(bytes-1))));
            for(unsigned i=bytes-1;i;i--)out[n++]=(char)(0x80|((c>>(6*(i-1)))&63));
        }
    }
    out[n]=0;
}
static void f1_report_startup_dialog(HWND hwnd,const WCHAR *title)
{
    extern void wine_nx_runtime_startup_dialog(const char *,const char *);
    static const WCHAR static_class[]={'S','t','a','t','i','c',0};
    char heading[384],body[1536]={0};size_t used=0;
    HWND child=get_window_relative(hwnd,GW_CHILD);
    f1_dialog_utf8(heading,sizeof(heading),title);
    for(unsigned n=0;child&&n<32;n++,child=get_window_relative(child,GW_HWNDNEXT)){
        WCHAR text[384]={0},name[32]={0};
        UNICODE_STRING cls={0,sizeof(name)-sizeof(WCHAR),name};
        NtUserGetClassName(child,FALSE,&cls);
        /* Static labels carry MessageBox text. Skip buttons and edit fields. */
        if(wcsicmp(name,static_class))continue;
        NtUserInternalGetWindowText(child,text,ARRAY_SIZE(text));
        if(!text[0])continue;
        if(used&&used+1<sizeof(body))body[used++]=' ';
        f1_dialog_utf8(body+used,sizeof(body)-used,text);
        used+=strlen(body+used);
    }
    wine_nx_runtime_startup_dialog(heading,body);
}
#endif
