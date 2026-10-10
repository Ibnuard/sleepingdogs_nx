/* Standard Wine rsaenh registrations for the F1 prefix. LGPL-2.1-or-later.
 * Provider names/types follow dlls/rsaenh/rsaenh.rgs in the Wine source.
 * Run after loading existing hives; add missing defaults without replacing
 * user values or creating a new WoW64 view for unrelated Software keys.
 */
#ifndef F1_CRYPTO_REGISTRY_H
#define F1_CRYPTO_REGISTRY_H

static unsigned int f1_crypto_default(struct horizon_reg *reg, struct horizon_reg_key *key,
                                     const char *name, const char *text, unsigned int number)
{
    unsigned short wide_name[32], wide_value[128];
    unsigned int i, index, len = strlen(name);
    for (i = 0; i < len; i++) wide_name[i] = (unsigned char)name[i];
    if (horizon_reg_find_value(key, wide_name, len * 2, &index)) return HORIZON_REG_SUCCESS;
    if (!text)
        return horizon_reg_set_value(reg, key, wide_name, len * 2,
                                     HORIZON_REG_DWORD, &number, sizeof(number));
    for (i = 0; text[i]; i++) wide_value[i] = (unsigned char)text[i];
    wide_value[i++] = 0;
    return horizon_reg_set_value(reg, key, wide_name, len * 2,
                                 HORIZON_REG_SZ, wide_value, i * 2);
}

static unsigned int f1_crypto_install_view(struct horizon_reg *reg, struct horizon_reg_key *software)
{
    static const struct { const char *name; unsigned int type; } providers[] = {
        {"Microsoft Base Cryptographic Provider v1.0", 1},
        {"Microsoft Enhanced Cryptographic Provider v1.0", 1},
        {"Microsoft Enhanced RSA and AES Cryptographic Provider", 24},
        {"Microsoft Enhanced RSA and AES Cryptographic Provider (Prototype)", 24},
        {"Microsoft RSA SChannel Cryptographic Provider", 12},
        {"Microsoft Strong Cryptographic Provider", 1}
    };
    static const struct { const char *type, *name, *description; } types[] = {
        {"001", "Microsoft Enhanced Cryptographic Provider v1.0", "RSA Full (Signature and Key Exchange)"},
        {"012", "Microsoft RSA SChannel Cryptographic Provider", "RSA SChannel"},
        {"024", "Microsoft Enhanced RSA and AES Cryptographic Provider", "RSA Full and AES"}
    };
    char path[256];
    struct horizon_reg_key *key;
    unsigned int i, status;
    for (i = 0; i < sizeof(providers) / sizeof(providers[0]); i++)
    {
        snprintf(path, sizeof(path), "Microsoft\\Cryptography\\Defaults\\Provider\\%s", providers[i].name);
        if (!(key = horizon_reg_create_ascii(reg, software, path))) return HORIZON_REG_NO_MEMORY;
        status = f1_crypto_default(reg, key, "Image Path", "%SystemRoot%\\system32\\rsaenh.dll", 0);
        if (!status) status = f1_crypto_default(reg, key, "Type", NULL, providers[i].type);
        if (status) return status;
    }
    for (i = 0; i < sizeof(types) / sizeof(types[0]); i++)
    {
        snprintf(path, sizeof(path), "Microsoft\\Cryptography\\Defaults\\Provider Types\\Type %s", types[i].type);
        if (!(key = horizon_reg_create_ascii(reg, software, path))) return HORIZON_REG_NO_MEMORY;
        status = f1_crypto_default(reg, key, "Name", types[i].name, 0);
        if (!status) status = f1_crypto_default(reg, key, "TypeName", types[i].description, 0);
        if (status) return status;
    }
    return HORIZON_REG_SUCCESS;
}

static unsigned int f1_crypto_registry_install(struct horizon_reg *reg,
                                               struct horizon_reg_key *machine,
                                               unsigned int *views)
{
    static const unsigned short wow_path[] = {'W','o','w','6','4','3','2','N','o','d','e'};
    struct horizon_reg_key *software, *wow = NULL;
    unsigned int status;
    *views = 0;
    if (!(software = horizon_reg_create_ascii(reg, machine, "Software"))) return HORIZON_REG_NO_MEMORY;
    if ((status = f1_crypto_install_view(reg, software))) return status;
    *views = 1;
    status = horizon_reg_open(reg, software, wow_path, sizeof(wow_path), 0, &wow);
    if (status == HORIZON_REG_NAME_NOT_FOUND) return HORIZON_REG_SUCCESS;
    if (status) return status;
    status = f1_crypto_install_view(reg, wow);
    horizon_reg_release(reg, wow);
    if (!status) *views = 2;
    return status;
}
#endif
