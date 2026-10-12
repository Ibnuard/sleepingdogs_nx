"""Compose the validated v3 launcher with native production-counter policy."""
import launcher_v3_overlay as v3
from launcher_v3_overlay import ROOT, SOURCE, settings_overlay, wine_overlay, osk_overlay, lsfg_overlay, replace
from launcher_v4_runtime import runtime_overlay as native_runtime_overlay


def runtime_overlay(text):
    text = native_runtime_overlay(v3.runtime_overlay(text))
    return text.replace('0.1.0-launcher.3', '0.1.0-launcher.4').replace(
        'sleepingdogs-launcher-v3-state-v1', 'sleepingdogs-launcher-v4-inline-v1')
