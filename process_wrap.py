def load_wrap(path):
    wrap = open(path, 'r', encoding='utf-8').readlines()
    HEADER = {}
    for line in wrap[1:]:
        line = line.strip()
        if not line:
            continue
        column, val = line.split(':',maxsplit=1)
        HEADER[column] = val
    return HEADER