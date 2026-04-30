def _read_version():
    p = Path(SPECPATH).resolve().parent / "src" / "version.py"
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if "__version__" in line:
                return line.split("=")[1].strip().strip('"').strip("'")
