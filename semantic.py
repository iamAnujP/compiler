import re

PURE_TYPES = {"int","char","float","double","void","long","short","unsigned","signed","bool"}
QUALIFIERS = {"const","static","extern","auto","register","volatile","inline","mutable"}
INT_TYPES  = {"int","short","long","unsigned","signed","char","bool"}
FLOAT_TYPES = {"float","double"}

C_KEYWORDS = {
    "auto","break","case","char","const","continue","default","do","double",
    "else","enum","extern","float","for","goto","if","inline","int","long",
    "register","return","short","signed","sizeof","static","struct","switch",
    "typedef","union","unsigned","void","volatile","while",
}

CPP_KEYWORDS = C_KEYWORDS | {
    "bool","class","catch","constexpr","delete","explicit","false","friend",
    "mutable","namespace","new","noexcept","nullptr","operator","override",
    "private","protected","public","template","this","throw","true","try",
    "typename","using","virtual","final","static_cast","dynamic_cast","const_cast",
}

PYTHON_KEYWORDS = {
    "False","None","True","and","as","assert","async","await","break","class",
    "continue","def","del","elif","else","except","finally","for","from",
    "global","if","import","in","is","lambda","nonlocal","not","or","pass",
    "raise","return","try","while","with","yield",
}

C_BUILTINS = {
    "printf","scanf","malloc","free","exit","NULL","EOF","stdin","stdout",
    "stderr","sizeof","strlen","strcpy","strcat","strcmp","atoi","atof",
    "abs","pow","sqrt","rand","srand","time","fopen","fclose","fprintf",
    "fscanf","fgets","fputs","assert","memcpy","memset","memmove","main",
}

CPP_BUILTINS = C_BUILTINS | {
    "cout","cin","cerr","clog","endl","string","vector","map","set","pair",
    "list","deque","queue","stack","array","tuple","optional","variant",
    "make_pair","make_shared","make_unique","shared_ptr","unique_ptr",
    "begin","end","size","push_back","pop_back","emplace_back",
    "std","swap","sort","find","count","min","max","move","forward",
}

PYTHON_BUILTINS = {
    "print","input","len","range","int","float","str","list","dict","set",
    "tuple","bool","type","isinstance","issubclass","hasattr","getattr",
    "setattr","delattr","abs","max","min","sum","sorted","reversed",
    "enumerate","zip","map","filter","open","super","object","property",
    "staticmethod","classmethod","repr","bytes","bytearray","complex",
    "divmod","pow","round","hex","oct","bin","chr","ord","hash","id",
    "iter","next","all","any","callable","dir","vars","globals","locals",
    "exec","eval","compile","format","breakpoint","exit","quit","help",
    "None","True","False","NotImplemented","__name__","__file__",
    "Exception","ValueError","TypeError","AttributeError","KeyError",
    "IndexError","RuntimeError","StopIteration","FileNotFoundError",
    "PermissionError","OSError","IOError","NameError","ZeroDivisionError",
    "ImportError","ModuleNotFoundError","AssertionError","OverflowError",
    "NotImplementedError","RecursionError","MemoryError","UnicodeError",
    "ArithmeticError","LookupError","EnvironmentError",
}


def semantic_analyze(tokens, language="c"):
    if language == "python":
        return _python_semantic(tokens)
    return _c_cpp_semantic(tokens, language)


def _c_cpp_semantic(tokens, language="c"):
    errors = []
    keywords = CPP_KEYWORDS if language == "cpp" else C_KEYWORDS
    builtins = CPP_BUILTINS if language == "cpp" else C_BUILTINS

    declared = set(builtins)

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in (PURE_TYPES | QUALIFIERS):
            j = i + 1
            while j < len(tokens) and (
                (tokens[j]["type"] == "KEYWORD" and tokens[j]["value"] in (PURE_TYPES | QUALIFIERS))
                or tokens[j]["value"] == "*"
            ):
                j += 1
            if j < len(tokens) and tokens[j]["type"] == "IDENTIFIER":
                name_tok = tokens[j]
                after = tokens[j+1] if j+1 < len(tokens) else None
                declared.add(name_tok["value"])

                if after and after["value"] == "(":
                    k = j + 2
                    while k < len(tokens) and tokens[k]["value"] != ")":
                        if tokens[k]["type"] == "KEYWORD" and tokens[k]["value"] in PURE_TYPES:
                            m = k + 1
                            while m < len(tokens) and tokens[m]["value"] == "*":
                                m += 1
                            if m < len(tokens) and tokens[m]["type"] == "IDENTIFIER":
                                declared.add(tokens[m]["value"])
                        k += 1

    for i, tok in enumerate(tokens):
        if tok["type"] != "IDENTIFIER": continue
        if tok["value"] in keywords: continue
        if tok["value"] in declared: continue

        prev = tokens[i-1] if i > 0 else None
        nxt  = tokens[i+1] if i+1 < len(tokens) else None

        if nxt and nxt["value"] == "(": continue
        if prev and prev["value"] in (".", "->"): continue
        if prev and prev["value"] == "::": continue
        if nxt  and nxt["value"]  == "::": continue
        if prev and prev["value"] == "<": continue
        if nxt  and nxt["value"]  == ">": continue
        if nxt  and nxt["value"]  == "*": continue
        if re.match(r'^[A-Z_][A-Z0-9_]+$', tok["value"]): continue
        if prev and prev["value"] in ("struct","enum","union","typedef","class","namespace"): continue
        if prev and prev["value"] in ("#","include"): continue

        errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                       "message":f"'{tok['value']}' used but not declared","token":tok["value"]})
        declared.add(tok["value"])

    var_values = {}
    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in PURE_TYPES:
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] == "*":
                j += 1
            if j < len(tokens) and tokens[j]["type"] == "IDENTIFIER":
                var_name = tokens[j]["value"]
                after = tokens[j+1] if j+1 < len(tokens) else None
                if after and after["value"] == "=":
                    val_tok = tokens[j+2] if j+2 < len(tokens) else None
                    if val_tok and val_tok["type"] == "INTEGER_LITERAL":
                        var_values[var_name] = int(val_tok["value"])

    for i, tok in enumerate(tokens):
        if tok["type"] == "OPERATOR" and tok["value"] in ("/", "%"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt:
                if nxt["type"] == "INTEGER_LITERAL" and nxt["value"] == "0":
                    errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                                   "message":"Division by zero","token":tok["value"]})
                elif nxt["type"] == "IDENTIFIER" and var_values.get(nxt["value"]) == 0:
                    errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                                   "message":f"Division by zero: variable '{nxt['value']}' is 0",
                                   "token":tok["value"]})

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] == "void":
            nxt   = tokens[i+1] if i+1 < len(tokens) else None
            after = tokens[i+2] if i+2 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER" and after and after["value"] in (";","="):
                errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                               "message":f"Cannot declare variable '{nxt['value']}' of type 'void'",
                               "token":"void"})

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in ("if", "while", "for"):
            j = i + 1
            if j < len(tokens) and tokens[j]["value"] == "(":
                depth = 1
                j += 1
                while j < len(tokens) and depth > 0:
                    if tokens[j]["value"] == "(":
                        depth += 1
                    elif tokens[j]["value"] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    if tokens[j]["value"] == "=":
                        prev_val = tokens[j-1]["value"] if j > 0 else ""
                        next_val = tokens[j+1]["value"] if j+1 < len(tokens) else ""
                        if prev_val not in ("!", "<", ">", "=", "+", "-", "*", "/", "%", "&", "|", "^") \
                                and next_val != "=":
                            errors.append({
                                "phase": "semantic",
                                "line": tokens[j]["line"],
                                "column": tokens[j]["column"],
                                "message": f"Assignment '=' used inside '{tok['value']}' condition; did you mean '=='?",
                                "token": "="
                            })
                    j += 1

    initialized = set(builtins)
    uninitialized = set()

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in PURE_TYPES:
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] == "*":
                j += 1
            if j < len(tokens) and tokens[j]["type"] == "IDENTIFIER":
                var_name = tokens[j]["value"]
                after = tokens[j+1] if j+1 < len(tokens) else None
                if after and after["value"] in ("=", "["):
                    initialized.add(var_name)
                elif after and after["value"] in (";", ","):
                    uninitialized.add(var_name)

    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER" and tok["value"] in uninitialized:
            prev = tokens[i-1] if i > 0 else None
            nxt  = tokens[i+1] if i+1 < len(tokens) else None
            if prev and prev["value"] in PURE_TYPES:
                continue
            if nxt and nxt["value"] == "=":
                after = tokens[i+2] if i+2 < len(tokens) else None
                if after and after["value"] != "=":
                    initialized.add(tok["value"])
                    uninitialized.discard(tok["value"])
                    continue
            if tok["value"] not in initialized:
                errors.append({
                    "phase": "semantic",
                    "line": tok["line"],
                    "column": tok["column"],
                    "message": f"Variable '{tok['value']}' may be used uninitialized",
                    "token": tok["value"]
                })
                initialized.add(tok["value"])

    array_sizes = {}
    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in PURE_TYPES:
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] == "*":
                j += 1
            if j < len(tokens) and tokens[j]["type"] == "IDENTIFIER":
                arr_name = tokens[j]["value"]
                after = tokens[j+1] if j+1 < len(tokens) else None
                if after and after["value"] == "[":
                    size_tok = tokens[j+2] if j+2 < len(tokens) else None
                    close    = tokens[j+3] if j+3 < len(tokens) else None
                    if size_tok and size_tok["type"] == "INTEGER_LITERAL" and close and close["value"] == "]":
                        array_sizes[arr_name] = int(size_tok["value"])

    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER" and tok["value"] in array_sizes:
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["value"] == "[":
                idx_tok = tokens[i+2] if i+2 < len(tokens) else None
                close   = tokens[i+3] if i+3 < len(tokens) else None
                if idx_tok and idx_tok["type"] == "INTEGER_LITERAL" and close and close["value"] == "]":
                    idx = int(idx_tok["value"])
                    size = array_sizes[tok["value"]]
                    if idx >= size:
                        errors.append({
                            "phase": "semantic",
                            "line": tok["line"],
                            "column": tok["column"],
                            "message": f"Array '{tok['value']}' index {idx} is out of bounds (size {size})",
                            "token": tok["value"]
                        })

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] == "while":
            j = i + 1
            if j >= len(tokens) or tokens[j]["value"] != "(":
                continue
            j += 1
            cond_vars = set()
            while j < len(tokens) and tokens[j]["value"] != ")":
                if tokens[j]["type"] == "IDENTIFIER":
                    cond_vars.add(tokens[j]["value"])
                j += 1
            if j >= len(tokens):
                continue
            j += 1
            if j >= len(tokens) or tokens[j]["value"] != "{":
                continue
            body_start = j + 1
            depth = 1
            j += 1
            while j < len(tokens) and depth > 0:
                if tokens[j]["value"] == "{":
                    depth += 1
                elif tokens[j]["value"] == "}":
                    depth -= 1
                j += 1
            body_end = j
            body_tokens = tokens[body_start:body_end - 1]

            modified = False
            for k, bt in enumerate(body_tokens):
                if bt["type"] == "IDENTIFIER" and bt["value"] in cond_vars:
                    nxt_bt  = body_tokens[k+1] if k+1 < len(body_tokens) else None
                    prev_bt = body_tokens[k-1] if k > 0 else None
                    if nxt_bt and nxt_bt["value"] in ("++", "--", "+=", "-=", "*=", "/=", "="):
                        if nxt_bt["value"] == "=":
                            after_bt = body_tokens[k+2] if k+2 < len(body_tokens) else None
                            if after_bt and after_bt["value"] == "=":
                                continue
                        modified = True
                        break
                    if prev_bt and prev_bt["value"] in ("++", "--"):
                        modified = True
                        break

            if not modified and cond_vars:
                errors.append({
                    "phase": "semantic",
                    "line": tok["line"],
                    "column": tok["column"],
                    "message": f"Possible infinite loop: variable(s) {sorted(cond_vars)} in while condition are never modified in loop body",
                    "token": "while"
                })

    return errors


def _python_semantic(tokens):
    errors = []
    scope = set(PYTHON_BUILTINS)

    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER":
            nxt   = tokens[i+1] if i+1 < len(tokens) else None
            after = tokens[i+2] if i+2 < len(tokens) else None
            if nxt and nxt["type"] == "OPERATOR" and nxt["value"] == "=":
                if not after or after["value"] != "=":
                    scope.add(tok["value"])

        if tok["value"] == "def":
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER":
                scope.add(nxt["value"])
                k = i + 2
                if k < len(tokens) and tokens[k]["value"] == "(":
                    k += 1
                    while k < len(tokens) and tokens[k]["value"] != ")":
                        if tokens[k]["type"] == "IDENTIFIER":
                            scope.add(tokens[k]["value"])
                        k += 1

        if tok["value"] == "class":
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER":
                scope.add(nxt["value"])

        if tok["value"] == "import":
            k = i + 1
            while k < len(tokens) and tokens[k]["type"] == "IDENTIFIER":
                scope.add(tokens[k]["value"])
                k += 1
                if k < len(tokens) and tokens[k]["value"] == ",": k += 1
                else: break

        if tok["value"] == "from":
            k = i + 1
            while k < len(tokens) and tokens[k]["type"] == "IDENTIFIER": k += 1
            if k < len(tokens) and tokens[k]["value"] == "import":
                k += 1
                while k < len(tokens) and tokens[k]["type"] == "IDENTIFIER":
                    scope.add(tokens[k]["value"])
                    k += 1
                    if k < len(tokens) and tokens[k]["value"] == ",": k += 1
                    else: break

        if tok["value"] == "for":
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER":
                scope.add(nxt["value"])

        if tok["value"] == "as":
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER":
                scope.add(nxt["value"])

    for i, tok in enumerate(tokens):
        if tok["type"] != "IDENTIFIER": continue
        if tok["value"] in PYTHON_KEYWORDS or tok["value"] in PYTHON_BUILTINS: continue
        if tok["value"] in scope: continue

        prev = tokens[i-1] if i > 0 else None
        nxt  = tokens[i+1] if i+1 < len(tokens) else None

        if prev and prev["value"] == ".": continue
        if nxt  and nxt["value"]  == ".": continue
        if prev and prev["value"] == "@": continue
        if nxt  and nxt["value"]  == "=":
            after = tokens[i+2] if i+2 < len(tokens) else None
            if after and after["value"] != "=": continue
        if prev and prev["value"] in ("import","from"): continue
        if prev and prev["value"] == ":": continue
        if tok["value"] in ("self","cls"): continue
        if re.match(r'^[A-Z_][A-Z0-9_]*$', tok["value"]): continue

        errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                       "message":f"'{tok['value']}' used but not defined","token":tok["value"]})
        scope.add(tok["value"])

    py_var_values = {}
    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER":
            nxt     = tokens[i+1] if i+1 < len(tokens) else None
            val_tok = tokens[i+2] if i+2 < len(tokens) else None
            if nxt and nxt["value"] == "=" and val_tok and val_tok["type"] == "INTEGER_LITERAL":
                after_val = tokens[i+3] if i+3 < len(tokens) else None
                if not after_val or after_val["value"] != "=":
                    py_var_values[tok["value"]] = int(val_tok["value"])

    for i, tok in enumerate(tokens):
        if tok["type"] == "OPERATOR" and tok["value"] in ("/", "%", "//"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt:
                if nxt["type"] == "INTEGER_LITERAL" and nxt["value"] == "0":
                    errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                                   "message":"Division by zero","token":tok["value"]})
                elif nxt["type"] == "IDENTIFIER" and py_var_values.get(nxt["value"]) == 0:
                    errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                                   "message":f"Division by zero: variable '{nxt['value']}' is 0",
                                   "token":tok["value"]})

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] in ("if", "elif", "while"):
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] != ":":
                if tokens[j]["value"] == "=":
                    prev_val = tokens[j-1]["value"] if j > 0 else ""
                    next_val = tokens[j+1]["value"] if j+1 < len(tokens) else ""
                    if prev_val not in ("!", "<", ">", "=", "+", "-", "*", "/", "%") \
                            and next_val != "=":
                        errors.append({
                            "phase": "semantic",
                            "line": tokens[j]["line"],
                            "column": tokens[j]["column"],
                            "message": f"Assignment '=' used inside '{tok['value']}' condition; did you mean '=='?",
                            "token": "="
                        })
                j += 1

    list_sizes = {}
    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER":
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["value"] == "=":
                bracket = tokens[i+2] if i+2 < len(tokens) else None
                if bracket and bracket["value"] == "[":
                    k2 = i + 3
                    depth2 = 1
                    elem_count = 0
                    prev_was_elem = False
                    while k2 < len(tokens) and depth2 > 0:
                        v = tokens[k2]["value"]
                        if v == "[": depth2 += 1
                        elif v == "]":
                            depth2 -= 1
                            if depth2 == 0: break
                        elif depth2 == 1:
                            if v == ",":
                                prev_was_elem = False
                            elif not prev_was_elem:
                                elem_count += 1
                                prev_was_elem = True
                        k2 += 1
                    if elem_count > 0:
                        list_sizes[tok["value"]] = elem_count

    for i, tok in enumerate(tokens):
        if tok["type"] == "IDENTIFIER" and tok["value"] in list_sizes:
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["value"] == "[":
                idx_tok = tokens[i+2] if i+2 < len(tokens) else None
                close   = tokens[i+3] if i+3 < len(tokens) else None
                if idx_tok and idx_tok["type"] == "INTEGER_LITERAL" and close and close["value"] == "]":
                    idx  = int(idx_tok["value"])
                    size = list_sizes[tok["value"]]
                    if idx >= size or idx < -size:
                        errors.append({
                            "phase": "semantic",
                            "line": tok["line"],
                            "column": tok["column"],
                            "message": f"List '{tok['value']}' index {idx} is out of bounds (length {size})",
                            "token": tok["value"]
                        })

    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] == "while":
            while_col  = tok["column"]
            while_line = tok["line"]
            j = i + 1
            cond_vars = set()
            while j < len(tokens) and tokens[j]["value"] != ":":
                if tokens[j]["type"] == "IDENTIFIER":
                    cond_vars.add(tokens[j]["value"])
                j += 1
            if j >= len(tokens):
                continue
            body_tokens = []
            k = j + 1
            while k < len(tokens):
                bt = tokens[k]
                if bt["line"] > while_line and bt["column"] > while_col:
                    body_tokens.append(bt)
                elif bt["line"] > while_line and bt["column"] <= while_col:
                    break
                k += 1

            if not body_tokens:
                continue

            modified = False
            for k2, bt in enumerate(body_tokens):
                if bt["type"] == "IDENTIFIER" and bt["value"] in cond_vars:
                    nxt_bt  = body_tokens[k2+1] if k2+1 < len(body_tokens) else None
                    prev_bt = body_tokens[k2-1] if k2 > 0 else None
                    if nxt_bt and nxt_bt["value"] in ("=", "+=", "-=", "*=", "/=", "//=", "%=", "**="):
                        if nxt_bt["value"] == "=":
                            after_bt = body_tokens[k2+2] if k2+2 < len(body_tokens) else None
                            if after_bt and after_bt["value"] == "=":
                                continue
                        modified = True
                        break
                    if prev_bt and prev_bt["value"] in ("++", "--"):
                        modified = True
                        break

            if not modified and cond_vars:
                errors.append({
                    "phase": "semantic",
                    "line": tok["line"],
                    "column": tok["column"],
                    "message": f"Possible infinite loop: variable(s) {sorted(cond_vars)} in while condition are never modified in loop body",
                    "token": "while"
                })

    return errors
