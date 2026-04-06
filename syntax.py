from collections import defaultdict

C_TYPES = {
    "int","char","float","double","void","long","short",
    "unsigned","signed","const","static","extern","auto","bool"
}
PYTHON_BLOCK_KW = {
    "if","elif","else","for","while","def","class","with","try","except","finally"
}

def syntax_analyze(tokens, language="c"):
    if language == "python":
        return _python_syntax(tokens)
    return _c_cpp_syntax(tokens)


# ── C / C++ ──────────────────────────────────────────────────

def _c_cpp_syntax(tokens):
    errors = []
    braces, parens, brackets = [], [], []

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

    # Unclosed braces, parens, and brackets
    for b  in braces:    errors.append({"phase":"syntax","line":b["line"],"column":b["column"],"message":"Unclosed brace '{' — missing corresponding '}'","token":"{"})
    for p  in parens:    errors.append({"phase":"syntax","line":p["line"],"column":p["column"],"message":"Unclosed parenthesis '(' — missing corresponding ')'","token":"("})
    for br in brackets:  errors.append({"phase":"syntax","line":br["line"],"column":br["column"],"message":"Unclosed bracket '[' — missing corresponding ']'","token":"["})

    for i, tok in enumerate(tokens):
        nxt  = tokens[i+1] if i+1 < len(tokens) else None
        prev = tokens[i-1] if i > 0 else None

        # Check for if/while/for requiring '(' after
        if tok["value"] in ("if","while","for") and (not nxt or nxt["value"] != "("):
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],"message":f"'{tok['value']}' must be followed by '('","token":tok["value"]})

        # Ensure return is followed by a semicolon
        if tok["value"] == "return":
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] not in ("{", "}"):
                if tokens[j]["value"] == ";":
                    break
                j += 1
            if j >= len(tokens) or tokens[j]["value"] != ";":
                errors.append({"phase":"syntax", "line":tok["line"], "column":tok["column"],
                               "message":"Missing semicolon after 'return'","token":"return"})

        # Check for missing semicolons after variable declarations or expressions in C/C++
        if tok["type"] in ("IDENTIFIER","INTEGER_LITERAL","FLOAT_LITERAL") and \
           nxt and nxt["value"] in C_TYPES and tok["line"] < nxt["line"] and \
           (not prev or prev["value"] not in (")", "{", "}", ";", ",")):
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"]+len(tok["value"]),
                           "message":f"Missing semicolon after '{tok['value']}'","token":tok["value"]})

    return errors


# ── Python ───────────────────────────────────────────────────

def _python_syntax(tokens):
    errors = []
    braces, parens, brackets = [], [], []

    # Track open/close braces, parens, and brackets
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

    # Unclosed braces, parens, and brackets
    for b  in braces:   errors.append({"phase":"syntax","line":b["line"],"column":b["column"],"message":"Unclosed brace '{' — missing corresponding '}'","token":"{"})
    for p  in parens:   errors.append({"phase":"syntax","line":p["line"],"column":p["column"],"message":"Unclosed parenthesis '(' — missing corresponding ')'","token":"("})
    for br in brackets: errors.append({"phase":"syntax","line":br["line"],"column":br["column"],"message":"Unclosed bracket '[' — missing corresponding ']'","token":"["})

    # Group tokens by line
    line_tokens = defaultdict(list)
    for tok in tokens:
        line_tokens[tok["line"]].append(tok)

    # Block keywords must end with ':', check for missing ':'
    for i, tok in enumerate(tokens):
        if tok["type"] != "KEYWORD" or tok["value"] not in PYTHON_BLOCK_KW:
            continue
        toks_on_line = line_tokens[tok["line"]]
        if not toks_on_line or toks_on_line[0] is not tok:
            continue
        if not any(t["value"] == ":" for t in toks_on_line):
            errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                           "message":f"'{tok['value']}' block header must end with ':'","token":tok["value"]})

    # def / class must be followed by an identifier
    for i, tok in enumerate(tokens):
        if tok["value"] in ("def","class"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if not nxt or nxt["type"] != "IDENTIFIER":
                errors.append({"phase":"syntax","line":tok["line"],"column":tok["column"],
                               "message":f"'{tok['value']}' must be followed by a name","token":tok["value"]})

    # Check for 'elif' not following 'if' and other conditional block errors
    for i, tok in enumerate(tokens):
        if tok["value"] == "elif":
            prev_tok = tokens[i-1] if i > 0 else None
            if prev_tok and prev_tok["value"] != "if":
                errors.append({"phase":"syntax", "line":tok["line"], "column":tok["column"],
                               "message":"'elif' should be preceded by 'if'","token":"elif"})

    return errors