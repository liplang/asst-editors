if exists('b:did_ftplugin')
  finish
endif
let b:did_ftplugin = 1
setlocal comments=:# commentstring=#\ %s
setlocal expandtab shiftwidth=2 softtabstop=2
setlocal suffixesadd=.lip
setlocal omnifunc=lip#Complete
setlocal formatoptions-=t formatoptions+=croql
command! -buffer LipCheck call lip#Check()
command! -buffer LipRun call lip#Run()
command! -buffer -nargs=1 -complete=file LipBuild call lip#Run(<q-args>)
command! -buffer -nargs=1 -complete=customlist,lip#TemplateNames LipTemplate call lip#Template(<q-args>)
let b:undo_ftplugin = 'setlocal comments< commentstring< expandtab< shiftwidth< softtabstop< suffixesadd< omnifunc< formatoptions< | delcommand LipCheck | delcommand LipRun | delcommand LipBuild | delcommand LipTemplate'
