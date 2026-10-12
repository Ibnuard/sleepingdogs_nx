"""Execute the linked v4 ARM64 startup policies and audit required symbols."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    text = (ROOT / 'tools/test_launcher_v2_binary.py').read_text()
    text = text.replace('local/launcher-v2', 'local/launcher-v4')
    namespace = {'__name__': 'v4_binary', '__file__': __file__}
    exec(compile(text, str(ROOT / 'tools/test_launcher_v2_binary.py'), 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
