"""Quiet production launch over the immutable, user-tested launcher v4.

Debug must be explicitly selected in the launcher. Legacy diagnostic files
cannot enable output during ordinary Play. Functional persistence is retained.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError((old[:120], text.count(old)))
    return text.replace(old, new, 1)


def runtime(text):
    text = once(text, 'static FILE *log_file;',
                'static FILE *log_file;\n#include "diagnostics.h"')
    text = once(text,
        '                    fx_ui_view.debug=fx_ui_view.debug_launch&&fx_ui_view.tile==3;',
        '                    fx_ui_view.debug=fx_ui_view.debug_launch&&fx_ui_view.tile==3;\n'
        '                    sd_production_select_debug(fx_ui_view.debug);')
    text = once(text, 'if(!fx_debug_file)fx_debug_file=f1_open_runtime_log(RUNTIME_DIR);',
                'if(fx_ui_view.debug&&!fx_debug_file)fx_debug_file=f1_open_runtime_log(RUNTIME_DIR);')
    text = once(text, '                        __atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);',
                '                        __atomic_store_n(&fx_debug_live,fx_ui_view.debug,__ATOMIC_RELEASE);')
    text = once(text, 'unsigned crash_rc=wine_nx_f1_crash_init(fx_ui_view.debug,renderer,selected);',
                'unsigned crash_rc=fx_ui_view.debug?wine_nx_f1_crash_init(1,renderer,selected):0;')
    # Diagnostic worker is unnecessary during normal Play. Required maintenance
    # stays active and records first successful Present even with every log off.
    begin = text.index('    pthread_t startup_monitor;')
    end = text.index('\n\n', begin)
    monitor = text[begin:end]
    text = text[:begin] + text[end:]
    text = once(text, '    else if (!fx_launcher_start()) return 0;',
                '    else if (!fx_launcher_start()) return 0;\n'
                '    sd_production_select_debug(guest_tests || fx_ui_view.debug);\n'
                '    if(wine_nx_sd_diagnostics_active()) {\n' + monitor + '\n    }')
    text = once(text, '    if (ticks % 5 == 0) horizon_registry_flush();',
                '    if (ticks % 5 == 0) { horizon_registry_flush(); fx_history_flush(); }')
    text = once(text, '    setenv("WINEDEBUG", "-all", 1);',
                '    setenv("WINEDEBUG", "-all", 1);\n'
                '    setenv("DXVK_LOG_PATH", "none", 1);\n'
                '    setenv("DXVK_LOG_LEVEL", "none", 1);')
    text = once(text, 'setenv("DXVK_LOG_PATH",RUNTIME_DIR "/native-dxvk-h4",1);',
                'setenv("DXVK_LOG_PATH",wine_nx_sd_diagnostics_active()?RUNTIME_DIR "/native-dxvk-h4":"none",1);\n'
                '        setenv("DXVK_LOG_LEVEL",wine_nx_sd_diagnostics_active()?"info":"none",1);')
    # Remove duplicate guest logging keys, then append exactly one policy.
    text = once(text,
        '        const char trace_key[] = "FEXTENDO_TRACE=0\\0DXVK_LOG_LEVEL=none\\0DXVK_LOG_PATH=none\\0WINEDEBUG=-all";\n'
        '        if (environment_bytes && environment_bytes + sizeof(trace_key) <= sizeof(short_environment)) {\n'
        '            memcpy(short_environment, environment, environment_bytes);\n'
        '            memcpy(short_environment + environment_bytes - 1, trace_key, sizeof(trace_key));\n'
        '            /* Production never enables guest diagnostics. */\n'
        '            environment_bytes += sizeof(trace_key);\n'
        '            short_environment[environment_bytes - 1] = 0;\n'
        '            environment = short_environment;\n'
        '        }',
        '        size_t quiet_bytes=sd_production_environment(short_environment,sizeof(short_environment),\n'
        '            environment,environment_bytes,wine_nx_sd_diagnostics_active());\n'
        '        if(!quiet_bytes)return NULL;\n'
        '        environment=short_environment;environment_bytes=quiet_bytes;')
    text = once(text, '#include "diagnostics.h"',
                '#include "diagnostics.h"\n#include "environment.h"')
    # Profilers and probes are optional observers, never scheduler policy.
    text = once(text, '    fex_game_timing_enabled = !guest_tests &&',
                '    fex_game_timing_enabled = wine_nx_sd_diagnostics_active() && !guest_tests &&')
    text = once(text, '    fex_gap_probe_enabled = wine_nx_config_file_bool',
                '    fex_gap_probe_enabled = wine_nx_sd_diagnostics_active() && wine_nx_config_file_bool')
    text = once(text, 'sd_perf_counters = sd_perf_counter_policy(',
                'sd_perf_counters = wine_nx_sd_diagnostics_active() && sd_perf_counter_policy(')
    text = once(text, '    runtime_profile = wine_nx_config_file_bool',
                '    runtime_profile = wine_nx_sd_diagnostics_active() && wine_nx_config_file_bool')
    text = once(text, 'runtime_profile = !guest_tests && wine_nx_config_file_bool',
                'runtime_profile = wine_nx_sd_diagnostics_active() && !guest_tests && wine_nx_config_file_bool')
    text = once(text, '!sd_com_enabled && !guest_tests && sd_frame_diag_requested',
                'wine_nx_sd_diagnostics_active() && !sd_com_enabled && !guest_tests && sd_frame_diag_requested')
    text = once(text, 'pes13_controller_trace_enabled = wine_nx_config_file_bool',
                'pes13_controller_trace_enabled = wine_nx_sd_diagnostics_active() && wine_nx_config_file_bool')
    text = once(text, 'int vulkan_probe = wine_nx_config_file_bool',
                'int vulkan_probe = wine_nx_sd_diagnostics_active() && wine_nx_config_file_bool')
    text = text.replace('0.1.0-launcher.4', '0.1.0-production.1').replace(
        'sleepingdogs-launcher-v4-inline-v1', 'sleepingdogs-production-v1')
    text = text.replace('Sleeping Dogs launcher could not start the game. Check fex-runtime.log.',
                        'Sleeping Dogs could not start. Check installation files or enable Launch Debug in Settings.')
    text = text.replace('Cannot apply graphics profile. Check SD space and fex-runtime.log.',
                        'Cannot apply graphics profile. Check SD space or use Launch Debug.')
    text = text.replace('Game stopped (0x%08x). See fex-runtime.log and crash.log.',
                        'Game stopped (0x%08x). Enable Launch Debug in Settings to capture details.')
    # Quiet launch failures must not direct users to a stale log from an older session.
    for old,new in (
        ('Check SD space and fex-runtime.log.','Check SD space or enable Launch Debug.'),
        ('See fex-runtime.log and HKShip_dxgi.log.','Enable Launch Debug in Settings.'),
        ('See fex-runtime.log.','Enable Launch Debug in Settings.'),
        ('Crash capture: crash.log + fex-runtime.log.','Enable Launch Debug in Settings for logs.'),
        ('Save fex-runtime.log and DXVK logs','Use Launch Debug for logs')):
        text=text.replace(old,new)
    return text


def checker(text):
    return once(text, '    /* Small standalone report also exists when the Play log was never opened. */',
                '    /* Cache is functional state; a text report is explicit diagnostics only. */\n'
                '    if(!wine_nx_sd_diagnostics_active())return;')


def logger(text):
    # Logger's minimum level is captured by a static constructor before main.
    # A late setenv alone cannot disable that already-created native logger.
    text = once(text, '#include "log.h"',
                '#include "log.h"\nextern "C" int wine_nx_sd_diagnostics_active(void);')
    return once(text, '  void Logger::emitMsg(LogLevel level, const std::string& message) {',
                '  void Logger::emitMsg(LogLevel level, const std::string& message) {\n'
                '    if (!wine_nx_sd_diagnostics_active()) return;')


def horizon_present(text):
    text = once(text, 'extern "C" void wine_nx_runtime_trace(const char*);',
                'extern "C" void wine_nx_runtime_trace(const char*);\n'
                'extern "C" int wine_nx_sd_diagnostics_active(void);')
    # Do not lose first-frame history when skipping the diagnostic clock/mutex.
    return once(text, '    if(result)return;\n    std::lock_guard<std::mutex> guard(metrics_mutex);',
                '    if(result)return;\n'
                '    if(!wine_nx_sd_diagnostics_active()){wine_nx_sd_com_first_present();return;}\n'
                '    std::lock_guard<std::mutex> guard(metrics_mutex);')
