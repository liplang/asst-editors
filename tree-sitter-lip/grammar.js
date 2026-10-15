// A tolerant structural grammar for editing, not a replacement for lipcheck.
// Keeping all balanced groups permits incremental highlighting of unfinished
// programs without duplicating the compiler's type, purity or graph rules.
module.exports = grammar({
  name: 'lip',
  word: $ => $.identifier,
  extras: $ => [/\s/, $.comment, /\\\r?\n/],
  rules: {
    source_file: $ => repeat($._item),
    _item: $ => choice(
      $.function_declaration, $.flow_declaration, $.anonymous_function,
      $.import_declaration, $.parentheses, $.list, $.block,
      $.multiline_string, $.string, $.number, $.identifier,
      $._keyword, $.operator, $.punctuation,
    ),
    function_declaration: $ => prec(2, seq(
      'fn', field('name', $.identifier), field('parameters', $.parentheses),
      '->', field('return_type', choice(alias($.identifier, $.type), 'effect', 'null')), optional('?'),
      field('body', $.block),
    )),
    flow_declaration: $ => prec(2, seq(
      'flow', field('name', $.identifier), field('parameters', $.parentheses),
      '->', field('return_type', choice(alias($.identifier, $.type), 'void', 'null', 'effect')),
      optional('?'), field('body', $.block),
    )),
    anonymous_function: $ => prec(2, seq(
      'fn', field('parameters', $.parentheses), '->',
      field('return_type', choice(alias($.identifier, $.type), 'effect', 'null')),
      optional('?'), field('body', $.block),
    )),
    import_declaration: $ => prec.right(2, seq(
      'import', field('kind', choice('go', 'python', 'host', 'lip')),
      field('path', $.string), optional(seq('as', field('alias', $.identifier))),
    )),
    parentheses: $ => seq('(', repeat($._item), ')'),
    list: $ => seq('[', repeat($._item), ']'),
    block: $ => seq('{', repeat($._item), '}'),
    identifier: _ => /[A-Za-z_][A-Za-z0-9_]*/,
    number: _ => /(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/,
    comment: _ => token(seq('#', /[^\r\n]*/)),
    string: $ => seq('"', repeat(choice(
      $.escape_sequence, $.invalid_escape, token.immediate(/[^"\\\r\n]+/),
    )), '"'),
    multiline_string: $ => seq('"""', repeat(choice(
      $.escape_sequence, $.invalid_escape, token.immediate(/[^"\\]+/),
      token.immediate(/"{1,2}/),
    )), '"""'),
    escape_sequence: _ => token.immediate(prec(1, /\\(?:["\\nrt]|u\{[0-9a-fA-F]{1,6}\})/)),
    invalid_escape: _ => token.immediate(/\\[^\r\n]/),
    _keyword: _ => choice(
      'import', 'as', 'flow', 'fn', 'return', 'if', 'else', 'match', 'for', 'in',
      'parallel', 'break', 'continue', 'with', 'next', 'effect', 'perform', 'export',
      'void', 'true', 'false', 'null',
    ),
    operator: _ => choice('<+', '->', '=>', '==', '!=', '<=', '>=', '&&', '||',
      '//', '**', '*/', '|>', '=', '+', '-', '*', '/', '%', '!', '<', '>', '?'),
    punctuation: _ => choice('.', ',', ':', ';'),
  },
});
