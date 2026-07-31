from pathlib import Path
import os
import runpy

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    target = root / "scraping" / "get_filmes.py"
    os.chdir(root / "scraping")
    runpy.run_path(str(target), run_name="__main__")
