import sys
import json
import platform
from pathlib import Path

sys.dont_write_bytecode = True
if platform.system() != 'Windows' or sys.version_info[:3] != (3, 12, 14) or not sys.flags.isolated:
    print(json.dumps({'status':'error','message':'Use the Windows launcher with Python 3.12.14 in isolated mode (-I).'}), file=sys.stderr)
    raise SystemExit(2)
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'foundation')]
from research_toolkit.cli import main
if __name__ == '__main__':
    raise SystemExit(main(ROOT))
