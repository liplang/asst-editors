if exists('b:current_syntax')
  finish
endif
syntax case match
syntax keyword lipKeyword import as flow fn return if else match for in parallel break continue with next effect perform export void
syntax keyword lipConstant true false null
syntax keyword lipBuiltin claim len str range map fold fail concat slice keys has put split parse_number
syntax match lipType /\%(:\|->\)\s*\zs\%(any\|bool\|number\|string\|list\|object\|function\|effect\|void\|null\)\>\%(?\)\?/
syntax match lipFunction /\<\%(fn\|flow\)\s\+\zs[A-Za-z_][A-Za-z0-9_]*/
syntax match lipNumber /\<\%(0\|[1-9][0-9]*\)\%(\.[0-9]\+\)\?\%([eE][+-]\?[0-9]\+\)\?\>/
syntax match lipOperator /<+\|->\|=>\|==\|!=\|<=\|>=\|&&\|||\|\/\/\|\*\*\|\*\/\||>\|[=+*\/%!<>?-]/
syntax keyword lipTodo TODO FIXME XXX NOTE contained
syntax match lipComment /#.*/ contains=lipTodo,@Spell
syntax match lipEscape /\\\%(["\\nrt]\|u{[0-9A-Fa-f]\{1,6}}\)/ contained
syntax region lipString start=/"/ skip=/\\./ end=/"/ end=/$/ contains=lipEscape,@Spell
" Last match wins: triple quotes must take precedence over ordinary strings.
syntax region lipMultilineString start=/"""/ skip=/\\./ end=/"""/ contains=lipEscape,@Spell keepend
syntax sync fromstart
highlight default link lipKeyword Keyword
highlight default link lipConstant Constant
highlight default link lipBuiltin Function
highlight default link lipType Type
highlight default link lipFunction Function
highlight default link lipNumber Number
highlight default link lipOperator Operator
highlight default link lipComment Comment
highlight default link lipTodo Todo
highlight default link lipEscape SpecialChar
highlight default link lipString String
highlight default link lipMultilineString String
let b:current_syntax = 'lip'
