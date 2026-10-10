/* SPDX-License-Identifier: LGPL-2.1-or-later */
static int sd_sync_parse_mode(const char *s, size_t size)
{
    if (!size || size > 3 || s[0] < '0' || s[0] > '2') return 0;
    if (size == 2 && s[1] != '\n') return 0;
    if (size == 3 && (s[1] != '\r' || s[2] != '\n')) return 0;
    return s[0] - '0';
}
static int sd_sync_load_mode(const char *path)
{
    char data[4];
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    size_t size = fread(data, 1, sizeof(data), file);
    int failed = ferror(file);
    fclose(file);
    return failed ? 0 : sd_sync_parse_mode(data, size);
}
