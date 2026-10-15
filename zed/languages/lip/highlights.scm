(comment) @comment
[(string) (multiline_string)] @string
(escape_sequence) @string.escape
(invalid_escape) @error
(number) @number
(identifier) @variable
(type) @type
[("true") ("false") ("null")] @constant
["import" "as" "export"] @keyword
["fn" "flow" "return" "if" "else" "match" "for" "in" "parallel"
 "break" "continue" "with" "next" "effect" "perform" "void"] @keyword
(import_declaration kind: _ @keyword)
(import_declaration alias: (identifier) @namespace)
(function_declaration name: (identifier) @function)
(flow_declaration name: (identifier) @function)
(parentheses (punctuation) @_colon . (identifier) @type
 (#eq? @_colon ":")
 (#match? @type "^(any|bool|number|string|list|object|function)$"))
(parentheses (punctuation) @_colon . ["effect" "null"] @type
 (#eq? @_colon ":"))
[(function_declaration return_type: _ @type)
 (flow_declaration return_type: _ @type)
 (anonymous_function return_type: _ @type)]
((identifier) @function.builtin
 (#match? @function.builtin "^(claim|len|str|range|map|fold|fail|concat|slice|keys|has|put|split|parse_number)$"))
[("(") (")") ("[") ("]") ("{") ("}")] @punctuation.bracket
(punctuation) @punctuation.delimiter
(operator) @operator
["->" "?"] @operator
