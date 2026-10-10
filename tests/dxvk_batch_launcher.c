int main(int argc,char **argv) {
    assert(argc==2);
    const char *root=argv[1];
    char path[1024], source[1024], config[8192];
    assert(fx_renderer_save(root,0));
    assert(fx_apply_renderer(root,0));
    const char *names[]={"d3d9.dll","d3d11.dll","dxgi.dll"};
    for(int i=0;i<3;i++) {
        snprintf(source,sizeof(source),"%s/launcher/renderers/dxvk-3.1.1/%s",root,names[i]);
        snprintf(path,sizeof(path),"%s/drive_c/SleepingDogs/%s",root,names[i]);
        assert(fx_files_equal(source,path));
    }
    for(int h=0;h<3;h++) {
        assert(fx_dx_hud_save(root,h));
        assert(fx_apply_preset(root,4));
        snprintf(path,sizeof(path),"%s/drive_c/SleepingDogs/dxvk.conf",root);
        size_t n=fx_read(path,config,sizeof(config)-1);config[n]=0;assert(n);
        assert(fx_renderer_option(config,"d3d11.sdSubmissionBatching","True"));
        assert(fx_renderer_option(config,"dxvk.hud",fx_dx_hud_values[h]));
        assert(fx_renderer_option(config,"dxgi.syncInterval","0"));
        assert(fx_renderer_option(config,"dxgi.maxFrameLatency","3"));
    }
    // Emulate the documented toggle, including CRLF produced by Windows editors.
    snprintf(source,sizeof(source),"%s/launcher/presets/performance/dxvk-3.1.1/dxvk.conf",root);
    size_t n=fx_read(source,config,sizeof(config)-1);config[n]=0;
    const char *flag="\r\nd3d11.sdSubmissionBatching = False\r\n";
    assert(n+strlen(flag)<sizeof(config));strcpy(config+n,flag);
    assert(fx_write(source,config,n+strlen(flag)));
    assert(fx_apply_preset(root,4));
    n=fx_read(path,config,sizeof(config)-1);config[n]=0;
    assert(fx_renderer_option(config,"d3d11.sdSubmissionBatching","False"));
    assert(fx_renderer_option(config,"dxvk.hud","full"));
    // Re-selecting the same renderer must replace a stale installed DLL.
    snprintf(path,sizeof(path),"%s/drive_c/SleepingDogs/d3d11.dll",root);
    assert(fx_write(path,"stale",5));assert(fx_apply_renderer(root,0));
    snprintf(source,sizeof(source),"%s/launcher/renderers/dxvk-3.1.1/d3d11.dll",root);
    assert(fx_files_equal(source,path));
    puts("PASS actual v11 C launcher: batch On/Off survives profile+HUD, DLL triplet refresh and Horizon rename semantics");
}
