/* LGPL-2.1-or-later. Matches Wine dsound_classes.idl and xaudio2.idl (v7).
 * Installed after loading hives. Add missing COM defaults; retain user values. */
#ifndef F1_AUDIO_REGISTRY_H
#define F1_AUDIO_REGISTRY_H
#include "f1_crypto_registry.h"

static unsigned f1_audio_install_classes(struct horizon_reg *reg, struct horizon_reg_key *classes)
{
    static const struct { const char *clsid, *dll; } entries[] = {
        {"{47D4D946-62E8-11CF-93BC-444553540000}", "dsound.dll"},
        {"{3901CC3F-84B5-4FA4-BA35-AA8172B8A09B}", "dsound.dll"},
        {"{5A508685-A254-4FBA-9B82-9A24B00306AF}", "xaudio2_7.dll"}
    };
    for (unsigned i = 0; i < sizeof(entries)/sizeof(entries[0]); ++i) {
        char path[96];
        snprintf(path, sizeof(path), "CLSID\\%s\\InprocServer32", entries[i].clsid);
        struct horizon_reg_key *key = horizon_reg_create_ascii(reg, classes, path);
        if (!key) return HORIZON_REG_NO_MEMORY;
        unsigned status = f1_crypto_default(reg, key, "", entries[i].dll, 0);
        if (!status) status = f1_crypto_default(reg, key, "ThreadingModel", "Both", 0);
        if (status) return status;
    }
    return HORIZON_REG_SUCCESS;
}

static unsigned f1_audio_registry_install(struct horizon_reg *reg, struct horizon_reg_key *machine)
{
    struct horizon_reg_key *classes = horizon_reg_create_ascii(reg, machine, "Software\\Classes");
    if (!classes) return HORIZON_REG_NO_MEMORY;
    unsigned status = f1_audio_install_classes(reg, classes);
    /* No new global WoW64 redirection. Cover either pre-existing CLSID view. */
    const char *views[] = {"Software\\Wow6432Node\\Classes", "Software\\Classes\\Wow6432Node"};
    for (unsigned i = 0; !status && i < 2; ++i) {
        unsigned short path[64];
        unsigned n = strlen(views[i]);
        for (unsigned j = 0; j < n; ++j) path[j] = views[i][j];
        struct horizon_reg_key *view = NULL;
        status = horizon_reg_open(reg, machine, path, n * 2, 0, &view);
        if (status == HORIZON_REG_NAME_NOT_FOUND) { status = 0; continue; }
        if (!status) { status = f1_audio_install_classes(reg, view); horizon_reg_release(reg, view); }
    }
    return status;
}
#endif
