"""Render the actual Sleeping Dogs C launcher using ASan/UBSan on the host."""
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fextendo_host_ui', root / 'vendor/f1-tools/check_launcher.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.HARNESS = module.HARNESS.replace('switch/f1-fex', 'switch/sleepingdogs-fex')
module.HARNESS = module.HARNESS.replace('F1_2013.exe', 'HKShip.exe').replace('F1_2013_dxgi.log', 'HKShip_dxgi.log')
module.HARNESS = module.HARNESS.replace('F1_2013', 'SleepingDogs').replace('F1 2013', 'Sleeping Dogs')
module.HARNESS = module.HARNESS.replace('F1:', 'Sleeping Dogs:').replace('F1 again', 'Sleeping Dogs again')
module.HARNESS = module.HARNESS.replace('F1 maps', 'Sleeping Dogs maps')
module.HARNESS = module.HARNESS.replace('struct fx_art art;', 'fx_input_mode=fx_input_mode_load(argv[1]);\n    struct fx_art art;')
module.HARNESS = module.HARNESS.replace('.settings_page=n,.sound=1,', '.settings_page=n,.selected=fx_selected(argv[1]),.renderer=fx_renderer_selected(argv[1]),.sound=1,')
module.main()
