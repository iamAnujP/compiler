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
        import re
        if re.match(r'^[A-Z_][A-Z0-9_]+$', tok["value"]): continue  
        if prev and prev["value"] in ("struct","enum","union","typedef","class","namespace"): continue
        if prev and prev["value"] in ("#","include"): continue

        errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                       "message":f"'{tok['value']}' used but not declared","token":tok["value"]})
        declared.add(tok["value"])  

    for i, tok in enumerate(tokens):
        if tok["type"] == "OPERATOR" and tok["value"] in ("/","%"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "INTEGER_LITERAL" and nxt["value"] == "0":
                errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                               "message":"Division by zero","token":tok["value"]})

    
    for i, tok in enumerate(tokens):
        if tok["type"] == "KEYWORD" and tok["value"] == "void":
            nxt   = tokens[i+1] if i+1 < len(tokens) else None
            after = tokens[i+2] if i+2 < len(tokens) else None
            if nxt and nxt["type"] == "IDENTIFIER" and after and after["value"] in (";","="):
                errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                               "message":f"Cannot declare variable '{nxt['value']}' of type 'void'",
                               "token":"void"})

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
        import re
        if re.match(r'^[A-Z_][A-Z0-9_]*$', tok["value"]): continue  

        errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                       "message":f"'{tok['value']}' used but not defined","token":tok["value"]})
        scope.add(tok["value"])

    for i, tok in enumerate(tokens):
        if tok["type"] == "OPERATOR" and tok["value"] in ("/","%","//"):
            nxt = tokens[i+1] if i+1 < len(tokens) else None
            if nxt and nxt["type"] == "INTEGER_LITERAL" and nxt["value"] == "0":
                errors.append({"phase":"semantic","line":tok["line"],"column":tok["column"],
                               "message":"Division by zero","token":tok["value"]})

    return errors
