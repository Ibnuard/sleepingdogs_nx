/* SPDX-License-Identifier: LGPL-2.1-or-later. UI worker never runs checks. */
static struct fx_art sd_checked_art;
static int sd_check_ready;
static int sd_check_cancelled(void){return __atomic_load_n(&fx_ui_command,__ATOMIC_ACQUIRE)<0||__atomic_load_n(&fx_ui_stop,__ATOMIC_ACQUIRE);}
static void sd_check_progress(int stage,int percent){
    pthread_mutex_lock(&fx_ui_lock);fx_ui_view.check.stage=stage;fx_ui_view.check.percent=percent;pthread_mutex_unlock(&fx_ui_lock);
}
static void sd_check_done(int stage){
    pthread_mutex_lock(&fx_ui_lock);fx_ui_view.check.done[stage]=1;pthread_mutex_unlock(&fx_ui_lock);
}
static void sd_check_request(void){ /* UI lock held; main thread executes. */
    sd_check_ready=0;fx_ui_view.check=(struct sd_check_view){.visible=1,.percent=-1};
    __atomic_store_n(&fx_ui_command,2,__ATOMIC_RELEASE);
}
static void sd_check_run(void){
    struct sd_check_job job={.root=RUNTIME_DIR,.cancelled=sd_check_cancelled,.progress=sd_check_progress};
    int ok=appletGetAppletType()==AppletType_Application;
    sd_boot_memory_compatible();
    if(!ok||sd_boot.rc[2]||sd_boot.rc[3]||sd_boot.title!=UINT64_C(0x059a3db219b42000)||sd_boot.total<=UINT64_C(0x80000000)){
        snprintf(job.error,sizeof(job.error),"Use the updated Sleeping Dogs FEXTendo Memory HOME tile. Album and other game forwarders are unsupported.");ok=0;
    }
    if(ok){
        sd_check_done(SD_CHECK_BOOT);sd_check_progress(SD_CHECK_PATCH,-1);
        if(sd_boot_profile_valid(&sd_boot))sd_low_window_init();
        ok=sd_boot_profile_valid(&sd_boot)&&sd_low_window_ready();
        if(!ok)snprintf(job.error,sizeof(job.error),"FEXTendo low-memory patch is required. Install it, reboot into its Hekate entry, then open the Sleeping Dogs HOME tile.");
    }
    if(ok&&!sd_check_cancelled()){
        sd_check_done(SD_CHECK_PATCH);sd_check_progress(SD_CHECK_GAME,-1);ok=sd_check_game(&job);
    }
    if(ok&&!sd_check_cancelled()){
        sd_check_done(SD_CHECK_GAME);sd_check_progress(SD_CHECK_RUNTIME,0);ok=sd_check_runtime(&job);
    }
    if(ok&&!sd_check_cancelled()){
        sd_check_done(SD_CHECK_RUNTIME);sd_check_progress(SD_CHECK_ART,-1);
        ok=fx_art_load(&sd_checked_art,RUNTIME_DIR);
        if(!ok)snprintf(job.error,sizeof(job.error),"Cannot load launcher artwork. Recopy the complete runtime update and retry.");
    }
    pthread_mutex_lock(&fx_ui_lock);
    if(sd_check_cancelled()){ok=0;snprintf(job.error,sizeof(job.error),"Check cancelled.");fx_art_free(&sd_checked_art);}
    else if(ok){sd_check_ready=1;fx_ui_view.check.complete=1;}
    else{fx_ui_view.check.failed=1;snprintf(fx_ui_view.check.error,sizeof(fx_ui_view.check.error),"%s",job.error);}
    if(!sd_check_cancelled())__atomic_store_n(&fx_ui_command,0,__ATOMIC_RELEASE);
    pthread_mutex_unlock(&fx_ui_lock);
    /* Small standalone report also exists when the Play log was never opened. */
    char path[768];snprintf(path,sizeof(path),"%s/system-check.log",RUNTIME_DIR);
    FILE *f=fopen(path,"w");if(f){fprintf(f,"launcher-v1\nresult=%s\nbase=%llx size=%llx title=%016llx quota=%llu\nqueries=%08x/%08x/%08x/%08x\nlow_window=%d\n%s\n",
        ok?"PASS":"FAIL",(unsigned long long)sd_boot.base,(unsigned long long)sd_boot.size,(unsigned long long)sd_boot.title,
        (unsigned long long)sd_boot.total,sd_boot.rc[0],sd_boot.rc[1],sd_boot.rc[2],sd_boot.rc[3],sd_low_window_ready(),job.error);fclose(f);}
}
