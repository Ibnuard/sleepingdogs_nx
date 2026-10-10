/* LGPL-2.1-or-later. Called under the existing Wine log mutex. */
static int sd_fault_wine_line(const char *line)
{
    static unsigned seh_lines, wow_lines, backtrace_lines;
    /* Recursive guest faults otherwise generate thousands of warning lines.
     * Keep the initial backtrace and all other warnings/errors. */
    if (strstr(line, ":warn:seh:") && strstr(line, "backtrace:")) {
        if (backtrace_lines >= 128) return 0;
        ++backtrace_lines;
    }
    if (strstr(line, ":err:") || strstr(line, ":warn:") || strstr(line, "[SD-DEP]")) return 1;
    if (strstr(line, ":seh:")) {
        if (seh_lines >= 256) return 0;
        ++seh_lines;
    }
    if (strstr(line, ":wow:")) {
        if (!strstr(line, ":call_user_exception_dispatcher ") || wow_lines >= 32) return 0;
        ++wow_lines;
    }
    return 1;
}
