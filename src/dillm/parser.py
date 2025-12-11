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

# Queries capture both the symbol node and its name directly
C_QUERY = """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @func

(struct_specifier
  name: (type_identifier) @name
  body: (_)) @struct
"""

CPP_QUERY = """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @func

(function_definition
  declarator: (function_declarator
    declarator: (field_identifier) @name)) @func

(function_definition
  declarator: (function_declarator
    declarator: (qualified_identifier
      name: (identifier) @name))) @func

(struct_specifier
  name: (type_identifier) @name
  body: (_)) @struct

(class_specifier
  name: (type_identifier) @name
  body: (_)) @class
"""

SYMBOL_QUERIES = {
    ".c": C_QUERY,
    ".h": CPP_QUERY,
    ".cpp": CPP_QUERY,
    ".hpp": CPP_QUERY,
    ".cc": CPP_QUERY,
    ".cxx": CPP_QUERY,
}


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
    seen_nodes = set()

    for _, captures in cursor.matches(tree.root_node):
        # Each match has @name and one of @func/@struct/@class
        name_node = None
        symbol_node = None
        symbol_type = None

        for capture_name, nodes in captures.items():
            for node in nodes:
                if capture_name == "name":
                    name_node = node
                else:
                    symbol_node = node
                    symbol_type = capture_name

        if not name_node or not symbol_node:
            continue

        node_id = (symbol_node.start_byte, symbol_node.end_byte)
        if node_id in seen_nodes:
            continue
        seen_nodes.add(node_id)

        symbol_name = content_bytes[name_node.start_byte:name_node.end_byte].decode()
        symbol_text = content_bytes[symbol_node.start_byte:symbol_node.end_byte].decode()
        start_line = symbol_node.start_point[0] + 1
        end_line = symbol_node.end_point[0] + 1

        symbols.append({
            "text": symbol_text,
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "start_line": start_line,
            "end_line": end_line,
            "filepath": str(path),
            "filename": filename,
        })

    return symbols


# Keep old name for compatibility
extract_functions = extract_symbols
