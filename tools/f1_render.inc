static void fx_render(struct fx_canvas *c,const struct fx_view *v) {
    int y,i;char status[96];
    int scene_index=v->splash_ms?3:v->screen==FX_LOADING?2:
        v->screen==FX_CREDITS?4+(v->credit_page!=0):v->screen==FX_SETTINGS;
    const uint32_t *scene=c->art->scene[scene_index];
    for(y=0;y<FX_H;y++)memcpy(c->pixels+y*c->stride,scene+y*FX_W,FX_W*4);
    if(v->splash_ms){fx_splash(c,v->splash_ms);return;}
    if(v->screen==FX_LOADING){
        if(v->debug){
            fx_rect(c,0,0,FX_W,FX_H,FX_COLOR(0,0,0),255);
            fx_text(c,34,20,"FEXTendo / F1 2013 - LIVE WINE DEBUG",1,FX_WHITE);
            fx_text(c,36,60,"v" FX_APP_VERSION " - DX11 runtime. Startup monitor every 5s.",0,FX_MUTED);
            if(v->fatal)fx_text(c,36,96,v->message?v->message:"Startup failed. See fex-runtime.log.",0,FX_COLOR(255,145,139));
            char lines[21][120];unsigned total;
            pthread_mutex_lock(&fx_debug_lock);
            total=fx_debug_total;
            for(i=0;i<21;i++)memcpy(lines[i],fx_debug_lines[i],120);
            pthread_mutex_unlock(&fx_debug_lock);
            unsigned count=v->fatal?18:20,first=total>count?total-count:0;
            for(unsigned n=first;n<total;n++){
                char visible[111];snprintf(visible,sizeof(visible),"%.108s",lines[n%21]);
                fx_text(c,36,(v->fatal?148:100)+(int)(n-first)*26,visible,0,
                    !strncmp(visible,"[FAIL]",6)?FX_COLOR(255,145,139):FX_COLOR(210,226,238));
            }
            snprintf(status,sizeof(status),"Startup %us  |  HOME: close  |  Save the full log after 60s",v->debug_seconds);
            if(v->fatal)snprintf(status,sizeof(status),"Startup failed  |  HOME: close  |  Save fex-runtime.log and DXVK logs");
            fx_text(c,36,659,status,3,FX_MUTED);
        }else{
            fx_spinner(c,640,462,v->frame);
            fx_center(c,640,507,v->message?v->message:"Preparing your game...",0,FX_MUTED);
        }
        return;
    }
    fx_battery(c,v);
    if(v->screen==FX_CREDITS)return;
    if(v->screen!=FX_SETTINGS){
        fx_play(c,76,552,v->tile<2,v->frame);
        char played[48];fx_last_played_label(played,v->last_played,v->wall_time);
        fx_text(c,76,623,"Last played",0,FX_MUTED);
        fx_text(c,76+fx_text_width(c->art,"Last played",0)+15,623,played,0,FX_WHITE);
        c->clip_left=600;c->clip_right=FX_W;
        float slide=fx_clamp(v->tile_mix-1,0,2);
        for(i=0;i<4;i++){
            float amount=fx_clamp(1-fabsf(v->tile_mix-i),0,1);
            int w=(int)lroundf(FX_TILE_MIN+(FX_TILE_MAX-FX_TILE_MIN)*amount);
            int x=750+260*i-(int)lroundf(260*slide)-w/2,yy=384-w/2;
            int selected=v->tile==i;
            fx_tile_image(c,x,yy,w,i,!selected);
            if(selected)fx_glass(c,x,yy,w,w,22,v->frame,1);
            if(selected)fx_glow(c,x,yy,w,w,22,v->frame,1.f);
            const char *title=i==0?"F1 2013":i==1?"Launch Debug":i==2?"Settings":"Credits";
            const char *subtitle=i==0?"Launch GUI":i==1?"Wine trace":i==2?"Preferences":"About";
            fx_text(c,x+9,yy+w+16,title,1,selected?FX_WHITE:FX_MUTED);
            fx_circle(c,x+14,yy+w+65,4,selected?FX_BLUE:FX_COLOR(90,112,140));
            fx_text(c,x+28,yy+w+53,subtitle,0,selected?FX_BLUE:FX_MUTED);
        }
        c->clip_left=c->clip_right=0;
        for(int x=600;x<FX_W;x++){
            float left=fx_clamp((732-x)/132.f,0,1)*fx_clamp(slide,0,1);
            float right=fx_clamp((x-1160)/120.f,0,1)*fx_clamp(2-slide,0,1);
            unsigned alpha=(unsigned)(255*fmaxf(left,right));
            if(alpha)for(y=230;y<604;y++){
                uint32_t *p=c->pixels+y*c->stride+x;*p=fx_blend(*p,scene[y*FX_W+x],alpha);
            }
        }
        snprintf(status,sizeof(status),"%s  /  %s",fx_preset_names[v->selected],fx_renderer_names[v->renderer]);
        fx_text(c,643,623,status,0,FX_MUTED);
    }else{
        int rows=fx_settings_rows(v->settings_page);
        fx_text(c,417,122,fx_settings_title(v->settings_page),2,FX_WHITE);
        fx_text(c,417,172,fx_settings_subtitle(v->settings_page),0,FX_MUTED);
        char position[16];snprintf(position,sizeof(position),"%d / %d",v->row+1,rows);
        fx_text(c,1116,135,position,0,FX_MUTED);
        c->clip_top=204;c->clip_bottom=560;
        for(i=0;i<rows;i++){
            int on=v->row==i;y=216+i*116-(int)lroundf(v->settings_scroll);
            if(y+118<c->clip_top||y-18>=c->clip_bottom)continue;
            if(on)fx_glass(c,412,y,766,100,14,v->frame,0);
            else fx_round(c,412,y,766,100,14,FX_COLOR(12,25,39),255);
            if(on)fx_focus(c,412,y,766,100,14,v->frame);
            fx_text(c,435,y+20,fx_settings_label(v,i),1,FX_WHITE);
            fx_text(c,437,y+61,fx_settings_detail(v,i),0,FX_MUTED);
            int toggle=fx_settings_toggle(v,i);
            if(fx_settings_selected(v,i)){
                fx_round(c,1060,y+35,95,29,14,FX_COLOR(18,98,132),255);
                fx_center(c,1107,y+38,"SELECTED",3,FX_WHITE);
            }else if(toggle>=0){
                fx_round(c,1080,y+34,72,32,16,toggle?FX_COLOR(21,144,208):FX_COLOR(50,61,76),255);
                fx_circle(c,toggle?1136:1096,y+50,12,FX_WHITE);
            }else if(fx_settings_group(v,i))fx_text(c,1135,y+34,">",1,FX_MUTED);
        }
        for(int fade=0;fade<16;fade++){
            unsigned alpha=(unsigned)(255*(1-fade/16.f)*(1-fade/16.f));
            fx_rect(c,394,204+fade,791,1,FX_COLOR(9,23,41),alpha);
            fx_rect(c,394,559-fade,791,1,FX_COLOR(9,23,41),alpha);
        }
        c->clip_top=c->clip_bottom=0;
        if(rows>3){
            fx_round(c,1194,216,3,332,1,FX_COLOR(32,51,70),255);
            int thumb=(int)(332.f*332.f/(rows*116.f-16.f));
            int thumb_y=216+(int)((332-thumb)*v->settings_scroll/((rows-3)*116.f));
            fx_round(c,1194,thumb_y,3,thumb,1,FX_COLOR(45,142,202),255);
        }
        fx_text(c,418,589,v->saved?"Settings saved. Ready to race.":"Game video settings are managed in F1 2013.",0,v->saved?FX_BLUE:FX_MUTED);
    }
    fx_hint(c,56,689,"A",v->screen==FX_SETTINGS?
        (fx_settings_group(v,v->row)?"Open":fx_settings_toggle(v,v->row)>=0?"Toggle":"Apply"):"Select");
    if(v->screen==FX_FAILED){
        fx_rect(c,0,0,FX_W,FX_H,FX_COLOR(1,7,17),202);
        for(i=12;i>=4;i-=4)fx_round(c,332-i,214+i,616+i*2,294,26+i,FX_COLOR(0,0,0),30);
        fx_round(c,331,207,618,298,25,FX_COLOR(66,93,126),190);
        fx_round(c,333,209,614,294,23,FX_COLOR(14,29,49),255);
        fx_round(c,369,244,50,50,14,FX_COLOR(66,37,49),255);
        fx_center(c,394,248,"!",1,FX_COLOR(255,142,138));
        fx_text(c,438,239,v->returned?(v->returned==1?"Game closed":"Game stopped"):"Launch failed",2,FX_WHITE);
        fx_wrapped(c,373,315,v->message?v->message:"Game startup failed.",532);
        fx_round(c,371,418,536,52,14,FX_COLOR(28,71,118),255);
        fx_hint(c,498,444,"A",v->fatal?"Close launcher":"Back to launcher");
    }
}
