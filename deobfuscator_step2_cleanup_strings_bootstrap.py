#!/usr/bin/env python3
import ast
import astor
import sys
import os


class NameUsageCollector(ast.NodeVisitor):
    def __init__(self):
        self.used_names = set()

    def visit_Name(self, node: ast.Name):
        self.used_names.add(node.id)
        self.generic_visit(node)


class CleanupStringsBootstrapTransformer(ast.NodeTransformer):
    def __init__(self, used_names: set[str]):
        super().__init__()
        self.used_names = used_names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # удаляем def _s(...), если _s больше нигде не используется
        if node.name == "_s" and "_s" not in self.used_names:
            return None
        return self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        new_names = []
        for alias in node.names:
            if alias.name == "base64" and "base64" not in self.used_names:
                continue
            new_names.append(alias)

        if not new_names:
            return None
        node.names = new_names
        return node


def cleanup_bootstrap(src_text: str) -> str:
    tree = ast.parse(src_text)

    collector = NameUsageCollector()
    collector.visit(tree)

    tree = CleanupStringsBootstrapTransformer(collector.used_names).visit(tree)
    ast.fix_missing_locations(tree)
    return astor.to_source(tree)


def main():
    if len(sys.argv) < 2:
        print("Usage: python deobfuscator_step2_cleanup_strings_bootstrap.py target_deobf_step1.py")
        return

    target_path = sys.argv[1]
    if not os.path.exists(target_path):
        print(f"File not found: {target_path}")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        src = f.read()

    out_src = cleanup_bootstrap(src)
    base, ext = os.path.splitext(target_path)
    out_path = f"{base[:-2]}2.py"

    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write(f"# Deobfuscated step2 (cleanup _s/base64) from {target_path}\n")
        fo.write(out_src)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
