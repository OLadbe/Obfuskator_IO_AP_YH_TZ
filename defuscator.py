#!/usr/bin/env python3
"""
deobfuscator_step1_strings.py

Шаг 1 дефускатора для obfuscator_viewable.py:
 - находит вызовы _s("BASE64") с константным аргументом
 - декодирует base64 -> utf-8 строку
 - заменяет вызов _s(...) на обычный строковый литерал

Usage:
    python deobfuscator_step1_strings.py target_obf.py
Output:
    target_obf_deobf_step1.py
"""

import ast
import astor
import base64
import sys
import os


class StringDeobfTransformer(ast.NodeTransformer):
    """
    Ищет вызовы _s("...") и раскодирует их обратно в str.

    Пример:
        _s("aGVsbG8=") -> "hello"
    """

    def visit_Call(self, node: ast.Call):
        # Сначала обходим потомков, чтобы не потерять структуру
        self.generic_visit(node)

        # Проверяем, что это вызов _s(...)
        if isinstance(node.func, ast.Name) and node.func.id == "_s":
            # Ожидаем ровно один позиционный аргумент без kwargs
            if len(node.args) == 1 and not node.keywords:
                arg = node.args[0]
                # Нас интересует только константа-строка (base64)
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    b64_value = arg.value
                    try:
                        decoded_bytes = base64.b64decode(b64_value)
                        decoded_str = decoded_bytes.decode("utf-8")
                    except Exception:
                        # Если что-то пошло не так — не трогаем этот узел
                        return node

                    # Заменяем вызов _s(...) на строковый литерал
                    new_node = ast.Constant(value=decoded_str)
                    return ast.copy_location(new_node, node)

        return node


def deobfuscate_strings(src_text: str) -> str:
    """
    Дефускация только строк (_s("...") -> "...")
    Возвращает новый исходный код как текст.
    """
    tree = ast.parse(src_text)
    transformer = StringDeobfTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    return astor.to_source(new_tree)


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

    deobf_src = deobfuscate_strings(src)

    base, ext = os.path.splitext(target_path)
    out_path = f"{base}_deobf_step1{ext or '.py'}"

    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write("# Deobfuscated (step 1: strings) from {}\n".format(target_path))
        fo.write(deobf_src)

    print("Saved step-1 deobfuscated file:", out_path)


if __name__ == "__main__":
    main()
