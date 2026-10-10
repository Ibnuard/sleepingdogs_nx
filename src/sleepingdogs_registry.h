/* LGPL-2.1-or-later. Installed flag from the supplied installscript.vdf.
 * Preserve existing values; this registers no license, Steam identity or key. */
#ifndef SLEEPINGDOGS_REGISTRY_H
#define SLEEPINGDOGS_REGISTRY_H
static unsigned sleepingdogs_install_view(struct horizon_reg *reg,
                                          struct horizon_reg_key *software)
{
    struct horizon_reg_key *key = horizon_reg_create_ascii(reg, software, "Square Enix\\Sleeping Dogs");
    if (!key) return HORIZON_REG_NO_MEMORY;
    return f1_crypto_default(reg, key, "Installed", NULL, 1);
}

static unsigned sleepingdogs_registry_install(struct horizon_reg *reg,
                                              struct horizon_reg_key *machine)
{
    const unsigned short path[] = {'W','o','w','6','4','3','2','N','o','d','e'};
    struct horizon_reg_key *software = horizon_reg_create_ascii(reg, machine, "Software");
    struct horizon_reg_key *wow = NULL;
    if (!software) return HORIZON_REG_NO_MEMORY;
    unsigned status = sleepingdogs_install_view(reg, software);
    if (status) return status;
    /* Creating a global Wow6432Node would redirect unrelated Wine provider
     * lookups. Only seed that view when the user's hive already has it. */
    status = horizon_reg_open(reg, software, path, sizeof(path), 0, &wow);
    if (status == HORIZON_REG_NAME_NOT_FOUND) return HORIZON_REG_SUCCESS;
    if (status) return status;
    status = sleepingdogs_install_view(reg, wow);
    horizon_reg_release(reg, wow);
    if (status) return status;
    return HORIZON_REG_SUCCESS;
}
#endif
