/* DXVK HUD selection is independent from renderer and graphics profile. */
#ifndef F1_DX_HUD_H
#define F1_DX_HUD_H
static int fx_dx_hud;
static const char *const fx_dx_hud_names[3] = {"None", "FPS", "Full"};
static const char *const fx_dx_hud_values[3] = {"", "fps", "full"};

static int fx_dx_hud_load(const char *root) {
    char path[768], value[8] = {0};
    snprintf(path, sizeof(path), "%s/launcher/dx-log.txt", root);
    size_t n = fx_read(path, value, sizeof(value));
    if (!n && access(path, F_OK)) {
        snprintf(path, sizeof(path), "%s/launcher/dx-log.txt.old", root);
        n = fx_read(path, value, sizeof(value));
    }
    if ((n == 2 && value[1] == '\n') ||
        (n == 3 && value[1] == '\r' && value[2] == '\n'))
        if (value[0] >= '0' && value[0] <= '2') return value[0] - '0';
    return 0;
}

static int fx_dx_hud_save(const char *root, int mode) {
    char path[768], stage[800], backup[800];
    if (mode < 0 || mode > 2) return 0;
    snprintf(path, sizeof(path), "%s/launcher/dx-log.txt", root);
    snprintf(stage, sizeof(stage), "%s.new", path);
    snprintf(backup, sizeof(backup), "%s.old", path);
    if (!fx_mkdir_parents(path)) return 0;
    /* Recover an interrupted rename before writing the next selection. */
    if (access(path, F_OK) && !access(backup, F_OK) && rename(backup, path)) return 0;
    const char value[2] = {(char)('0' + mode), '\n'};
    if (!fx_write(stage, value, sizeof(value))) { unlink(stage); return 0; }
    if (unlink(backup) && errno != ENOENT) { unlink(stage); return 0; }
    int existing = !access(path, F_OK);
    if (existing && rename(path, backup)) { unlink(stage); return 0; }
    if (rename(stage, path)) {
        if (existing) rename(backup, path);
        unlink(stage); return 0;
    }
    unlink(backup);
    return 1;
}

static int fx_dx_hud_config(const char *source, const char *stage, int mode) {
    char config[8192];
    if (mode < 0 || mode > 2) return 0;
    size_t n = fx_read(source, config, sizeof(config));
    if (!n || n == sizeof(config) || memchr(config, 0, n)) return 0;
    int count = snprintf(config + n, sizeof(config) - n,
        "\n# Show DX Log: %s (launcher choice)\ndxvk.hud = %s\n",
        fx_dx_hud_names[mode], fx_dx_hud_values[mode]);
    if (count < 0 || (size_t)count >= sizeof(config) - n) return 0;
    return fx_write(stage, config, n + (size_t)count);
}
#endif
