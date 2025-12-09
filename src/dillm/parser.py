from pathlib import Path

import tree_sitter_c
import tree_sitter_cpp
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser, Query, QueryCursor

PY_LANGUAGE = Language(tree_sitter_python.language())
JS_LANGUAGE = Language(tree_sitter_javascript.language())
TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
C_LANGUAGE = Language(tree_sitter_c.language())
CPP_LANGUAGE = Language(tree_sitter_cpp.language())

LANG_MAP = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".c": C_LANGUAGE,
    ".h": CPP_LANGUAGE,
    ".cpp": CPP_LANGUAGE,
    ".hpp": CPP_LANGUAGE,
    ".cc": CPP_LANGUAGE,
    ".cxx": CPP_LANGUAGE,
}

FUNC_QUERIES = {
    ".py": "(function_definition) @func",
    ".js": "[(function_declaration) @func (arrow_function) @func (method_definition) @func]",
    ".ts": "[(function_declaration) @func (arrow_function) @func (method_definition) @func]",
    ".tsx": "[(function_declaration) @func (arrow_function) @func (method_definition) @func]",
    ".jsx": "[(function_declaration) @func (arrow_function) @func (method_definition) @func]",
    ".c": "(function_definition) @func",
    ".h": "[(function_definition) @func (declaration) @func]",
    ".cpp": "(function_definition) @func",
    ".hpp": "[(function_definition) @func (declaration) @func]",
    ".cc": "(function_definition) @func",
    ".cxx": "(function_definition) @func",
}


def extract_functions(filepath: str) -> list[dict]:
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext not in LANG_MAP:
        return []

    lang = LANG_MAP[ext]
    query_str = FUNC_QUERIES[ext]

    content = path.read_text(encoding="utf-8", errors="replace")

    parser = Parser(lang)
    tree = parser.parse(content.encode())

    query = Query(lang, query_str)
    cursor = QueryCursor(query)

    functions = []
    for _, captures in cursor.matches(tree.root_node):
        for name, nodes in captures.items():
            for node in nodes:
                func_text = content[node.start_byte : node.end_byte]
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                functions.append(
                    {
                        "text": func_text,
                        "start_line": start_line,
                        "end_line": end_line,
                        "filepath": str(path),
                        "filename": path.name,
                    }
                )

    return functions
