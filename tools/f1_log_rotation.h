/* SPDX-License-Identifier: MIT. Preserve the failed launch until the next Play. */
#ifndef F1_LOG_ROTATION_H
#define F1_LOG_ROTATION_H
static FILE *f1_open_runtime_log(const char *root)
{
    char current[768], previous[768];
    snprintf(current, sizeof(current), "%s/fex-runtime.log", root);
    snprintf(previous, sizeof(previous), "%s/fex-runtime-previous.log", root);
    if (!access(current, F_OK)) {
        if ((!access(previous, F_OK) && unlink(previous)) || rename(current, previous))
            return fopen(current, "ab"); /* Retain old evidence if rotation fails. */
    }
    return fopen(current, "wb");
}
#endif
