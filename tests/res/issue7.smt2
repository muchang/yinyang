(define-const a String "\x0a")
(define-const b String "\n")
(simplify (= a b))
(simplify (str.++ a b))
(check-sat)
