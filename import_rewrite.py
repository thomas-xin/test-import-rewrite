with open("in.py", "r", encoding="utf-8") as f:
    data = f.read().splitlines()

imports = {}
inlines = {}
renames = {}
out = []
for line in data:
    if line.startswith("import "):
        keys = line[7:].split(",")
        for key in keys:
            key = key.strip()
            if key and key not in ("contextlib", "concurrent.futures"):
                if key[0] != "." and "." in key:
                    key, value = key.split(".", 2)
                    if " as " in value:
                        value, name = value.split(" as ", 2)
                        v = key + "." + value
                        if v in renames:
                            renames[v].add(name)
                        else:
                            renames[v] = {name}
                    if key in inlines:
                        inlines[key].add(value)
                    else:
                        inlines[key] = {value}
                elif " as " in key:
                    key, name = key.split(" as ", 2)
                    if key in renames:
                        renames[key].add(name)
                    else:
                        renames[key] = {name}
                if key not in imports:
                    imports[key] = None
    elif line.startswith("from ") and " import " in line:
        i = line.index(" import ")
        key = line[5:i]
        value = line[i + 8:]
        if value == "*":
            if key not in imports:
                imports[key] = None
        if key in imports and imports[key] is not None:
            imports[key].add(value)
        else:
            imports[key] = {value}
    else:
        out.append(line)

start = """import contextlib, concurrent.futures

# A context manager that enables concurrent imports.
class MultiThreadedImporter(contextlib.AbstractContextManager, contextlib.ContextDecorator):

    def __init__(self, glob=None):
        self.glob = glob
        self.exc = concurrent.futures.ThreadPoolExecutor(max_workers=12)
        self.out = {}

    def __enter__(self):
        return self

    def __import__(self, *modules):
        for module in modules:
            self.out[module] = self.exc.submit(__import__, module)
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_type and exc_value:
            raise exc_value
    
    def close(self):
        for k in tuple(self.out):
            self.out[k] = self.out[k].result()
        glob = self.glob if self.glob is not None else globals()
        glob.update(self.out)
        self.exc.shutdown(True)

with MultiThreadedImporter() as importer:
    importer.__import__(
"""

if imports or inlines or renames:

    specials = set()
    for value, names in renames.items():
        for name in names:
            specials.add(name + " = " + value)
    line = "\n".join(specials)
    print(line)
    out.insert(0, line)
    specials = set()
    for key, value in imports.items():
        if value is not None:
            specials.add(f"from {key} import {', '.join(value)}")
    line = "\n".join(specials)
    print(line)
    out.insert(0, line)
    specials = set()
    for key, value in inlines.items():
        specials.add("import " + ", ".join(key + "." + v for v in value))
    line = "\n".join(specials)
    print(line)
    out.insert(0, line)
    out.insert(0, "    )")
    for key in imports:
        out.insert(0, "        \"" + key + "\",")

    with open("out.py", "w", encoding="utf-8") as f:
        f.write(start + "\n".join(out))
