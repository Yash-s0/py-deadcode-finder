def read_file(path):
    try:
        return path.read_text(encoding="utf-8")
    except:
        return ""
