# Obfuscated by obfuscator_viewable.py
import base64


def _s(b64: str):
    try:
        return base64.b64decode(b64).decode('utf-8')
    except Exception:
        return ''.join(chr(c) for c in base64.b64decode(b64))


import builtins as __builtins_mod
_bmDwLlUJu = __builtins_mod.len
_bIpGPlKKg = __builtins_mod.map
_bxwiZtnKc = __builtins_mod.print
_bHkGSUZQQ = __builtins_mod.filter
_bvwESqNGH = __builtins_mod.range
_bdWTsUDDX = __builtins_mod.enumerate
_bokdxpevS = __builtins_mod.open
_bHCBpSLGx = __builtins_mod.input
_vAGCUsOzi = 5
_vwieyuDwc = 7
_bxwiZtnKc(_vAGCUsOzi + _vwieyuDwc)
