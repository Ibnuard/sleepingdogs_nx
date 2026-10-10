/* F1 settings pages follow the grouped FEXTendo launcher layout. */
#ifndef F1_FEXTENDO_SETTINGS_H
#define F1_FEXTENDO_SETTINGS_H
enum fx_settings_page { FX_SETTINGS_ROOT, FX_SETTINGS_GRAPHICS,
    FX_SETTINGS_RENDERER, FX_SETTINGS_KEYBOARD, FX_SETTINGS_AUDIO,
    FX_SETTINGS_PAGES };

static int fx_input_mode;
static int fx_input_mode_load(const char *root) {
    char path[768], value[2];
    snprintf(path,sizeof(path),"%s/controller-keyboard.txt",root);
    if(fx_read(path,value,2)==2&&value[0]=='1')return 1;
    snprintf(path,sizeof(path),"%s/controller-gamepad.txt",root);
    if(fx_read(path,value,2)==2&&value[0]=='1')return 2;
    return 0;
}
static int fx_input_mode_save(const char *root,int mode) {
    char keyboard[768],gamepad[768],old_keyboard[2],old_gamepad[2];
    char off[2]={'0','\n'},on[2]={'1','\n'};
    if(mode<0||mode>2)return 0;
    snprintf(keyboard,sizeof(keyboard),"%s/controller-keyboard.txt",root);
    snprintf(gamepad,sizeof(gamepad),"%s/controller-gamepad.txt",root);
    int had_keyboard=fx_read(keyboard,old_keyboard,2)==2;
    int had_gamepad=fx_read(gamepad,old_gamepad,2)==2;
    /* First disable both, then enable the selected exclusive mode. */
    if(!fx_write(keyboard,off,2))return 0;
    if(!fx_write(gamepad,off,2))goto rollback;
    if(mode==1&&!fx_write(keyboard,on,2))goto rollback;
    if(mode==2&&!fx_write(gamepad,on,2))goto rollback;
    return 1;
rollback:
    if(had_keyboard)fx_write(keyboard,old_keyboard,2);else unlink(keyboard);
    if(had_gamepad)fx_write(gamepad,old_gamepad,2);else unlink(gamepad);
    return 0;
}
static int fx_settings_rows(int page) {
    static const int counts[FX_SETTINGS_PAGES]={5,4,2,3,2};
    return page>=0&&page<FX_SETTINGS_PAGES?counts[page]:5;
}
static float fx_settings_scroll_target(int row,int page) {
    int max=fx_settings_rows(page)-3,scroll=row-2;
    if(max<0)max=0;if(scroll<0)scroll=0;if(scroll>max)scroll=max;
    return scroll*116.f;
}
static void fx_settings_enter(struct fx_view *v,int page,int row) {
    v->settings_page=page;v->row=row;v->saved=0;
    v->settings_scroll=fx_settings_scroll_target(row,page);
}
static void fx_settings_back(struct fx_view *v) {
    if(v->settings_page==FX_SETTINGS_ROOT){v->screen=FX_HOME;return;}
    int row=v->settings_page==FX_SETTINGS_GRAPHICS?0:
        v->settings_page==FX_SETTINGS_RENDERER?1:
        v->settings_page==FX_SETTINGS_KEYBOARD?2:3;
    fx_settings_enter(v,FX_SETTINGS_ROOT,row);
}
static const char *fx_settings_title(int page) {
    static const char *const titles[]={"Settings","Graphics","Renderer","Keyboard","Audio"};
    return titles[page];
}
static const char *fx_settings_subtitle(int page) {
    static const char *const text[]={"Choose a group to configure.",
        "Choose a DXVK profile for the next race.","Choose the Direct3D renderer.",
        "Choose how the controller sends game input.","Launcher sounds and music."};
    return text[page];
}
static const char *fx_settings_label(const struct fx_view *v,int row) {
    static const char *const root[]={"Graphics","Renderer","Keyboard","Audio","Debug timestamp"};
    static const char *const keyboard[]={"Standard","Keyboard only","Gamepad only"};
    static const char *const audio[]={"Menu sounds","Background music"};
    switch(v->settings_page){
    case FX_SETTINGS_GRAPHICS:return fx_preset_names[row];
    case FX_SETTINGS_RENDERER:return fx_renderer_names[row];
    case FX_SETTINGS_KEYBOARD:return keyboard[row];
    case FX_SETTINGS_AUDIO:return audio[row];
    default:return root[row];
    }
}
static const char *fx_settings_detail(const struct fx_view *v,int row) {
    static const char *const keyboard[]={"Controller sends both supported input types.",
        "Controller buttons emulate keyboard keys.","Controller is exposed as a gamepad."};
    switch(v->settings_page){
    case FX_SETTINGS_ROOT:
        return row==0?fx_preset_names[v->selected]:row==1?fx_renderer_names[v->renderer]:
            row==2?fx_settings_label(&(struct fx_view){.settings_page=FX_SETTINGS_KEYBOARD},fx_input_mode):
            row==3?"Menu sounds and background music":"On-screen stopwatch while you play";
    case FX_SETTINGS_GRAPHICS:return fx_preset_details[row];
    case FX_SETTINGS_RENDERER:return row?"Async shader compilation  /  Alternative renderer":"Default renderer";
    case FX_SETTINGS_KEYBOARD:return keyboard[row];
    case FX_SETTINGS_AUDIO:return row?"Original ambient loop in the launcher":"Soft sounds for navigation and actions";
    default:return "";
    }
}
static int fx_settings_selected(const struct fx_view *v,int row) {
    return (v->settings_page==FX_SETTINGS_GRAPHICS&&v->selected==row)||
        (v->settings_page==FX_SETTINGS_RENDERER&&v->renderer==row)||
        (v->settings_page==FX_SETTINGS_KEYBOARD&&fx_input_mode==row);
}
static int fx_settings_toggle(const struct fx_view *v,int row) {
    if(v->settings_page==FX_SETTINGS_ROOT&&row==4)return v->timestamp;
    if(v->settings_page==FX_SETTINGS_AUDIO)return row?v->music:v->sound;
    return -1;
}
static int fx_settings_group(const struct fx_view *v,int row) {
    return v->settings_page==FX_SETTINGS_ROOT&&row<4;
}
static int fx_settings_choose(struct fx_view *v,const char *root) {
    int row=v->row,page=v->settings_page;
    if(row<0||row>=fx_settings_rows(page))return 0;
    if(page==FX_SETTINGS_ROOT&&row<4){
        static const int pages[]={FX_SETTINGS_GRAPHICS,FX_SETTINGS_RENDERER,FX_SETTINGS_KEYBOARD,FX_SETTINGS_AUDIO};
        fx_settings_enter(v,pages[row],row==0?v->selected:row==1?v->renderer:row==2?fx_input_mode:0);
        return 1;
    }
    if(page==FX_SETTINGS_GRAPHICS){if(!fx_apply_preset(root,row))return 0;v->selected=row;}
    else if(page==FX_SETTINGS_RENDERER){if(!fx_renderer_save(root,row))return 0;v->renderer=row;}
    else if(page==FX_SETTINGS_KEYBOARD){if(!fx_input_mode_save(root,row))return 0;fx_input_mode=row;}
    else if(page==FX_SETTINGS_AUDIO){
        if(row){if(!fx_background_music_save(root,!v->music))return 0;v->music=!v->music;}
        else{if(!fx_menu_sound_save(root,!v->sound))return 0;v->sound=!v->sound;}
    }else if(page==FX_SETTINGS_ROOT&&row==4){
        if(!fx_debug_timestamp_save(root,!v->timestamp))return 0;v->timestamp=!v->timestamp;
    }else return 0;
    v->saved=1;return 1;
}
#endif
