"""
NexusMind Backend 启动入口
"""

import os
import sys


def _prepare_runtime():
    if sys.platform == 'win32':
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='replace')

    backend_root = os.path.dirname(os.path.abspath(__file__))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)


_prepare_runtime()

from app import create_app
from app.config import Config


def _read_server_options():
    return {
        "host": os.environ.get('FLASK_HOST', '0.0.0.0'),
        "port": int(os.environ.get('FLASK_PORT', 5001)),
        "debug": Config.DEBUG,
        "threaded": True,
    }


def main():
    """主函数"""
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f"  - {err}")
        print("\n请检查 .env 文件中的配置")
        sys.exit(1)

    app = create_app()
    app.run(**_read_server_options())


if __name__ == '__main__':
    main()
