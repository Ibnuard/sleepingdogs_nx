"""Run retained launcher, keyboard, checker and Vulkan-policy regressions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    text = (ROOT / 'tools/test_launcher_v3.py').read_text()
    text = text.replace('launcher-v3', 'launcher-v4')
    namespace = {'__name__': 'v4_fixture', '__file__': __file__}
    exec(compile(text, str(ROOT / 'tools/test_launcher_v3.py'), 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
