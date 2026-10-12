/* Included after the actual launcher UI and screenshot bounds helpers. */
int main(int argc,char **argv){
    assert(argc==3);const char *root=argv[1];
    struct sd_boot_memory memory={.base=0x200000,.size=UINT64_C(0x7fffe00000),.title=UINT64_C(0x059a3db219b42000),.total=UINT64_C(0xda000000)};
    assert(sd_boot_profile_valid(&memory));
    for(unsigned i=0;i<4;i++){memory.rc[i]=1;assert(!sd_boot_profile_valid(&memory));memory.rc[i]=0;}
    memory.size=0xffe00000;assert(!sd_boot_profile_valid(&memory));memory.size=UINT64_C(0x7fffe00000);
    memory.base=0x80000000;assert(!sd_boot_profile_valid(&memory));memory.base=0x200000;
    memory.total=0x80000000;assert(!sd_boot_profile_valid(&memory));memory.total=UINT64_C(0xda000000);
    memory.title++;assert(!sd_boot_profile_valid(&memory));memory.title--;
    assert(!fx_debug_launch(root));
    struct fx_view v={.screen=FX_SETTINGS,.selected=2,.renderer=2,.music=1,.sound=1,.battery=100,.frame=32};
    assert(FX_SETTINGS_PAGES==10&&fx_settings_rows(FX_SETTINGS_ROOT)==10);
    assert(!v.debug_launch);fx_settings_enter(&v,FX_SETTINGS_ROOT,8);
    assert(fx_settings_choose(&v,root)&&v.debug_launch&&fx_debug_launch(root));
    v.tile=3;assert(fx_settings_choose(&v,root)&&!v.debug_launch&&!v.tile&&!fx_debug_launch(root));
    fx_settings_enter(&v,FX_SETTINGS_ROOT,9);assert(fx_settings_choose(&v,root)&&checks_requested==1);
    fx_settings_enter(&v,FX_SETTINGS_ROOT,7);assert(fx_settings_choose(&v,root)&&v.settings_page==FX_SETTINGS_OSK);
    for(int s=0;s<FX_KEYBOARD_SHORTCUTS;s++){
        fx_settings_enter(&v,FX_SETTINGS_SHORTCUT,s);assert(fx_settings_choose(&v,root));
        assert(fx_keyboard_options.shortcut==s&&fx_settings_selected(&v,s));
        assert(fx_keyboard_options_load(root).shortcut==s);
        fx_settings_back(&v);assert(v.settings_page==FX_SETTINGS_OSK&&v.row==0);
    }
    for(int h=0;h<FX_KEYBOARD_HOLD_CHOICES;h++){
        fx_settings_enter(&v,FX_SETTINGS_HOLD,h);assert(fx_settings_choose(&v,root));
        assert(fx_keyboard_options.hold_ms==(int)fx_keyboard_hold_ms[h]);
        fx_settings_back(&v);assert(v.settings_page==FX_SETTINGS_OSK&&v.row==2);
    }
    for(int row=0;row<fx_settings_rows(FX_SETTINGS_ROOT);row++){
        struct fx_view root_view={.settings_page=FX_SETTINGS_ROOT};
        assert(strcmp(fx_settings_label(&root_view,row),"Game detail"));
    }
    fx_lsfg_available=1;fx_settings_enter(&v,FX_SETTINGS_LSFG,0);
    assert(fx_settings_choose(&v,root)&&fx_lsfg.enabled&&fx_lsfg_load(root).enabled);
    v.row=1;assert(fx_settings_choose(&v,root)&&fx_lsfg.flow==2&&fx_lsfg_load(root).flow==2);
    struct fx_art art;assert(fx_art_load(&art,root));
    uint32_t *pixels=calloc((size_t)1296*720,4);assert(pixels);
    struct fx_canvas c={.pixels=pixels,.stride=1296,.art=&art,.clip_bottom=720};
    v.screen=FX_HOME;v.tile=0;v.tile_mix=0;fx_render(&c,&v);save_image(&c,argv[2],"home");
    v.debug_launch=1;v.tile=3;v.tile_mix=3;fx_render(&c,&v);save_image(&c,argv[2],"debug-enabled");
    v.screen=FX_SETTINGS;fx_settings_enter(&v,FX_SETTINGS_ROOT,8);fx_render(&c,&v);save_image(&c,argv[2],"settings");
    fx_settings_enter(&v,FX_SETTINGS_SHORTCUT,5);fx_render(&c,&v);save_image(&c,argv[2],"keyboard");
    fx_settings_enter(&v,FX_SETTINGS_LSFG,0);fx_render(&c,&v);save_image(&c,argv[2],"lsfg");
    v.check=(struct sd_check_view){.visible=1,.stage=1,.percent=-1,.done={1,0,0,0}};
    fx_render(&c,&v);save_image(&c,argv[2],"patch-check");
    v.check.failed=1;snprintf(v.check.error,sizeof(v.check.error),"FEXTendo low-memory patch is required. Install it, reboot into its Hekate entry, then open the Sleeping Dogs HOME tile.");
    fx_render(&c,&v);save_image(&c,argv[2],"patch-required");
    text_inside(&art,"Active / mapping passed",0,714,281,247,103,1033,640);
    free(pixels);fx_art_free(&art);
    puts("PASS: memory profile rejects unpatched/wrong-title/query failures; debug defaults hidden and persists; keyboard routes/options; six real UI previews with guarded stride");
    return 0;
}
