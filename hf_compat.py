# hf_compat.py - Helper cho Hugging Face Spaces
import os
import sys


def is_huggingface():
    """Phat hien dang chay tren Hugging Face Spaces."""
    return bool(os.environ.get('SPACE_ID') or os.environ.get('SPACE_AUTHOR_NAME'))


def get_data_dir():
    """
    Tra ve thu muc co the ghi duoc.
    - Local: thu muc hien tai
    - HF: /tmp/ (vi code folder read-only)
    """
    if is_huggingface():
        return '/tmp'
    return os.getcwd()


def get_path(filename):
    """Tra ve full path cho file, dat trong data dir."""
    base = get_data_dir()
    return os.path.join(base, filename)


def get_port(default=5000):
    """
    Lay port tu env.
    - Local: 5000
    - HF: 7860 (mac dinh cua HF Spaces)
    """
    try:
        return int(os.environ.get('PORT', default if not is_huggingface() else 7860))
    except Exception:
        return 7860 if is_huggingface() else 5000


def should_skip_playwright():
    """
    Tra ve True neu nen bo qua Playwright.
    - Local: False (chay binh thuong)
    - HF: True (khong cai duoc chromium)
    """
    if is_huggingface():
        return True
    # Cho phep override bang env
    if os.environ.get('DISABLE_PLAYWRIGHT', '').lower() in ('1', 'true', 'yes'):
        return True
    return False


def print_env_info():
    """In thong tin moi truong khi server start."""
    if is_huggingface():
        print("=" * 60)
        print("  HUGGING FACE SPACES DETECTED")
        print(f"  SPACE_ID: {os.environ.get('SPACE_ID', '?')}")
        print(f"  Data dir: {get_data_dir()}")
        print(f"  Port: {get_port()}")
        print(f"  Playwright: DISABLED")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  LOCAL MODE")
        print(f"  Data dir: {get_data_dir()}")
        print(f"  Port: {get_port()}")
        print("=" * 60)


# Auto-detect khi import
IS_HF = is_huggingface()

if __name__ == '__main__':
    print_env_info()