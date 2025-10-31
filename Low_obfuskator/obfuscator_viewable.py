#!/usr/bin/env python3
"""
obfuscator_viewable.py

Проста версія обфускатора, яка:
 - змінює назви локальних змінних / функцій / класів,
 - обфускує string literals (замінює на _s("BASE64")),
 - замінює деякі вбудовані функції (print, range, len ...) на випадкові імена
 - генерує зручний обфускований .py, який можна відкрити і виконати.

Usage:
    python obfuscator_viewable.py target.py
Output:
    target_obf.py
"""
import ast
import astor
import random
import string
import base64
import sys
import builtins

# Конфіг: які builtins замінювати
TARGET_BUILTINS = {'print', 'range', 'len', 'open', 'input', 'enumerate', 'map', 'filter'}

def rand_name(prefix='_x', n=10):
    return prefix + ''.join(random.choice(string.ascii_letters) for _ in range(n))

class RenameTransformer(ast.NodeTransformer):

    def __init__(self, reserved):
        super().__init__()
        self.map = {}      # original -> obf
        self.reserved = set(reserved)  # імена, які не трогаємо

    def _get(self, name):
        if name in self.map:
            return self.map[name]
        new = rand_name('_v', 8)
        self.map[name] = new
        return new

    def visit_FunctionDef(self, node):
        # змінюємо ім'я функції, але не якщо воно в reserved (наприклад main API)
        if node.name not in self.reserved and not node.name.startswith('__'):
            node.name = self._get(node.name)
        # аргументи
        for arg in node.args.args:
            if arg.arg not in self.reserved and not arg.arg.startswith('__'):
                arg.arg = self._get(arg.arg)
        # vararg / kwarg
        if node.args.vararg and node.args.vararg.arg not in self.reserved:
            node.args.vararg.arg = self._get(node.args.vararg.arg)
        if node.args.kwarg and node.args.kwarg.arg not in self.reserved:
            node.args.kwarg.arg = self._get(node.args.kwarg.arg)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        if node.name not in self.reserved and not node.name.startswith('__'):
            node.name = self._get(node.name)
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        # замінюємо імена у локальному контексті (Store/Load/Del)
        if isinstance(node.ctx, (ast.Store, ast.Load, ast.Del)):
            n = node.id
            if n in self.reserved:
                return node
            # пропускаємо імпортовані модулі і атрибути (це простіше — уникнемо ломки)
            if n.isidentifier() and not n.startswith('__'):
                # не міняємо глобальні builtins, вони будуть оброблені окремо
                # ми міняємо лише ті, що зустріли в map або створимо нові
                if n in self.map:
                    node.id = self.map[n]
                else:
                    # Щоб не ламати імпорти/зовнішні API: міняємо лише локальні імена, які зустрічаються як Store або в defs
                    # Якщо це Load-only і не в map — залишимо без змін (запобігає перевизначенню модулів)
                    if isinstance(node.ctx, ast.Store):
                        node.id = self._get(n)
        return node

class StringObfTransformer(ast.NodeTransformer):
    """
    Замінює літерали str на виклики _s("BASE64")
    """
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value != "":
            raw = node.value.encode('utf-8')
            b64 = base64.b64encode(raw).decode('ascii')
            call = ast.Call(func=ast.Name(id='_s', ctx=ast.Load()),
                            args=[ast.Constant(value=b64)],
                            keywords=[])
            return ast.copy_location(call, node)
        return node

def build_builtin_assignments():
    """
    Повертає список ast.Assign на початок модуля:
      import builtins as __builtins_mod
      _bXYZ = __builtins_mod.print
    і також map builtins_name -> obf_name
    """
    assigns = []
    map_b = {}
    # імпорт builtins
    imp = ast.Import(names=[ast.alias(name='builtins', asname='__builtins_mod')])
    assigns.append(imp)
    for name in TARGET_BUILTINS:
        if hasattr(builtins, name):
            obf = rand_name('_b', 8)
            # створити: obf = __builtins_mod.<name>
            target = ast.Attribute(value=ast.Name(id='__builtins_mod', ctx=ast.Load()), attr=name, ctx=ast.Load())
            assign = ast.Assign(targets=[ast.Name(id=obf, ctx=ast.Store())], value=target)
            assigns.append(assign)
            map_b[name] = obf
    return assigns, map_b

class BuiltinReplaceTransformer(ast.NodeTransformer):
    """Замінює звернення до TARGET_BUILTINS (Name nodes) на нові імена (obf)"""
    def __init__(self, builtin_map):
        super().__init__()
        self.builtin_map = builtin_map

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if node.id in self.builtin_map:
                return ast.copy_location(ast.Name(id=self.builtin_map[node.id], ctx=ast.Load()), node)
        return node

def make_bootstrap_strings():
    """
    _s decoder: приймає base64 string, повертає str
    Ми повертаємо AST nodes (FunctionDef + maybe helper import)
    """
    src = '''
import base64
def _s(b64: str):
    try:
        return base64.b64decode(b64).decode('utf-8')
    except Exception:
        # fallback: attempt bytes decode
        return ''.join(chr(c) for c in base64.b64decode(b64))
'''
    mod = ast.parse(src)
    return mod.body  # список nodes

def obfuscate_source_text(src_text, preserve_names=None):
    """
    preserve_names: імена, які не обфускувати (наприклад: ['main_api', 'CONSTANT'])
    """
    preserve = set(preserve_names or [])
    tree = ast.parse(src_text)
    # 1) Обфуски builtins — створимо присвоєння і замінимо звернення
    builtin_assigns, builtin_map = build_builtin_assignments()
    tree = BuiltinReplaceTransformer(builtin_map).visit(tree)
    ast.fix_missing_locations(tree)

    # 2) Обфускуємо рядки
    tree = StringObfTransformer().visit(tree)
    ast.fix_missing_locations(tree)

    # 3) Перейменування локалей
    ren = RenameTransformer(reserved=preserve.union(set(builtin_map.values())))
    tree = ren.visit(tree)
    ast.fix_missing_locations(tree)

    # 4) Зібрати фінальний модуль: bootstrap (_s func) + builtin assigns + rest
    final = ast.Module(body=[], type_ignores=[])
    # додати _s decoder
    final.body.extend(make_bootstrap_strings())
    # додати присвоєння для builtins
    final.body.extend(builtin_assigns)
    # додати основний код (body)
    final.body.extend(tree.body)
    ast.fix_missing_locations(final)
    return final, ren.map, builtin_map

def main():
    if len(sys.argv) < 2:
        print("Usage: python obfuscator_viewable.py target.py")
        return
    target = sys.argv[1]
    with open(target, 'r', encoding='utf-8') as f:
        src = f.read()

    mod, rename_map, builtin_map = obfuscate_source_text(src, preserve_names={'__all__'})
    # згенерувати код
    out_src = astor.to_source(mod)
    out_path = target.replace('.py', '_obf.py')
    with open(out_path, 'w', encoding='utf-8') as fo:
        fo.write("# Obfuscated by obfuscator_viewable.py\n")
        fo.write(out_src)
    print("Saved obfuscated file:", out_path)
    if rename_map:
        print("Renamed symbols (sample):")
        for k, v in list(rename_map.items())[:20]:
            print("  ", k, "->", v)
    if builtin_map:
        print("Builtin replacements:")
        for k, v in builtin_map.items():
            print("  ", k, "->", v)

if __name__ == '__main__':
    main()
