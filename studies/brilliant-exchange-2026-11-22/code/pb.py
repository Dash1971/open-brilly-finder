"""Schema-less protobuf decoder -> list of (field, type, value); nested messages decoded recursively."""
import struct, base64, json
def rv(b, i):
    x = 0; s = 0
    while True:
        c = b[i]; i += 1
        x |= (c & 127) << s
        if not c & 128: break
        s += 7
        if s > 70: raise ValueError
    return x, i
def is_text(s):
    if any(c < 9 or 13 < c < 32 for c in s): return False
    try: s.decode('utf-8'); return True
    except Exception: return False
def dec(b, depth=0):
    i = 0; out = []
    n = len(b)
    while i < n:
        k, i = rv(b, i); f, w = k >> 3, k & 7
        if f == 0 or f > 5000: raise ValueError
        if w == 0:
            v, i = rv(b, i); out.append((f, 'v', v))
        elif w == 1:
            if i + 8 > n: raise ValueError
            out.append((f, 'd', struct.unpack('<d', b[i:i+8])[0])); i += 8
        elif w == 5:
            if i + 4 > n: raise ValueError
            out.append((f, 'f', struct.unpack('<f', b[i:i+4])[0])); i += 4
        elif w == 2:
            ln, i = rv(b, i)
            if i + ln > n: raise ValueError
            s = bytes(b[i:i+ln]); i += ln
            val = None
            if ln and depth < 14:
                try: val = ('m', dec(s, depth + 1))
                except Exception: val = None
            if val is None: val = ('s', s.decode('utf-8') if is_text(s) else s)
            out.append((f, val[0], val[1]))
        else: raise ValueError
    return out
def zz(v): return (v >> 1) ^ -(v & 1)
def load(path):
    msgs = json.load(open(path))
    big = max((base64.b64decode(m) for m in msgs), key=len)
    return dec(big)
def get(n, *path):
    """first match along a field path"""
    cur = n
    for f in path:
        nxt = [x for x in cur if x[0] == f]
        if not nxt: return None
        cur = nxt[0][2]
    return cur
def allf(n, f): return [x[2] for x in n if x[0] == f]
def show(n, d=0, maxd=6, maxs=60):
    out = []
    for f, t, v in n:
        if t == 'm': out.append(f"{f}{{{show(v, d+1, maxd, maxs) if d < maxd else '..'}}}")
        elif t == 's': out.append(f'{f}"{(v if isinstance(v, str) else repr(v))[:maxs]}"')
        elif t in 'fd': out.append(f"{f}~{v:.4g}")
        else: out.append(f"{f}:{v}")
    return ' '.join(out)
