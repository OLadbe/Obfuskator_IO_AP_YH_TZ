#!/usr/bin/env python3
import ast
import astor
import sys
import os

TARGET_BUILTINS = {'print', 'range', 'len', 'open', 'input', 'enumerate', 'map', 'filter'}


class BuiltinMappingCollector(ast.NodeVisitor):
    def __init__(self):
        self.obf_to_builtin = {}

    def visit_Assign(self, node: ast.Assign):
        # ищем: _bXXXX = __builtins_mod.print
        if len(node.targets) != 1:
            return
        t = node.targets[0]
        v = node.value

        if not isinstance(t, ast.Name):
            return
        if not isinstance(v, ast.Attribute):
            return
        if not (isinstance(v.value, ast.Name) and v.value.id == "__builtins_mod"):
            return

        builtin_name = v.attr
        if builtin_name in TARGET_BUILTINS:
            self.obf_to_builtin[t.id] = builtin_name


class BuiltinReplaceTransformer(ast.NodeTransformer):
    def __init__(self, obf_to_builtin: dict[str, str]):
        super().__init__()
        self.obf_to_builtin = obf_to_builtin

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load) and node.id in self.obf_to_builtin:
            return ast.copy_location(ast.Name(id=self.obf_to_builtin[node.id], ctx=node.ctx), node)
        return node


class NameUsageCollector(ast.NodeVisitor):
    def __init__(self):
        self.used = set()

    def visit_Name(self, node: ast.Name):
        self.used.add(node.id)
        self.generic_visit(node)


class BuiltinCleanupTransformer(ast.NodeTransformer):
    def __init__(self, obf_to_builtin: dict[str, str], used_names: set[str]):
        super().__init__()
        self.obf_to_builtin = obf_to_builtin
        self.used_names = used_names

    def visit_Assign(self, node: ast.Assign):
        # удаляем присвоения _bXXXX = __builtins_mod.<builtin>
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in self.obf_to_builtin:
                return None
        return self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        # удаляем import builtins as __builtins_mod если __builtins_mod не используется
        new_names = []
        for alias in node.names:
            if alias.name == "builtins" and alias.asname == "__builtins_mod":
                if "__builtins_mod" not in self.used_names:
                    continue
            new_names.append(alias)
        if not new_names:
            return None
        node.names = new_names
        return node


def restore_builtins(src_text: str) -> str:
    tree = ast.parse(src_text)

    collector = BuiltinMappingCollector()
    collector.visit(tree)
    obf_to_builtin = collector.obf_to_builtin

    if not obf_to_builtin:
        return src_text

    tree = BuiltinReplaceTransformer(obf_to_builtin).visit(tree)
    ast.fix_missing_locations(tree)

    name_usage = NameUsageCollector()
    name_usage.visit(tree)

    tree = BuiltinCleanupTransformer(obf_to_builtin, name_usage.used).visit(tree)
    ast.fix_missing_locations(tree)

    return astor.to_source(tree)


def main():
    if len(sys.argv) < 2:
        print("Usage: python deobfuscator_step3_restore_builtins.py target_deobf_step2.py")
        return

    target_path = sys.argv[1]
    if not os.path.exists(target_path):
        print(f"File not found: {target_path}")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        src = f.read()

    out_src = restore_builtins(src)
    base, ext = os.path.splitext(target_path)
    out_path = f"{base[:-2]}3.py"


    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write(f"# Deobfuscated step3 (restore builtins) from {target_path}\n")
        fo.write(out_src)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
