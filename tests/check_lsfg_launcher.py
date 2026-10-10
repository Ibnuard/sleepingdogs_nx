"""Run the real launcher settings, persistence and rendering with sanitizers."""
from pathlib import Path
import importlib.util,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('hud',ROOT/'tests/check_performance_hud.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
extra=r'''
    assert(fx_lsfg_load(root).enabled==0&&fx_lsfg_load(root).performance==1&&fx_lsfg_load(root).flow==1);
    assert(fx_settings_rows(FX_SETTINGS_ROOT)==7&&fx_settings_rows(FX_SETTINGS_LSFG)==2);
    fx_lsfg_available=0;fx_lsfg=(struct sd_lsfg_settings){0,1,1};
    fx_settings_enter(&v,FX_SETTINGS_LSFG,0);assert(fx_settings_choose(&v,root));
    assert(v.screen==FX_FAILED&&!fx_lsfg.enabled&&strstr(v.message,"shader pack"));
    v.screen=FX_SETTINGS;fx_lsfg_available=1;
    for(int e=0;e<2;e++)for(int p=0;p<2;p++)for(int f=0;f<3;f++){
        struct sd_lsfg_settings s={e,p,f};assert(fx_lsfg_save(root,s));
        s=fx_lsfg_load(root);assert(s.enabled==e&&s.performance==1&&s.flow==f);
    }
    fx_lsfg=(struct sd_lsfg_settings){0,1,1};
    for(int row=0;row<2;row++){
        fx_settings_enter(&v,FX_SETTINGS_LSFG,row);assert(fx_settings_choose(&v,root));
        struct sd_lsfg_settings s=fx_lsfg_load(root);
        assert(s.enabled==fx_lsfg.enabled&&s.performance==fx_lsfg.performance&&s.flow==fx_lsfg.flow);
    }
    snprintf(path,sizeof(path),"%s/launcher/lsfg.txt",root);
    snprintf(old,sizeof(old),"%s.old",path);assert(!rename(path,old));
    assert(fx_lsfg_load(root).enabled==1);
    assert(fx_lsfg_save(root,(struct sd_lsfg_settings){0,1,0}));assert(access(old,F_OK));
    assert(fx_write(path,"1 1 8\n",6));assert(fx_lsfg_load(root).enabled==0);
    snprintf(old,sizeof(old),"%s.new",path);assert(!mkdir(old,0700));
    assert(!fx_lsfg_save(root,(struct sd_lsfg_settings){1,1,1}));assert(!rmdir(old));
    fx_lsfg=(struct sd_lsfg_settings){1,1,1};assert(fx_lsfg_save(root,fx_lsfg));
'''
m.HARNESS=m.HARNESS.replace('row<6','row<7').replace('    struct fx_art art;',extra+'\n    struct fx_art art;')
m.HARNESS=m.HARNESS.replace('    fx_art_free(&art);free(pixels);',r'''
    fx_settings_enter(&v,FX_SETTINGS_ROOT,6);fx_render(&c,&v);save_image(&c,argv[2],"settings-lsfg");
    for(int row=0;row<2;row++){
        char name[32];snprintf(name,sizeof(name),"lsfg-row-%d",row);
        fx_settings_enter(&v,FX_SETTINGS_LSFG,row);fx_render(&c,&v);save_image(&c,argv[2],name);
    }
    fx_art_free(&art);free(pixels);
''')
writer=m.write_json
m.write_json=lambda path,data:writer(ROOT/'reports/lsfg-launcher-check.json',dict(data,
    lsfg_persistence_combinations=12,missing_pack_guard=True,lsfg_navigation=True))
sys.argv += ['--source','/home/blekjek/sleepingdogs-lsfg-v15/native-source','--output',
    str(ROOT/'local/lsfg-launcher-check')]
m.main()
