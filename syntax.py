from collections import defaultdict

C_TYPES = {
    "int","char","float","double","void","long","short",
    "unsigned","signed","const","static","extern","auto","bool"
}

COMPOUND_KW = {
    "if","else","while","for","do","switch","case","default",
    "struct","class","namespace","try","catch","public","private","protected"
}

PYTHON_BLOCK_KW = {
    "if","elif","else","for","while","def","class","with","try","except","finally"
}

INVALID_C_PUNCT = {"@", "$", "`", "?"}


def syntax_analyze(tokens, language="c"):
    if language == "python":
        return _python_syntax(tokens)
    return _c_cpp_syntax(tokens, language)


# ── C / C++ ──────────────────────────────────────────────────

def _c_cpp_syntax(tokens, language="c"):
    errors = []
    braces, parens, brackets = [], [], []

    # ── Bracket matching ──
    for tok in tokens:
        if tok["type"] != "PUNCTUATION": continue
        if   tok["value"] == "{": braces.append(tok)
        elif tok["value"] == "}":
            if not braces: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected '}' — no matching '{'","token":"}"})
            else: braces.pop()
        if   tok["value"] == "(": parens.append(tok)
        elif tok["value"] == ")":
            if not parens: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected ')' — no matching '('","token":")"})
            else: parens.pop()
        if   tok["value"] == "[": brackets.append(tok)
        elif tok["value"] == "]":
            if not brackets: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected ']' — no matching '['","token":"]"})
            else: brackets.pop()

    for b  in braces:   errors.append({"phase":"syntax","line":b["line"],"column":b["column"],"message":"Unclosed brace '{' — missing corresponding '}'","token":"{"})
    for p  in parens:   errors.append({"phase":"syntax","line":p["line"],"column":p["column"],"message":"Unclosed parenthesis '(' — missing corresponding ')'","token":"("})
    for br in brackets: errors.append({"phase":"syntax","line":br["line"],"column":br["column"],"message":"Unclosed bracket '[' — missing corresponding ']'","token":"["})

    # ── Invalid characters for C/C++ (@ $ ` ?) ──
    for tok in tokens:
        if tok["type"] == "PUNCTUATION" and tok["value"] in INVALID_C_PUNCT:
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                           "message":f"Invalid character '{tok['value']}' in {language.upper()} code",
                           "token":tok["value"]})

    # ── if / while / for must be followed by ( ──
    for i, tok in enumerate(tokens):
        nxt = tokens[i+1] if i+1 < len(tokens) else None
        if tok["value"] in ("if","while","for") and tok["type"] == "KEYWORD":
            if not nxt or nxt["value"] != "(":
                errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                               "message":f"'{tok['value']}' must be followed by '('",
                               "token":tok["value"]})

    # ── Missing semicolons — per-line analysis ──
    line_tokens = defaultdict(list)
    for tok in tokens:
        line_tokens[tok["line"]].append(tok)

    sorted_lines = sorted(line_tokens.keys())

    STMT_END_TYPES  = {"IDENTIFIER","INTEGER_LITERAL","FLOAT_LITERAL","STRING_LITERAL","CHAR_LITERAL"}
    STMT_END_PUNCTS = {")", "]"}
    NO_SEMI_ENDS    = {"{", "}", ";", ",", ":", "#", "\\"}

    for li, line_num in enumerate(sorted_lines):
        line_toks = line_tokens[line_num]
        first_tok = line_toks[0]
        last_tok  = line_toks[-1]

        # Skip preprocessor lines
        if first_tok["value"] == "#":
            continue

        # Skip compound statement header lines (if/else/while/for/struct/class/…)
        if first_tok["type"] == "KEYWORD" and first_tok["value"] in COMPOUND_KW:
            continue

        # Skip lines that already end with a proper terminator
        if last_tok["value"] in NO_SEMI_ENDS:
            continue

        # Function definition: line ends with ) and contains ( — not a statement
        if last_tok["value"] == ")" and any(t["value"] == "(" for t in line_toks):
            continue

        # Line ends with an expression → must have a semicolon
        if last_tok["type"] in STMT_END_TYPES or last_tok["value"] in STMT_END_PUNCTS:
            if li + 1 >= len(sorted_lines):
                continue
            errors.append({"phase":"syntax",
                           "line":line_num,
                           "column":last_tok["column"] + len(last_tok["value"]),
                           "message":f"Missing semicolon after '{last_tok['value']}'",
                           "token":last_tok["value"]})

    return errors


# ── Python ───────────────────────────────────────────────────

def _python_syntax(tokens):
    errors = []
    braces, parens, brackets = [], [], []

    # ── Bracket matching ──
    for tok in tokens:
        if tok["type"] != "PUNCTUATION": continue
        if   tok["value"] == "(": parens.append(tok)
        elif tok["value"] == ")":
            if not parens: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected ')' — no matching '('","token":")"})
            else: parens.pop()
        if   tok["value"] == "[": brackets.append(tok)
        elif tok["value"] == "]":
            if not brackets: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected ']' — no matching '['","token":"]"})
            else: brackets.pop()
        if   tok["value"] == "{": braces.append(tok)
        elif tok["value"] == "}":
            if not braces: errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":"Unexpected '}' — no matching '{'","token":"}"})
            else: braces.pop()

    for p  in parens:   errors.append({"phase":"syntax","line":p["line"],"column":p["column"],"message":"Unclosed parenthesis '(' — missing corresponding ')'","token":"("})
    for br in brackets: errors.append({"phase":"syntax","line":br["line"],"column":br["column"],"message":"Unclosed bracket '[' — missing corresponding ']'","token":"["})
    for b  in braces:   errors.append({"phase":"syntax","line":b["line"],"column":b["column"],"message":"Unclosed brace '{' — missing corresponding '}'","token":"{"})

    # ── Group tokens by line ──
    line_tokens = defaultdict(list)
    for tok in tokens:
        line_tokens[tok["line"]].append(tok)

    # ── Block keywords must end with ':' ──
    for i, tok in enumerate(tokens):
        if tok["type"] != "KEYWORD" or tok["value"] not in PYTHON_BLOCK_KW:
            continue
        toks_on_line = line_tokens[tok["line"]]
        if not toks_on_line or toks_on_line[0] is not tok:
            continue
        if not any(t["value"] == ":" for t in toks_on_line):
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                           "message":f"'{tok['value']}' block header must end with ':'",
                           "token":tok["value"]})

    # ── def / class must be followed by an identifier ──
    for i, tok in enumerate(tokens):
        if tok["value"] in ("def","class"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if not nxt or nxt["type"] != "IDENTIFIER":
                errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                               "message":f"'{tok['value']}' must be followed by a name",
                               "token":tok["value"]})

    # ── elif / else without a preceding if ──
    saw_if = False
    for tok in tokens:
        if tok["value"] == "if":
            saw_if = True
            continue
        if tok["value"] in ("elif","else") and not saw_if:
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                           "message":f"'{tok['value']}' without a preceding 'if'",
                           "token":tok["value"]})

    return errors
