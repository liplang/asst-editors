;;; lip-mode.el --- Edit LIP 1.0 programs -*- lexical-binding: t; -*-

;; Package-Requires: ((emacs "27.1"))
;; Version: 1.0.0
;;; Commentary:
;; Add this directory to load-path and (require 'lip-mode).
;; C-c C-c checks, C-c C-r runs, C-c C-b builds; M-TAB completes.
;;; Code:

(require 'compile)
(require 'imenu)
(require 'subr-x)
(require 'skeleton)

(defgroup lip nil "LIP language support." :group 'languages)
(defcustom lip-indent-offset 2 "Indentation width." :type 'integer :safe #'integerp)
(defcustom lip-compiler-command "lipc" "LIP executable." :type 'string)
(defcustom lip-check-command "lipcheck" "Compile-only checker executable." :type 'string)
(defcustom lip-command-arguments nil
  "Extra arguments, before the source filename (e.g. -entry Main -host demo)."
  :type '(repeat string))
(defcustom lip-run-arguments nil
  "Run-only arguments, such as -input followed by a JSON object."
  :type '(repeat string))
(defcustom lip-project-root nil "Static import root, or nil for the file directory."
  :type '(choice (const nil) directory))

(defconst lip--keywords
  '("import" "as" "flow" "fn" "return" "if" "else" "match" "for" "in"
    "parallel" "break" "continue" "with" "next" "effect" "perform" "export" "void"))
(defconst lip--types '("any" "bool" "number" "string" "list" "object" "function" "effect"))
(defconst lip--builtins
  '("claim" "len" "str" "range" "map" "fold" "fail" "concat" "slice" "keys"
    "has" "put" "split" "parse_number"))
(defvar lip-mode-syntax-table
  (let ((table (make-syntax-table)))
    (modify-syntax-entry ?_ "w" table)
    (modify-syntax-entry ?# "<" table)
    (modify-syntax-entry ?\n ">" table)
    (modify-syntax-entry ?\" "\"" table)
    (modify-syntax-entry ?\\ "\\" table)
    (dolist (char '(?+ ?- ?* ?/ ?% ?= ?! ?< ?> ?& ?| ?? ?: ?.))
      (modify-syntax-entry char "." table))
    table))

(defun lip--syntax-propertize (start end)
  "Mark triple quote delimiters between START and END as generic strings."
  (goto-char start)
  (while (re-search-forward "\"\"\"" end t)
    (let* ((begin (match-beginning 0))
           (state (save-excursion (syntax-ppss begin))))
      (cond
       ((nth 5 state) (goto-char (1+ begin)))
       ((and (not (nth 4 state))
             (or (not (nth 3 state)) (eq t (nth 3 state))))
        (put-text-property begin (1+ begin) 'syntax-table (string-to-syntax "|"))
        (put-text-property (1+ begin) (+ begin 3) 'syntax-table (string-to-syntax ".")))))))

(defun lip-indent-line ()
  "Indent balanced LIP constructs without rewriting multiline string contents."
  (interactive)
  (let* ((offset (- (point) (line-beginning-position)))
         (state (syntax-ppss (line-beginning-position)))
         (open (nth 1 state))
         (indent 0))
    (unless (nth 3 state)
      (when open
        (setq indent
              (save-excursion
                (back-to-indentation)
                (let ((closing (looking-at "[])}]")))
                  (goto-char open)
                  (+ (current-indentation) (if closing 0 lip-indent-offset))))))
      (indent-line-to indent)
      (when (> offset indent) (move-to-column offset)))))

(defun lip-completion-at-point ()
  "Complete keywords, core functions, and names present in this buffer."
  (unless (let ((state (syntax-ppss))) (or (nth 3 state) (nth 4 state)))
    (let* ((bounds (bounds-of-thing-at-point 'symbol))
           (names (append lip--keywords lip--types lip--builtins '("true" "false" "null"))))
      (when bounds
        (save-excursion
          (goto-char (point-min))
          (while (re-search-forward "\\_<[A-Za-z_][A-Za-z0-9_]*\\_>" nil t)
            (push (match-string-no-properties 0) names)))
        (list (car bounds) (cdr bounds) (delete-dups names) :exclusive 'no)))))

(defun lip--imenu-index ()
  "List declarations, ignoring declaration-like text in strings and comments."
  (let (functions flows)
    (save-excursion
      (goto-char (point-min))
      (while (re-search-forward "\\_<\\(fn\\|flow\\)\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)" nil t)
        (let* ((begin (match-beginning 0))
               (kind (match-string-no-properties 1))
               (name (match-string-no-properties 2))
               (state (save-excursion (syntax-ppss begin))))
          (unless (or (nth 3 state) (nth 4 state))
            (if (equal kind "fn") (push (cons name begin) functions)
              (push (cons name begin) flows))))))
    (append (when flows (list (cons "Flows" (nreverse flows))))
            (when functions (list (cons "Functions" (nreverse functions)))))))

(defun lip--command (action &optional output)
  "Save and compile ACTION; OUTPUT is the explicit build destination."
  (unless buffer-file-name (user-error "Save this LIP buffer first"))
  (save-buffer)
  (let* ((project (when lip-project-root (expand-file-name lip-project-root (file-name-directory buffer-file-name))))
         (default-directory (if project (file-name-as-directory project) (file-name-directory buffer-file-name)))
         (args (append (if (equal action "check") (list lip-check-command)
                         (list lip-compiler-command action))
                       lip-command-arguments
                       (when (equal action "run") lip-run-arguments)
                       (when project (list "-project" project))
                       (when output (list "-o" (expand-file-name output)))
                       (list buffer-file-name))))
    (with-current-buffer (compilation-start (mapconcat #'shell-quote-argument args " ") 'compilation-mode)
      (setq-local compilation-error-regexp-alist '(lip-check lip-runtime))
      (setq-local compilation-error-regexp-alist-alist
                  '((lip-check "^\\(.+\\):\\([0-9]+\\):\\([0-9]+\\): " 1 2 3)
                    (lip-runtime "^E-[A-Z-]+ at \\(.+\\):\\([0-9]+\\):\\([0-9]+\\): " 1 2 3))))))

(defun lip-check () "Check the saved file without running its Flow." (interactive) (lip--command "check"))
(defun lip-run () "Run the saved file." (interactive) (lip--command "run"))
(defun lip-build (output)
  "Build an executable at OUTPUT."
  (interactive (list (read-file-name "Build executable: " nil nil nil "program")))
  (when (or (string-suffix-p ".lip" output t)
            (and buffer-file-name (equal (expand-file-name output) buffer-file-name)))
    (user-error "Choose an executable destination that does not overwrite LIP source"))
  (lip--command "build" output))

(define-skeleton lip--flow-template
  "Insert a named Flow." "Flow name: "
  "flow " str "(" (skeleton-read "Parameters (name: type): ") ") -> "
  (skeleton-read "Return type: " "any") " {\n" > "return " _ "\n" "}" > "\n")
(define-skeleton lip--function-template
  "Insert a pure function." "Function name: "
  "fn " str "(" (skeleton-read "Parameters (name: type): ") ") -> "
  (skeleton-read "Return type: " "number") " {\n" > _ "\n" "}" > "\n")
(define-skeleton lip--loop-template
  "Insert a sequential loop." "Item name: "
  "for " str " in " (skeleton-read "List expression: ") " {\n" > _ "\n" "}" > "\n")
(define-skeleton lip--carry-template
  "Insert carry iteration." "Result binding: "
  str " = for item in " (skeleton-read "List expression: ")
  " with acc = " (skeleton-read "Seed: " "0") " {\n" > "next " _ "\n" "}" > "\n")
(defun lip-insert-template (name)
  "Insert a prompted template selected by NAME."
  (interactive (list (completing-read "LIP template: " '("flow" "fn" "for" "carry") nil t)))
  (call-interactively (cdr (assoc name '(("flow" . lip--flow-template) ("fn" . lip--function-template)
                                       ("for" . lip--loop-template) ("carry" . lip--carry-template))))))

(defvar lip-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "C-c C-c") #'lip-check)
    (define-key map (kbd "C-c C-r") #'lip-run)
    (define-key map (kbd "C-c C-b") #'lip-build)
    (define-key map (kbd "C-c C-s") #'lip-insert-template)
    map))

;;;###autoload
(define-derived-mode lip-mode prog-mode "LIP"
  "Major mode for LIP 1.0."
  :syntax-table lip-mode-syntax-table
  (setq-local comment-start "# ")
  (setq-local comment-end "")
  (setq-local indent-tabs-mode nil)
  (setq-local tab-width lip-indent-offset)
  (setq-local indent-line-function #'lip-indent-line)
  (setq-local syntax-propertize-function #'lip--syntax-propertize)
  (add-hook 'syntax-propertize-extend-region-functions #'syntax-propertize-wholelines nil t)
  (setq-local font-lock-defaults
              `(((,(regexp-opt lip--keywords 'symbols) . font-lock-keyword-face)
                 (,(regexp-opt '("true" "false" "null") 'symbols) . font-lock-constant-face)
                 ("\\_<\\(?:fn\\|flow\\)\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)" 1 font-lock-function-name-face)
                 (":\\s-*\\(any\\|bool\\|number\\|string\\|list\\|object\\|function\\|effect\\)\\_>" 1 font-lock-type-face)
                 ("->\\s-*\\(any\\|bool\\|number\\|string\\|list\\|object\\|function\\|effect\\|void\\|null\\)\\_>" 1 font-lock-type-face)
                 ("\\_<\\(?:0\\|[1-9][0-9]*\\)\\(?:\\.[0-9]+\\)?\\(?:[eE][+-]?[0-9]+\\)?\\_>" . font-lock-constant-face)
                 (,(regexp-opt lip--builtins 'symbols) . font-lock-builtin-face))))
  (setq-local imenu-create-index-function #'lip--imenu-index)
  (setq-local beginning-of-defun-function
              (lambda (&optional arg) (re-search-backward "^[ \t]*\\(?:export[ \t]+\\)?\\(?:fn\\|flow\\)\\_>" nil 'move (or arg 1))))
  (add-hook 'completion-at-point-functions #'lip-completion-at-point nil t))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.lip\\'" . lip-mode))
(provide 'lip-mode)
;;; lip-mode.el ends here
