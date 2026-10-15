-- Optional Neovim conveniences; the syntax/indent/ftplugin live in ../vim.
local M = {}
function M.setup(opts)
  opts = opts or {}
  local source = debug.getinfo(1, 'S').source:sub(2)
  local base = vim.fn.fnamemodify(source, ':p:h:h:h:h')
  vim.opt.runtimepath:append(base .. '/vim')
  vim.filetype.add({ extension = { lip = 'lip' } })
  vim.g.lip_compiler = opts.compiler or 'lipc'
  vim.g.lip_check = opts.checker or 'lipcheck'
  vim.g.lip_args = opts.args or {}
  vim.g.lip_run_args = opts.run_args or {}
  vim.g.lip_project = opts.project or ''
  local group = vim.api.nvim_create_augroup('LipSupport', { clear = true })
  vim.api.nvim_create_autocmd('FileType', {
    group = group, pattern = 'lip', callback = function(event)
      if opts.keymaps ~= false then
        local map = function(key, command, desc)
          vim.keymap.set('n', key, command, { buffer = event.buf, desc = desc })
        end
        map('<localleader>c', '<cmd>LipCheck<cr>', 'LIP: check')
        map('<localleader>r', '<cmd>LipRun<cr>', 'LIP: run')
      end
      if opts.check_on_save then
        vim.api.nvim_create_autocmd('BufWritePost', {
          group = group, buffer = event.buf, callback = function() vim.cmd.LipCheck() end,
        })
      end
    end,
  })
end
return M
