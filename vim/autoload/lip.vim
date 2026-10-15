" Shared Vim 9 / Neovim runtime. No plugin manager or language server required.
let s:save_cpo = &cpoptions
set cpoptions&vim
let s:words = split('import as flow fn return if else match for in parallel break continue with next effect perform export void true false null any bool number string list object function claim len str range map fold fail concat slice keys has put split parse_number')
let s:templates = {
      \ 'flow': ['flow Main() -> any {', '  return null', '}'],
      \ 'fn': ['fn name(value: number) -> number {', '  value', '}'],
      \ 'if': ['if condition {', '  result = true', '} else {', '  result = false', '}'],
      \ 'for': ['for item in items {', '  result = item', '}'],
      \ 'carry': ['total = for item in items with acc = 0 {', '  next acc + item', '}'],
      \ 'claimfor': ['results = claim()', 'for item in items parallel {', '  results <+ item', '}'],
      \ 'match': ['match value {', '  null => 0,', '  _ => 1', '}'],
      \ 'importlip': ['import lip "lib/module.lip" as module'],
      \ 'text': ['"""', '', '"""']}

function! lip#TemplateNames(lead, line, pos) abort
  return filter(sort(keys(s:templates)), 'stridx(v:val, a:lead) == 0')
endfunction

function! lip#Template(name) abort
  if !has_key(s:templates, a:name)
    echoerr 'Unknown LIP template: ' . a:name
    return
  endif
  let prefix = matchstr(getline('.'), '^\s*')
  let lines = map(copy(s:templates[a:name]), 'prefix . v:val')
  if getline('.') =~# '^\s*$'
    call setline('.', lines[0])
    call append(line('.'), lines[1:])
  else
    call append(line('.'), lines)
    normal! j
  endif
endfunction

function! lip#Complete(findstart, base) abort
  if a:findstart
    let start = col('.') - 1
    while start > 0 && getline('.')[start - 1] =~# '[A-Za-z0-9_]'
      let start -= 1
    endwhile
    return start
  endif
  let words = copy(s:words)
  for line in getline(1, '$')
    call extend(words, split(substitute(line, '[^A-Za-z0-9_]', ' ', 'g')))
  endfor
  return filter(sort(uniq(sort(words))), 'v:val =~# "^[A-Za-z_]" && stridx(v:val, a:base) == 0')
endfunction

function! lip#Indent(lnum) abort
  " Scan delimiters, comments and both string forms. Syntax highlighting may be off.
  let stack = []
  let mode = ''
  let continued = 0
  for n in range(1, a:lnum - 1)
    let line = getline(n)
    let i = 0
    let continued = 0
    while i < strlen(line)
      let c = line[i]
      if mode !=# ''
        if c ==# '\'
          let i += 2
          continue
        elseif mode ==# 'triple' && strpart(line, i, 3) ==# '"""'
          let mode = ''
          let i += 3
          continue
        elseif mode ==# 'single' && c ==# '"'
          let mode = ''
        endif
      elseif c ==# '#'
        break
      elseif strpart(line, i, 3) ==# '"""'
        let mode = 'triple'
        let i += 3
        continue
      elseif c ==# '"'
        let mode = 'single'
      elseif c =~# '[([{]'
        call add(stack, [c, indent(n)])
      elseif c =~# '[])}]' && !empty(stack)
        call remove(stack, -1)
      elseif c ==# '\' && i == strlen(line) - 1
        let continued = 1
      endif
      let i += 1
    endwhile
    if mode ==# 'single'
      let mode = ''
    endif
  endfor
  if mode ==# 'triple'
    return -1
  endif
  let closing = getline(a:lnum) =~# '^\s*[])}]'
  if !empty(stack)
    return stack[-1][1] + (closing ? 0 : shiftwidth())
  endif
  return continued ? shiftwidth() : 0
endfunction

function! lip#Arguments() abort
  let args = copy(get(b:, 'lip_args', get(g:, 'lip_args', [])))
  let root = get(b:, 'lip_project', get(g:, 'lip_project', ''))
  if !empty(root)
    call extend(args, ['-project', fnamemodify(root, ':p')])
  endif
  return args
endfunction

function! lip#Check() abort
  if empty(expand('%:p'))
    echoerr 'Save this LIP buffer first'
    return
  endif
  update
  let args = [get(g:, 'lip_check', 'lipcheck')] + lip#Arguments() + [expand('%:p')]
  let output = system(join(map(copy(args), 'shellescape(v:val)'), ' '))
  let failed = v:shell_error
  call setqflist([], ' ', {'title': 'LIP check', 'lines': split(output, "\n"), 'efm': '%f:%l:%c: %m'})
  " Compiler columns count Unicode scalars; Quickfix expects byte offsets.
  let items = getqflist()
  for item in items
    if get(item, 'valid', 0) && item.lnum > 0 && item.col > 0
      let lines = getbufline(item.bufnr, item.lnum)
      if empty(lines) && filereadable(bufname(item.bufnr))
        let lines = readfile(bufname(item.bufnr), '', item.lnum)[-1:]
      endif
      if !empty(lines)
        let column = byteidxcomp(lines[0], item.col - 1)
        if column >= 0
          let item.col = column + 1
        endif
      endif
    endif
  endfor
  call setqflist(items, 'r')
  if failed
    copen
  else
    cclose
    echom 'LIP check passed'
  endif
endfunction

function! lip#Run(...) abort
  if empty(expand('%:p'))
    echoerr 'Save this LIP buffer first'
    return
  endif
  update
  let args = [get(g:, 'lip_compiler', 'lipc'), a:0 ? 'build' : 'run'] + lip#Arguments()
  if !a:0
    call extend(args, get(b:, 'lip_run_args', get(g:, 'lip_run_args', [])))
  endif
  if a:0
    if fnamemodify(a:1, ':p') ==# expand('%:p') || a:1 =~? '\.lip$'
      echoerr 'Choose an executable destination that does not overwrite LIP source'
      return
    endif
    call extend(args, ['-o', fnamemodify(a:1, ':p')])
  endif
  call add(args, expand('%:p'))
  let cwd = get(b:, 'lip_project', get(g:, 'lip_project', ''))
  if empty(cwd)
    let cwd = expand('%:p:h')
  endif
  botright new
  if has('nvim')
    call termopen(args, {'cwd': cwd})
    startinsert
  else
    call term_start(args, {'curwin': 1, 'cwd': cwd})
  endif
endfunction

let &cpoptions = s:save_cpo
unlet s:save_cpo
