from pathlib import Path

import tree_sitter_c
import tree_sitter_cpp
from tree_sitter import Language, Parser, Query, QueryCursor

C_LANGUAGE = Language(tree_sitter_c.language())
CPP_LANGUAGE = Language(tree_sitter_cpp.language())

LANG_MAP = {
    ".c": C_LANGUAGE,
    ".h": CPP_LANGUAGE,
    ".cpp": CPP_LANGUAGE,
    ".hpp": CPP_LANGUAGE,
    ".cc": CPP_LANGUAGE,
    ".cxx": CPP_LANGUAGE,
}

# Queries for functions, structs, and classes
SYMBOL_QUERIES = {
    ".c": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
    ]""",
    ".h": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
        (class_specifier name: (type_identifier) @_name body: (_)) @class
    ]""",
    ".cpp": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
        (class_specifier name: (type_identifier) @_name body: (_)) @class
    ]""",
    ".hpp": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
        (class_specifier name: (type_identifier) @_name body: (_)) @class
    ]""",
    ".cc": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
        (class_specifier name: (type_identifier) @_name body: (_)) @class
    ]""",
    ".cxx": """[
        (function_definition) @func
        (struct_specifier name: (type_identifier) @_name body: (_)) @struct
        (class_specifier name: (type_identifier) @_name body: (_)) @class
    ]""",
}


def _get_symbol_name(node, content: bytes) -> str | None:
    """Extract symbol name from a function, struct, or class node."""
    node_type = node.type

    if node_type == "function_definition":
        # For functions: look for declarator -> (function_declarator -> declarator) or direct identifier
        declarator = node.child_by_field_name("declarator")
        while declarator:
            if declarator.type == "function_declarator":
                inner = declarator.child_by_field_name("declarator")
                if inner:
                    if inner.type == "identifier":
                        return content[inner.start_byte : inner.end_byte].decode()
                    # Handle qualified names like ClassName::method
                    if inner.type == "qualified_identifier":
                        name_node = inner.child_by_field_name("name")
                        if name_node:
                            return content[
                                name_node.start_byte : name_node.end_byte
                            ].decode()
                break
            elif declarator.type == "identifier":
                return content[declarator.start_byte : declarator.end_byte].decode()
            declarator = declarator.child_by_field_name("declarator")

    elif node_type in ("struct_specifier", "class_specifier"):
        # For structs/classes: look for name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return content[name_node.start_byte : name_node.end_byte].decode()

    return None


def extract_symbols(filepath: str, original_filename: str | None = None) -> list[dict]:
    """Extract functions, structs, and classes from C/C++ files."""
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext not in LANG_MAP:
        return []

    lang = LANG_MAP[ext]
    query_str = SYMBOL_QUERIES[ext]

    content = path.read_text(encoding="utf-8", errors="replace")
    content_bytes = content.encode()

    parser = Parser(lang)
    tree = parser.parse(content_bytes)

    query = Query(lang, query_str)
    cursor = QueryCursor(query)

    filename = original_filename or path.name

    symbols = []
    seen_nodes = set()  # Avoid duplicates from multiple capture names

    for _, captures in cursor.matches(tree.root_node):
        for capture_name, nodes in captures.items():
            if capture_name.startswith("_"):  # Skip helper captures like @_name
                continue
            for node in nodes:
                node_id = (node.start_byte, node.end_byte)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)

                symbol_name = _get_symbol_name(node, content_bytes)
                if not symbol_name:
                    continue

                symbol_text = content[node.start_byte : node.end_byte]
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1

                symbols.append(
                    {
                        "text": symbol_text,
                        "symbol_name": symbol_name,
                        "symbol_type": capture_name,  # "func", "struct", or "class"
                        "start_line": start_line,
                        "end_line": end_line,
                        "filepath": str(path),
                        "filename": filename,
                    }
                )

    return symbols


# Keep old name for compatibility
def extract_functions(
    filepath: str, original_filename: str | None = None
) -> list[dict]:
    return extract_symbols(filepath, original_filename)
