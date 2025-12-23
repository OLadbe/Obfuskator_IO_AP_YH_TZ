#!/usr/bin/env python3
import ast
import astor
import sys
import os
import re

OBF_NAME_RE = re.compile(r"^_v[A-Za-z]{8}$")


class RenameLocalsTransformer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.mapping = {}
        self.func_counter = 1
        self.class_counter = 1
        self.var_counter = 1

    def _map(self, old: str, kind: str) -> str:
        if old in self.mapping:
            return self.mapping[old]
        if kind == "func":
            new = f"func_{self.func_counter}"
            self.func_counter += 1
        elif kind == "class":
            new = f"Class{self.class_counter}"
            self.class_counter += 1
        else:
            new = f"var_{self.var_counter}"
            self.var_counter += 1
        self.mapping[old] = new
        return new

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if OBF_NAME_RE.match(node.name):
            node.name = self._map(node.name, "func")

        for arg in node.args.args:
            if OBF_NAME_RE.match(arg.arg):
                arg.arg = self._map(arg.arg, "var")

        if node.args.vararg and OBF_NAME_RE.match(node.args.vararg.arg):
            node.args.vararg.arg = self._map(node.args.vararg.arg, "var")

        if node.args.kwarg and OBF_NAME_RE.match(node.args.kwarg.arg):
            node.args.kwarg.arg = self._map(node.args.kwarg.arg, "var")

        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        if OBF_NAME_RE.match(node.name):
            node.name = self._map(node.name, "class")
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name):
        if OBF_NAME_RE.match(node.id):
            node.id = self._map(node.id, "var")
        return self.generic_visit(node)


def rename_locals(src_text: str) -> str:
    tree = ast.parse(src_text)
    tree = RenameLocalsTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    return astor.to_source(tree)


def main():
    if len(sys.argv) < 2:
        print("Usage: python deobfuscator_step4_rename_locals.py target_deobf_step3.py")
        return

    target_path = sys.argv[1]
    if not os.path.exists(target_path):
        print(f"File not found: {target_path}")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        src = f.read()

    out_src = rename_locals(src)
    base, ext = os.path.splitext(target_path)
    out_path = f"{base.split('_')[0]}_deobf.py"



    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write(f"# Deobfuscated step4 (rename locals) from {target_path}\n")
        fo.write(out_src)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
