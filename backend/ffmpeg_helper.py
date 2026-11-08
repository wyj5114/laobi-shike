import os
import shutil
import subprocess
import sys
from dotenv import load_dotenv

from app.utils.logger import get_logger
logger = get_logger(__name__)


def _load_dotenv_from_multiple_paths():
    """尝试多个位置加载 .env，适配源码运行和 PyInstaller 打包场景。

    PyInstaller 打包后当前工作目录是 EXE 所在目录，而源码运行时 .env
    通常在项目根目录或 backend/ 同级。遍历常见候选路径确保能命中。
    """
    candidates = []
    # 1. 当前工作目录（EXE 所在目录）
    candidates.append(os.path.join(os.getcwd(), '.env'))
    # 2. 本脚本所在目录（backend/）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, '.env'))
    # 3. 项目根目录（backend/../.env）
    candidates.append(os.path.join(script_dir, '..', '.env'))
    # 4. PyInstaller 打包后的 _internal/ 子目录
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, '_internal', '.env'))

    for path in candidates:
        normalized = os.path.normpath(path)
        if os.path.isfile(normalized):
            load_dotenv(normalized)
            return
    # 都没找到，fallback 到默认行为（从 CWD 找）
    load_dotenv()


_load_dotenv_from_multiple_paths()
def get_ffmpeg_bin() -> str:
    """返回可直接调用的 ffmpeg 可执行文件路径。

    优先 FFMPEG_BIN_PATH（可以给目录，也可以直接给 ffmpeg.exe 的完整路径），
    其次系统 PATH，最后退回裸命令名（由系统再解析）。
    """
    explicit = (os.getenv("FFMPEG_BIN_PATH") or "").strip()
    if explicit:
        candidate = explicit
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which("ffmpeg")
    return found or "ffmpeg"


def check_ffmpeg_exists() -> bool:
    """
    检查 ffmpeg 是否可用。优先使用 FFMPEG_BIN_PATH 环境变量指定的路径。
    """
    ffmpeg_bin = get_ffmpeg_bin()
    logger.info(f"ffmpeg 路径: {ffmpeg_bin}")
    if ffmpeg_bin == "ffmpeg":
        # 没显式配置也没在 PATH 里找到，再按旧的“遍历 PATH”逻辑补一次，
        # 兼容某些把 ffmpeg 放在非标准目录、但已加入 PATH 的机器
        system_path = os.environ.get("PATH", "")
        for path_dir in system_path.split(os.pathsep):
            ffmpeg_exe_path = os.path.join(path_dir, "ffmpeg.exe")
            if os.path.isfile(ffmpeg_exe_path):
                ffmpeg_bin = ffmpeg_exe_path
                logger.info(f"在系统PATH中找到ffmpeg: {path_dir}")
                break
    else:
        # 把 ffmpeg 所在目录放到 PATH 最前面，让 ffmpeg-python / 子进程也能直接调用
        os.environ["PATH"] = os.path.dirname(ffmpeg_bin) + os.pathsep + os.environ.get("PATH", "")
    try:
        subprocess.run([ffmpeg_bin, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info("ffmpeg 已安装")
        return True
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        logger.info("ffmpeg 未安装")
        return False


def ensure_ffmpeg_or_raise():
    """
    校验 ffmpeg 是否可用，否则抛出异常并提示安装方式。
    """
    if not check_ffmpeg_exists():
        logger.error("未检测到 ffmpeg，请先安装后再使用本功能。")
        raise EnvironmentError(
            " 未检测到 ffmpeg，请先安装后再使用本功能。\n"
            "👉 下载地址：https://ffmpeg.org/download.html\n"
            "🪟 Windows 推荐：https://www.gyan.dev/ffmpeg/builds/\n"
            "💡 如果你已安装，请将其路径写入 `.env` 文件，例如：\n"
            "FFMPEG_BIN_PATH=/your/custom/ffmpeg/bin"
        )
