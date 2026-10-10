/* Test the real in-memory Wine/Horizon registry used in the native NRO. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "horizon_registry.h"
#include "f1_crypto_registry.h"
#include "sleepingdogs_registry.h"

static long long now(void) { return 123; }
static void signal_event(void *event) { (void)event; }

int main(void)
{
    struct horizon_reg reg = {0};
    /* Match the initialization contract of the registry's own host tests. */
    assert(horizon_reg_init(&reg, now, signal_event));
    struct horizon_reg_key *machine = horizon_reg_create_ascii(&reg, reg.root, "Machine");
    assert(machine);
    assert(!sleepingdogs_registry_install(&reg, machine));
    assert(!sleepingdogs_registry_install(&reg, machine));
    struct horizon_reg_key *key = horizon_reg_create_ascii(&reg, machine, "Software\\Square Enix\\Sleeping Dogs");
    const unsigned short name[] = {'I','n','s','t','a','l','l','e','d'};
    unsigned index;
    struct horizon_reg_value *value = horizon_reg_find_value(key, name, sizeof(name), &index);
    assert(value && value->type == HORIZON_REG_DWORD && value->len == 4);
    assert(*(unsigned *)value->data == 1);
    unsigned custom = 7;
    assert(!horizon_reg_set_value(&reg, key, name, sizeof(name), HORIZON_REG_DWORD, &custom, 4));
    assert(!sleepingdogs_registry_install(&reg, machine));
    value = horizon_reg_find_value(key, name, sizeof(name), &index);
    assert(*(unsigned *)value->data == 7);
    struct horizon_reg_key *software = horizon_reg_create_ascii(&reg, machine, "Software");
    const unsigned short wowname[] = {'W','o','w','6','4','3','2','N','o','d','e'};
    struct horizon_reg_key *wow = NULL;
    assert(horizon_reg_open(&reg, software, wowname, sizeof(wowname), 0, &wow) == HORIZON_REG_NAME_NOT_FOUND);
    wow = horizon_reg_create_ascii(&reg, software, "Wow6432Node");
    assert(wow && !sleepingdogs_registry_install(&reg, machine));
    key = horizon_reg_create_ascii(&reg, wow, "Square Enix\\Sleeping Dogs");
    value = horizon_reg_find_value(key, name, sizeof(name), &index);
    assert(value && *(unsigned *)value->data == 1);
    puts("PASS: game registry defaults are idempotent and preserve existing values");
    horizon_reg_release(&reg, reg.root);
    return 0;
}
