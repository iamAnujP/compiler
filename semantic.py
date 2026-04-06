# ── C / C++ shared constants ──────────────────────────────────
PURE_TYPES  = {"int","char","float","double","void","long","short","unsigned","signed","bool"}
QUALIFIERS  = {"const","static","extern","auto","register","volatile","inline","mutable"}
INT_TYPES   = {"int","short","long","unsigned","signed","char","bool"}
FLOAT_TYPES = {"float","double"}

C_KEYWORDS = {
    "auto","break","case","char","const","continue","default","do","double",
    "else","enum","extern","float","for","goto","if","inline","int","long",
    "register","return","short","signed","sizeof","static","struct","switch",
    "typedef","union","unsigned","void","volatile","while"
}
CPP_KEYWORDS = C_KEYWORDS | {
    "bool","class","catch","constexpr","delete","explicit","false","friend",
    "mutable","namespace","new","noexcept","nullptr","operator","override",
    "private","protected","public","template","this","throw","true","try",
    "typename","using","virtual","final","static_cast","dynamic_cast","const_cast"
}
PYTHON_KEYWORDS = {
    "False","None","True","and","as","assert","async","await","break","class",
    "continue","def","del","elif","else","except","finally","for","from",
    "global","if","import","in","is","lambda","nonlocal","not","or","pass",
    "raise","return","try","while","with","yield"
}

C_BUILTINS = {
    "printf","scanf","malloc","free","exit","NULL","EOF","stdin","stdout",
    "stderr","sizeof","strlen","strcpy","strcat","strcmp","atoi","atof",
    "abs","pow","sqrt","rand","srand","time","fopen","fclose","fprintf",
    "fscanf","fgets","fputs","assert","memcpy","memset","memmove","main"
}
CPP_BUILTINS = C_BUILTINS | {
    "cout","cin","cerr","clog","endl","string","vector","map","set","pair",
    "list","deque","queue","stack","array","tuple","optional","variant",
    "make_pair","make_shared","make_unique","shared_ptr","unique_ptr",
    "begin","end","size","push_back","pop_back","emplace_back",
    "std","swap","sort","find","count","min","max","move","forward"
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
    "ArithmeticError","LookupError","EnvironmentError","ConnectionError"
}


def semantic_analyze(tokens, language="c"):
    if language == "python":
        return _python_semantic(tokens)
    builtins = CPP_BUILTINS if language == "cpp" else C_BUILTINS
    kw_set   = CPP_KEYWORDS  if language == "cpp" else C_KEYWORDS
    return _c_cpp_semantic(tokens, builtins, kw_set)


# ── C / C++ ──────────────────────────────────────────────────

def _c_cpp_semantic(tokens, builtins, kw_set):
    errors = []
    scope_stack = [{}]

    def current_scope(): return scope_stack[-1]
    def lookup(name):
        for s in reversed(scope_stack):
            if name in s: return s[name]
    def declare(name, entry):
        s = current_scope()
        if name in s and len(scope_stack) > 1:
            errors.append({"phase":"semantic","line":entry["line"],"column":entry["column"],
                           "message":f"Duplicate declaration of '{name}' — already declared at line {s[name]['line']}","token":name})
        else:
            s[name] = entry

    i = 0
    while i < len(tokens):
        tok  = tokens[i]
        nxt  = tokens[i+1] if i+1 < len(tokens) else None
        prev = tokens[i-1] if i > 0 else None

        if tok["value"] == "{": scope_stack.append({}); i += 1; continue
        if tok["value"] == "}":
            if len(scope_stack) > 1: scope_stack.pop()
            i += 1; continue

        is_qual  = tok["value"] in QUALIFIERS
        type_tok = tokens[i+1] if is_qual and i+1 < len(tokens) else tok
        off      = 1 if is_qual else 0

        if type_tok and type_tok["value"] in PURE_TYPES:
            name_idx = i + 1 + off
            name_tok = tokens[name_idx] if name_idx < len(tokens) else None
            if name_tok and name_tok["type"] == "IDENTIFIER":
                after_idx = i + 2 + off
                after = tokens[after_idx] if after_idx < len(tokens) else None
                if after and after["value"] == "(":
                    declare(name_tok["value"],{"name":name_tok["value"],"type":type_tok["value"],"line":name_tok["line"],"column":name_tok["column"],"kind":"function"})
                    j = i + 3 + off
                    while j < len(tokens) and tokens[j]["value"] != ")":
                        if tokens[j]["value"] in PURE_TYPES and j+1 < len(tokens) and tokens[j+1]["type"] == "IDENTIFIER":
                            declare(tokens[j+1]["value"],{"name":tokens[j+1]["value"],"type":tokens[j]["value"],"line":tokens[j+1]["line"],"column":tokens[j+1]["column"],"kind":"parameter"})
                            j += 2
                        else: j += 1
                        if j < len(tokens) and tokens[j]["value"] == ",": j += 1
                    i = j + 1; continue
                else:
                    declare(name_tok["value"],{"name":name_tok["value"],"type":type_tok["value"],"line":name_tok["line"],"column":name_tok["column"],"kind":"variable"})
            i += 1; continue

        if tok["type"] == "IDENTIFIER":
            is_decl = prev and (prev["value"] in PURE_TYPES or prev["value"] in QUALIFIERS or prev["value"] == ",")
            if not is_decl and tok["value"] not in builtins and tok["value"] not in kw_set:
                if not lookup(tok["value"]):
                    msg = (f"Call to undeclared function '{tok['value']}'" if nxt and nxt["value"] == "("
                           else f"Use of undeclared identifier '{tok['value']}'")
                    errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],"message":msg,"token":tok["value"]})

        if tok["value"] == "=":
            lhs = tokens[i-1] if i > 0 else None
            rhs = tokens[i+1] if i+1 < len(tokens) else None
            if lhs and rhs:
                entry = lookup(lhs["value"])
                if entry:
                    if entry["type"] in INT_TYPES and rhs["type"] == "FLOAT_LITERAL":
                        errors.append({"phase":"semantic","line":rhs["line"],"column":rhs["column"],
                                       "message":f"Type mismatch: assigning float '{rhs['value']}' to integer '{lhs['value']}' (data loss)","token":rhs["value"]})
                    if entry["type"] in (INT_TYPES | FLOAT_TYPES) and rhs["type"] == "STRING_LITERAL":
                        errors.append({"phase":"semantic","line":rhs["line"],"column":rhs["column"],
                                       "message":f"Type mismatch: cannot assign string to numeric variable '{lhs['value']}'","token":rhs["value"]})
        i += 1

    return errors


# ── Python ───────────────────────────────────────────────────

def _python_semantic(tokens):
    errors = []
    declared = set()

    # ── Pass 1: collect all declared names ───────────────────
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i+1] if i+1 < len(tokens) else None

        # def name( — collect function name + parameters
        if tok["value"] == "def" and nxt and nxt["type"] == "IDENTIFIER":
            declared.add(nxt["value"])
            j = i + 2
            if j < len(tokens) and tokens[j]["value"] == "(":
                j += 1
                while j < len(tokens) and tokens[j]["value"] != ")":
                    if tokens[j]["type"] == "IDENTIFIER":
                        declared.add(tokens[j]["value"])
                    j += 1

        # class Name
        elif tok["value"] == "class" and nxt and nxt["type"] == "IDENTIFIER":
            declared.add(nxt["value"])

        # import x, y  /  import x as alias
        elif tok["value"] == "import":
            j = i + 1
            while j < len(tokens) and tokens[j]["line"] == tok["line"]:
                if tokens[j]["type"] == "IDENTIFIER" and tokens[j]["value"] not in PYTHON_KEYWORDS:
                    declared.add(tokens[j]["value"])
                j += 1

        # from x import a, b
        elif tok["value"] == "from":
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] != "import": j += 1
            j += 1
            while j < len(tokens) and tokens[j]["line"] == tok["line"]:
                if tokens[j]["type"] == "IDENTIFIER":
                    declared.add(tokens[j]["value"])
                j += 1

        # name = value  (not ==)
        elif tok["type"] == "IDENTIFIER" and nxt and nxt["value"] == "=":
            after = tokens[i+2] if i+2 < len(tokens) else None
            if not after or after["value"] != "=":
                prev = tokens[i-1] if i > 0 else None
                if not prev or prev["value"] not in (".", "->", "::"):
                    declared.add(tok["value"])

        # name += / -= / etc.
        elif tok["type"] == "IDENTIFIER" and nxt and nxt["value"] in ("+=","-=","*=","/=","//=","**=","%=","&=","|=","^="):
            declared.add(tok["value"])

        # for var in ... / for x, y in ...
        elif tok["value"] == "for":
            j = i + 1
            while j < len(tokens) and tokens[j]["value"] != "in":
                if tokens[j]["type"] == "IDENTIFIER":
                    declared.add(tokens[j]["value"])
                j += 1

        # ... as var
        elif tok["value"] == "as" and nxt and nxt["type"] == "IDENTIFIER":
            declared.add(nxt["value"])

        # global / nonlocal
        elif tok["value"] in ("global","nonlocal"):
            j = i + 1
            while j < len(tokens) and tokens[j]["line"] == tok["line"]:
                if tokens[j]["type"] == "IDENTIFIER":
                    declared.add(tokens[j]["value"])
                j += 1

        i += 1

    # ── Pass 2: check usage ───────────────────────────────────
    for i, tok in enumerate(tokens):
        if tok["type"] != "IDENTIFIER": continue
        nxt  = tokens[i+1] if i+1 < len(tokens) else None
        prev = tokens[i-1] if i > 0 else None

        # Skip declaration positions
        if prev and prev["value"] in ("def","class","import","from","as","global","nonlocal","lambda",".","->"): continue
        # Skip if attribute access
        if prev and prev["value"] == ".": continue
        # Skip assignment target
        if nxt and nxt["value"] == "=":
            after = tokens[i+2] if i+2 < len(tokens) else None
            if not after or after["value"] != "=": continue
        # Skip augmented assignment
        if nxt and nxt["value"] in ("+=","-=","*=","/=","//=","**=","%=","&=","|=","^="): continue
        # Skip for-loop variable
        if prev and prev["value"] == "for": continue

        if tok["value"] not in PYTHON_BUILTINS and tok["value"] not in PYTHON_KEYWORDS and tok["value"] not in declared:
            msg = (f"Call to undeclared function '{tok['value']}'" if nxt and nxt["value"] == "("
                   else f"Use of undeclared variable '{tok['value']}'")
            errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],"message":msg,"token":tok["value"]})

    return errors