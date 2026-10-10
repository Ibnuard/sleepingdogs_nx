/* SPDX-License-Identifier: MIT. Apply the circuit memory profile once at the
 * requested 1280x720 fullscreen. Lower only settings that size scene/GPU
 * resources; CPU, physics, input, audio and saves are preserved. Older backups
 * remain, and choices the user makes after the migration persist. */
#ifndef F1_GAME_CONFIG_H
#define F1_GAME_CONFIG_H
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#define F1_CONFIG_CAP 65536
#define F1_MEMORY_MARKER "launcher/circuit-memory-v5.txt"
#define F1_MEMORY_BACKUP ".pre-0.1.27.bak"

struct f1_xml_setting { const char *tag, *name, *value; };

static const struct f1_xml_setting f1_resolution_settings[] = {
    {"resolution", "width", "1280"}, {"resolution", "height", "720"},
    {"resolution", "oldWidth", "1280"}, {"resolution", "oldHeight", "720"},
    {"resolution", "aspect", "16:9"}, {"resolution", "fullscreen", "true"}
};

/* Values are the game's own ultralow/off options from
 * system/hardware_settings_options.xml. Texture LOD 3 skips one more mip level
 * than the earlier LOD 2 migration; the restrictions file allows any lod >= 0. */
static const struct f1_xml_setting f1_memory_settings[] = {
    {"resolution", "multisampling", "off"},
    {"textures", "lod", "3"},
    {"shadows", "enabled", "false"}, {"shadows", "size", "512"},
    {"headlights", "headlightQuality", "0"},
    {"particles", "enabled", "false"}, {"particles", "wind", "false"},
    {"crowd", "enabled", "false"},
    {"cloth", "enabled", "false"},
    {"groundcover", "mode", "off"}, {"groundcover", "clutter", "false"},
    {"objects", "lod", "1.0"}, {"objects", "maxlod", "0"},
    {"trees", "lod", "0.5"}, {"trees", "maxlod", "1"},
    {"vehicles", "characterQuality", "0"}, {"vehicles", "lodQuality", "0"},
    {"envmap", "faces", "0"}, {"envmap", "size", "256"},
    {"water", "update", "false"}, {"water", "detail", "0"},
    {"mirrors", "enabled", "false"}, {"mirrors", "width", "256"}, {"mirrors", "height", "64"},
    {"skidmarks", "enabled", "false"},
    {"dynamic_ambient_occ", "enabled", "false"},
    {"track_reflections", "enabled", "false"}
};

static int f1_xml_replace(char *xml, size_t cap, char *begin, char *end, const char *text)
{
    size_t length = strlen(xml), old = end - begin, add = strlen(text);
    if (add > cap - 1 || length - old > cap - 1 - add) return 0;
    memmove(begin + add, end, length - (end - xml) + 1);
    memcpy(begin, text, add);
    return 1;
}

/* Bounded XML attribute scanner. Comments, quoted '>' and attribute spacing
 * cannot be mistaken for a tag. Only the first matching tag is considered.
 * 1 = value found in [*begin,*end); 2 = tag found without the attribute
 * (*begin = insertion point); 0 = no such tag; -1 = malformed input. */
static int f1_xml_locate(char *xml, const char *tag, const char *name, char **begin, char **end)
{
    char *p = xml;
    while ((p = strchr(p, '<'))) {
        if (!strncmp(p, "<!--", 4)) {
            if (!(p = strstr(p + 4, "-->"))) return -1;
            p += 3; continue;
        }
        if (p[1] == '!') return -1;
        char *start = ++p;
        while (*p && !isspace((unsigned char)*p) && *p != '/' && *p != '>') ++p;
        int match = (size_t)(p - start) == strlen(tag) && !memcmp(start, tag, p - start);
        while (*p && *p != '>') {
            if (isspace((unsigned char)*p) || *p == '/' || *p == '?') { ++p; continue; }
            char *attr = p;
            while (*p && !isspace((unsigned char)*p) && *p != '=' && *p != '>') ++p;
            size_t len = p - attr;
            while (isspace((unsigned char)*p)) ++p;
            if (*p != '=') { if (!match) break; return -1; }
            ++p;
            while (isspace((unsigned char)*p)) ++p;
            char quote = *p++;
            if (quote != '\'' && quote != '"') return -1;
            char *v = p;
            if (!(p = strchr(p, quote))) return -1;
            if (match && len == strlen(name) && !memcmp(attr, name, len)) {
                *begin = v; *end = p; return 1;
            }
            ++p;
        }
        if (!*p) return -1;
        if (match) {
            if (p > xml && p[-1] == '/') --p;
            *begin = *end = p; return 2;
        }
        /* Closing tags and the XML declaration can skip their remaining name. */
        if (!(p = strchr(p, '>'))) return -1;
        ++p;
    }
    return 0;
}

/* 1 = set/inserted, 0 = tag absent, -1 = malformed or no room. */
static int f1_xml_attribute(char *xml, size_t cap, const char *tag, const char *name, const char *value)
{
    char *begin, *end;
    int rc = f1_xml_locate(xml, tag, name, &begin, &end);
    if (rc <= 0) return rc;
    if (rc == 1) return f1_xml_replace(xml, cap, begin, end, value) ? 1 : -1;
    char text[128];
    int n = snprintf(text, sizeof(text), " %s=\"%s\"", name, value);
    if (n < 0 || n >= (int)sizeof(text)) return -1;
    return f1_xml_replace(xml, cap, begin, begin, text) ? 1 : -1;
}

static int f1_xml_get(char *xml, const char *tag, const char *name, char *out, size_t cap)
{
    char *begin, *end;
    out[0] = 0;
    int rc = f1_xml_locate(xml, tag, name, &begin, &end);
    if (rc != 1) return rc;
    size_t n = end - begin;
    if (n >= cap) n = cap - 1;
    memcpy(out, begin, n); out[n] = 0;
    return 1;
}

static int f1_resolution_patch_xml(char *xml, size_t cap)
{
    if (!strstr(xml, "<hardware_settings_config ") || !strstr(xml, "</hardware_settings_config>")) return 0;
    for (unsigned i = 0; i < sizeof(f1_resolution_settings)/sizeof(f1_resolution_settings[0]); ++i) {
        const struct f1_xml_setting *s = &f1_resolution_settings[i];
        if (f1_xml_attribute(xml, cap, s->tag, s->name, s->value) != 1) return 0;
    }
    return 1;
}

/* Resolution is required. A memory setting whose tag is missing from an older
 * XML is skipped; malformed XML or lack of space rejects the whole change. */
static int f1_memory_patch_xml(char *xml, size_t cap)
{
    if (!f1_resolution_patch_xml(xml, cap)) return 0;
    int applied = 0;
    for (unsigned i = 0; i < sizeof(f1_memory_settings)/sizeof(f1_memory_settings[0]); ++i) {
        const struct f1_xml_setting *s = &f1_memory_settings[i];
        int rc = f1_xml_attribute(xml, cap, s->tag, s->name, s->value);
        if (rc < 0) return 0;
        applied += rc == 1;
    }
    return applied;
}

static int f1_config_read(const char *path, char *data)
{
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    size_t size = fread(data, 1, F1_CONFIG_CAP, file);
    int ok = !ferror(file) && size && size < F1_CONFIG_CAP && !memchr(data, 0, size);
    fclose(file);
    if (ok) data[size] = 0;
    return ok;
}

static int f1_config_write(const char *path, const char *data, int exclusive)
{
    int fd = open(path, O_WRONLY | O_CREAT | (exclusive ? O_EXCL : O_TRUNC), 0666);
    if (fd < 0) return 0;
    size_t size = strlen(data), done = 0;
    while (done < size) {
        ssize_t n = write(fd, data + done, size - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) break;
        done += n;
    }
    int ok = done == size && fsync(fd) == 0;
    if (close(fd)) ok = 0;
    if (!ok) unlink(path); /* only our new/temporary file */
    return ok;
}

/* 2 = applied now, 1 = already applied earlier, 0 = failed (XML untouched). */
static int f1_prepare_game_graphics(const char *root)
{
    char path[768], temp[800], backup[800], marker[768], move[800];
    snprintf(marker, sizeof(marker), "%s/" F1_MEMORY_MARKER, root);
    if (!access(marker, F_OK)) return 1;
    const char *dirs[] = {"drive_c/My Games", "drive_c/My Games/FormulaOne2013",
                        "drive_c/My Games/FormulaOne2013/hardwaresettings"};
    for (unsigned i = 0; i < 3; ++i) {
        snprintf(path, sizeof(path), "%s/%s", root, dirs[i]);
        if (mkdir(path, 0777) && errno != EEXIST) return 0;
    }
    snprintf(path, sizeof(path), "%s/%s/hardware_settings_config.xml", root, dirs[2]);
    snprintf(temp, sizeof(temp), "%s.fextendo-tmp", path);
    snprintf(backup, sizeof(backup), "%s" F1_MEMORY_BACKUP, path);
    snprintf(move, sizeof(move), "%s.fextendo-rollback", path);
    /* Recover a launch interrupted between the two renames. */
    if (access(path, F_OK) && !access(move, F_OK) && rename(move, path)) return 0;
    char *original = malloc(F1_CONFIG_CAP), *changed = malloc(F1_CONFIG_CAP);
    int ok = 0, existing = !access(path, F_OK);
    if (!original || !changed) goto done;
    if (existing) { if (!f1_config_read(path, original)) goto done; }
    else {
        char base[768];
        snprintf(base, sizeof(base), "%s/drive_c/F1_2013/system/hardware_settings_config.xml", root);
        if (!f1_config_read(base, original)) goto done;
    }
    strcpy(changed, original);
    if (!f1_memory_patch_xml(changed, F1_CONFIG_CAP)) goto done;
    if (existing && access(backup, F_OK) && !f1_config_write(backup, original, 1)) goto done;
    if (!f1_config_write(temp, changed, 0)) goto done;
    if (existing && rename(path, move)) { unlink(temp); goto done; }
    if (rename(temp, path)) {
        if (existing) rename(move, path);
        unlink(temp); goto done;
    }
    if (existing) unlink(move);
    ok = f1_config_write(marker, "1280x720 fullscreen with circuit memory profile v5; applied once; later user choices preserved\n", 0) ? 2 : 0;
done:
    free(changed); free(original);
    return ok;
}

/* Compact key=value view of every setting the memory profile touches. */
static void f1_game_graphics_summary(const char *root, char *text, size_t capacity)
{
    static const struct { const char *label, *tag, *name; } keys[] = {
        {"w", "resolution", "width"}, {"h", "resolution", "height"},
        {"fs", "resolution", "fullscreen"}, {"msaa", "resolution", "multisampling"},
        {"tex_lod", "textures", "lod"}, {"shadows", "shadows", "enabled"},
        {"particles", "particles", "enabled"}, {"crowd", "crowd", "enabled"},
        {"cloth", "cloth", "enabled"}, {"ground", "groundcover", "mode"},
        {"trees", "trees", "lod"}, {"objects", "objects", "lod"},
        {"drivers", "vehicles", "characterQuality"}, {"car_lod", "vehicles", "lodQuality"},
        {"envmap", "envmap", "faces"}, {"water", "water", "detail"},
        {"mirrors", "mirrors", "enabled"}, {"ao", "dynamic_ambient_occ", "enabled"},
        {"track_refl", "track_reflections", "enabled"}
    };
    char path[768];
    snprintf(path, sizeof(path), "%s/drive_c/My Games/FormulaOne2013/hardwaresettings/hardware_settings_config.xml", root);
    char *xml = malloc(F1_CONFIG_CAP);
    snprintf(text, capacity, "Could not read active hardware_settings_config.xml");
    if (xml && f1_config_read(path, xml)) {
        size_t used = 0;
        text[0] = 0;
        for (unsigned i = 0; i < sizeof(keys)/sizeof(keys[0]) && used + 1 < capacity; ++i) {
            char value[32];
            if (f1_xml_get(xml, keys[i].tag, keys[i].name, value, sizeof(value)) != 1) strcpy(value, "?");
            int n = snprintf(text + used, capacity - used, "%s%s=%s", i ? " " : "", keys[i].label, value);
            if (n < 0) break;
            used += (size_t)n < capacity - used ? (size_t)n : capacity - used - 1;
        }
    }
    free(xml);
}
#endif
