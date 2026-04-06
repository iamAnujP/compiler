C_KEYWORDS = {
    "auto","break","case","char","const","continue","default","do","double",
    "else","enum","extern","float","for","goto","if","inline","int","long",
    "register","return","short","signed","sizeof","static","struct","switch",
    "typedef","union","unsigned","void","volatile","while"
}
CPP_KEYWORDS = C_KEYWORDS | {
    "bool","class","catch","constexpr","delete","explicit","export","false",
    "friend","mutable","namespace","new","noexcept","nullptr","operator",
    "override","private","protected","public","template","this","throw","true",
    "try","typename","using","virtual","final","static_cast","dynamic_cast",
    "const_cast","reinterpret_cast"
}
PYTHON_KEYWORDS = {
    "False","None","True","and","as","assert","async","await","break","class",
    "continue","def","del","elif","else","except","finally","for","from",
    "global","if","import","in","is","lambda","nonlocal","not","or","pass",
    "raise","return","try","while","with","yield"
}

C_TWO_OPS     = {"++","--","+=","-=","*=","/=","%=","==","!=","<=",">=","&&","||","<<",">>","->"}
CPP_TWO_OPS   = C_TWO_OPS | {"::"}
PYTHON_TWO_OPS= {"**","//","==","!=","<=",">=","+=","-=","*=","/=","//=","**=","%=","->",":=","<<",">>","&=","|=","^="}

C_ONE_OPS     = set("+-*/%=<>!&|^~.")
PYTHON_ONE_OPS= set("+-*/%=<>!&|^~.@")


def _get_config(language):
    if language == "cpp":
        return CPP_KEYWORDS, CPP_TWO_OPS, C_ONE_OPS
    elif language == "python":
        return PYTHON_KEYWORDS, PYTHON_TWO_OPS, PYTHON_ONE_OPS
    return C_KEYWORDS, C_TWO_OPS, C_ONE_OPS


def lexical_analyze(code, language="c"):
    keywords, two_ops, one_ops = _get_config(language)
    tokens, errors = [], []
    i, line, line_start = 0, 1, 0

    while i < len(code):
        col = i - line_start + 1
        ch  = code[i]

        if ch == "\n":
            line += 1; line_start = i + 1; i += 1; continue
        if ch.isspace():
            i += 1; continue

        # ── Comments ──────────────────────────────────────────
        if language == "python" and ch == "#":
            while i < len(code) and code[i] != "\n": i += 1
            continue

        if language in ("c","cpp") and code[i:i+2] == "//":
            while i < len(code) and code[i] != "\n": i += 1
            continue

        if language in ("c","cpp") and code[i:i+2] == "/*":
            i += 2
            while i < len(code)-1 and code[i:i+2] != "*/":
                if code[i] == "\n": line += 1; line_start = i + 1
                i += 1
            if code[i:i+2] == "*/": i += 2
            else: errors.append({"phase":"lexical","line":line,"column":col,"message":"Unterminated block comment","token":"/*"})
            continue

        # ── Python triple-quoted strings ─────────────────────
        if language == "python" and code[i:i+3] in ('"""', "'''"):
            q3 = code[i:i+3]; s = q3; i += 3; closed = False
            while i < len(code):
                if code[i:i+3] == q3: s += q3; i += 3; closed = True; break
                if code[i] == "\n": line += 1; line_start = i + 1
                s += code[i]; i += 1
            if not closed: errors.append({"phase":"lexical","line":line,"column":col,"message":"Unterminated triple-quoted string","token":q3})
            else: tokens.append({"type":"STRING_LITERAL","value":s,"line":line,"column":col})
            continue

        # ── Identifiers / keywords ────────────────────────────
        if ch.isalpha() or ch == "_":
            ident = ""
            while i < len(code) and (code[i].isalnum() or code[i] == "_"): ident += code[i]; i += 1

            # Python string prefixes: f"", b"", r"", etc.
            if language == "python" and ident.lower() in ("f","b","r","rb","br","fr","rf","u") and i < len(code) and code[i] in ('"',"'"):
                quote = code[i]; s = ident + quote; i += 1; closed = False
                while i < len(code):
                    if code[i] == "\\": s += code[i]+(code[i+1] if i+1<len(code) else ""); i += 2; continue
                    if code[i] == quote: s += quote; i += 1; closed = True; break
                    if code[i] == "\n": break
                    s += code[i]; i += 1
                if not closed: errors.append({"phase":"lexical","line":line,"column":col,"message":"Unterminated string literal","token":s})
                else: tokens.append({"type":"STRING_LITERAL","value":s,"line":line,"column":col})
                continue

            tok_type = "KEYWORD" if ident in keywords else "IDENTIFIER"
            tokens.append({"type":tok_type,"value":ident,"line":line,"column":col})
            continue

        # ── Double-quoted string ──────────────────────────────
        if ch == '"':
            s = '"'; i += 1; closed = False
            while i < len(code):
                if code[i] == "\\": s += code[i]+(code[i+1] if i+1<len(code) else ""); i += 2; continue
                if code[i] == '"': s += '"'; i += 1; closed = True; break
                if code[i] == "\n": break
                s += code[i]; i += 1
            if not closed: errors.append({"phase":"lexical","line":line,"column":col,"message":"Unterminated string literal","token":s})
            else: tokens.append({"type":"STRING_LITERAL","value":s,"line":line,"column":col})
            continue

        # ── Single-quoted ─────────────────────────────────────
        if ch == "'":
            tok_type = "CHAR_LITERAL" if language in ("c","cpp") else "STRING_LITERAL"
            s = "'"; i += 1; closed = False
            while i < len(code):
                if code[i] == "\\": s += code[i]+(code[i+1] if i+1<len(code) else ""); i += 2; continue
                if code[i] == "'": s += "'"; i += 1; closed = True; break
                if code[i] == "\n": break
                s += code[i]; i += 1
            if not closed: errors.append({"phase":"lexical","line":line,"column":col,"message":"Unterminated character/string literal","token":s})
            else: tokens.append({"type":tok_type,"value":s,"line":line,"column":col})
            continue

        # ── Number literal ────────────────────────────────────
        if ch.isdigit() or (ch == "." and i+1 < len(code) and code[i+1].isdigit()):
            num = ""; is_float = False
            while i < len(code) and (code[i].isdigit() or code[i] in "._xXabcdefABCDEF"):
                if code[i] == ".": is_float = True
                num += code[i]; i += 1
            if i < len(code) and code[i] in "fF" and language in ("c","cpp"): num += code[i]; i += 1; is_float = True
            if i < len(code) and code[i] in "jJ" and language == "python":     num += code[i]; i += 1
            tokens.append({"type":"FLOAT_LITERAL" if is_float else "INTEGER_LITERAL","value":num,"line":line,"column":col})
            continue

        # ── Two-char operators ────────────────────────────────
        two = code[i:i+2]
        if two in two_ops: tokens.append({"type":"OPERATOR","value":two,"line":line,"column":col}); i += 2; continue

        # ── One-char operators ────────────────────────────────
        if ch in one_ops: tokens.append({"type":"OPERATOR","value":ch,"line":line,"column":col}); i += 1; continue

        # ── Punctuation ───────────────────────────────────────
        c_punct = "{}()[];,#"
        py_punct = "{}()[];,:"
        if (language in ("c","cpp") and ch in c_punct) or (language == "python" and ch in py_punct):
            tokens.append({"type":"PUNCTUATION","value":ch,"line":line,"column":col}); i += 1; continue

        errors.append({"phase":"lexical","line":line,"column":col,"message":f"Unrecognized character '{ch}'","token":ch})
        i += 1

    return tokens, errors