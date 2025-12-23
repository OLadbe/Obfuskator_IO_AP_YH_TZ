#!/usr/bin/env python3
import ast
import astor
import base64
import sys
import os


class StringDeobfTransformer(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)

        if isinstance(node.func, ast.Name) and node.func.id == "_s":
            if len(node.args) == 1 and not node.keywords:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    try:
                        decoded = base64.b64decode(arg.value).decode("utf-8")
                    except Exception:
                        return node
                    return ast.copy_location(ast.Constant(value=decoded), node)
        return node


def deobfuscate_strings(src_text: str) -> str:
    tree = ast.parse(src_text)
    tree = StringDeobfTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    return astor.to_source(tree)


def main():
    if len(sys.argv) < 2:
        print("Usage: python deobfuscator_step1_strings.py target_obf.py")
        return

    target_path = sys.argv[1]
    if not os.path.exists(target_path):
        print(f"File not found: {target_path}")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        src = f.read()

    out_src = deobfuscate_strings(src)
    base, ext = os.path.splitext(target_path)
    out_path = f"{base[:-4]}_d1.py"

    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write(f"# Deobfuscated step1 (strings) from {target_path}\n")
        fo.write(out_src)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
