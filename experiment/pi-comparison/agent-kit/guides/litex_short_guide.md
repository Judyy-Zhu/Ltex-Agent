# LiteX Short Guide (for LitexGeo Library Construction)

## 1. Choosing the Form of Definitions

| Purpose | LiteX Form |
|------|-----------|
| Properties/Relations/Conditions | `prop` |
| Named Objects (given values/types) | `have` |
| Explicit Formula Mappings | `have fn` |
| Unique Existence Selection | `have fn ... by exist!` |

## 2. Function Definitions (have fn)

**Basic Syntax**:
```litex
have fn name(arg1, arg2 Type) ReturnType = expression
```

**Examples**:
```litex
have fn vec(A, B cart(R, R)) cart(R, R) = (B(1) - A(1), B(2) - A(2))
have fn dot(u, v cart(R, R)) R = u(1) * v(1) + u(2) * v(2)
have fn distance_sq(A, B cart(R, R)) R = dot(vec(A, B), vec(A, B))
```

**Key Rules**:
- Type annotation format: `(arg Type)` without colon `:`
- Return type written directly, without arrow `->`
- Expression written directly, without `return`

### 2.1 Functions Returning Sets

**Functions returning sets must use `power_set(Type)` as the return type**, not `set` directly.

**Basic Syntax**:
```litex
have fn name(args Type) power_set(ElementType) = {element ElementType: conditions}
```

**Parameters with Constraints**:
```litex
have fn name(arg1, arg2 Type: constraint) power_set(ElementType) = {element ElementType: conditions}
```

**Examples**:
```litex
# Line (general equation)
have fn line(a, b, c R: a != 0 or b != 0) power_set(cart(R, R)) = 
    {p cart(R, R): a * p(1) + b * p(2) + c = 0}

# Line through two points
have fn line_of(a, b cart(R, R): a != b) power_set(cart(R, R)) = 
    {p cart(R, R): det(vec(a, p), vec(a, b)) = 0}

# Circle
have fn circle(o cart(R, R), r R) power_set(cart(R, R)) = 
    {p cart(R, R): distance_sq(o, p) = r * r}
```

**Key Rules**:
- ✅ Use `power_set(cart(R, R))` as return type
- ❌ **Don't use** `set` (will error with "set is not a valid identifier")
- Constraints written after parameters: `(a, b Type: constraint)`
- Set comprehension: `{element Type: conditions}`

## 3. Predicate Definitions (prop)

**Basic Syntax**:
```litex
prop name(args Type):
    conditions
```

**Examples**:
```litex
prop is_collinear(p, q, r cart(R, R)):
    det(vec(p, q), vec(p, r)) = 0

prop is_perpendicular(a, b, c, d cart(R, R)):
    a != b
    c != d
    dot(vec(a, b), vec(c, d)) = 0
```

**Key Rules**:
- Used to define conditions, relations, properties
- Can have multiple conditions, one per line
- Write non-zero conditions first, then main equations
- **⚠️ Use lowercase letters for parameter names** (p, q, r, a, b etc.), not uppercase (P, Q, R), otherwise you'll get "variable already bound" errors
- **⚠️ When using prop in theorem conditions or conclusions, must add `$` prefix** (see "Theorem Proofs" below)

### 3.1 Existential Quantifier (exist ... st)

To express "there exists" in prop, use `exist ... st {...}` syntax:

**Basic Syntax**:
```litex
prop name(args Type):
    exist var1, var2 Type st {condition1, condition2, ...}
```

**Examples**:
```litex
# Check if a set is a line
prop is_line(L power_set(cart(R, R))):
    exist a, b, c R st {a != 0 or b != 0, L = line(a, b, c)}

# Check if four points are concyclic
prop are_concyclic(a, b, c, d cart(R, R)):
    exist o cart(R, R) st {
        distance_sq(o, a) = distance_sq(o, b),
        distance_sq(o, b) = distance_sq(o, c),
        distance_sq(o, c) = distance_sq(o, d)
    }
```

**Key Rules**:
- ✅ Use `exist ... st {...}` 
- ❌ **Don't use** `exists ... :` or `exist ... :` (will error with "Expected operator or $prop in fact")
- Conditions after `st` are wrapped in curly braces `{...}`
- Multiple conditions separated by commas

### 3.2 Set Membership ($in)

To check if an element belongs to a set, use the `$in` operator:

**Basic Syntax**:
```litex
prop name(element, set):
    element $in set
```

**Examples**:
```litex
# Check if point is on line
prop is_on_line(p, a, b cart(R, R)):
    a != b
    p $in line_of(a, b)

# Check if point is on circle
prop is_on_circle(p, o cart(R, R), r R):
    p $in circle(o, r)
```

**Key Rules**:
- ✅ Use `$in` 
- ❌ **Don't use** `in` (will error with "Expected operator or $prop in fact")
- Must prefix with dollar sign `$`

## 4. Theorem Proofs (thm)

**Basic Syntax** (without conditions):
```litex
thm name:
    ? forall x, y Type:
        conclusion
    proof_body (equation chain)
```

**Basic Syntax** (with conditions, using equations as conditions):
```litex
thm name:
    ? forall x, y Type:
        condition1,        # ← Multiple conditions separated by commas
        condition2,        # ← Comma
        condition3         # ← Last condition without comma
        =>:
            conclusion
    proof_body (equation chain)
```

**Basic Syntax** (with conditions, using prop predicates as conditions):
```litex
thm name:
    ? forall x, y Type:
        $prop_name(args),  # ← prop needs $ prefix, multiple conditions with commas
        $prop_name(args)   # ← Last one without comma
        =>:
            $prop_name(args)  # ← Conclusion also needs $
    proof_body (equation chain)
```

**⚠️ Important: Multiple conditions must be separated by commas!**
- ✅ `condition1, condition2 =>:`
- ❌ `condition1 condition2 =>:` (will cause ParseError)

**Examples** (equation conditions):
```litex
thm addition_cancel:
    ? forall a, b, c R:
        a + c = b + c
        =>:
            a = b
    a = (a + c) - c = (b + c) - c = b

thm addition_cancel_left:
    ? forall a, b, c R:
        c + a = c + b
        =>:
            a = b
    c + a = a + c
    c + b = b + c
    by thm addition_cancel(a, b, c)
```

**Examples** (prop predicate conditions):
```litex
# Already defined: prop is_collinear(p, q, r): det(vec(p, q), vec(p, r)) = 0

thm collinear_symmetric:
    ? forall p, q, r cart(R, R):
        $is_collinear(p, q, r)    # ← Using prop needs $ prefix
        =>:
            $is_collinear(p, r, q)  # ← Conclusion also needs $
    det(vec(p, r), vec(p, q)) = -det(vec(p, q), vec(p, r))
    -det(vec(p, q), vec(p, r)) = -0
    -0 = 0
```

**Examples** (multiple conditions, separated by commas):
```litex
# Already defined: prop are_segments_congruent(a, b, c, d): distance_sq(a, b) = distance_sq(c, d)

thm segments_congruent_transitive:
    ? forall a, b, c, d, e, f cart(R, R):
        $are_segments_congruent(a, b, c, d),    # ← Condition 1, comma
        $are_segments_congruent(c, d, e, f)     # ← Condition 2, last one without comma
        =>:
            $are_segments_congruent(a, b, e, f)
    distance_sq(a, b) = distance_sq(c, d)
    distance_sq(c, d) = distance_sq(e, f)
    distance_sq(a, b) = distance_sq(e, f)
```

**Key: prop predicates in conditions and conclusions must use `$` prefix!**
- ✅ `$is_collinear(p, q, r)`
- ❌ `is_collinear(p, q, r)` (will cause ParseError)

**Key: Multiple conditions must be separated by commas!**
- ✅ `condition1, condition2 =>:`
- ❌ `condition1 condition2 =>:` (will cause ParseError)


**Key Rules**:
- Use `?` to start goal block, not `prove:`
- Conditions and conclusions separated by `=>:`
- Proof body is **equation chain**, not tactic style (no `proof...end`)
- Can reference other theorems: `by thm name(args)`
- **Theorems must have proof bodies**, not just declarations
- **⚠️ Must declare expanded forms before using function definitions** (see "Using Function Definitions" below)
- **⚠️ Avoid variable name conflicts**: If P, Q, R are already used in conditions, don't rebind these variables in the proof
- **⚠️ Don't redeclare conditions in proofs** (see "Using Conditions" below)

## 4.1 Using Conditions (Assumptions)

In theorems with conditions, the conditions defined through `prop` imply certain equations, which you can use directly in the proof.

**❌ Error: Redeclaring conditions**:
```litex
# Given: prop is_collinear(p, q, r): det(vec(p, q), vec(p, r)) = 0

thm is_collinear_symmetric:
    ? forall p, q, r cart(R, R):
        is_collinear(p, q, r)        # Condition
        =>:
            is_collinear(p, r, q)
    det(vec(p, q), vec(p, r)) = 0    # ❌ Error! This is redeclaring the condition
    det(vec(p, r), vec(p, q)) = -det(vec(p, q), vec(p, r))
    ...
```
This will cause `Expected operator or $prop in fact` error.

**✅ Correct: Use the equation implied by the condition directly**:
```litex
thm is_collinear_symmetric:
    ? forall p, q, r cart(R, R):
        is_collinear(p, q, r)        # Condition implies: det(vec(p, q), vec(p, r)) = 0
        =>:
            is_collinear(p, r, q)
    det(vec(p, r), vec(p, q)) = -det(vec(p, q), vec(p, r))  # Start proof directly
    -det(vec(p, q), vec(p, r)) = -0   # Use condition: det(vec(p, q), vec(p, r)) = 0
    -0 = 0
```

**Principle:**
- The condition `is_collinear(p, q, r)` is defined as `det(vec(p, q), vec(p, r)) = 0`
- In the proof, you can replace `det(vec(p, q), vec(p, r))` with `0`
- But **don't** redeclare `det(vec(p, q), vec(p, r)) = 0` at the start of the proof, this will be treated as a syntax error

**Another example:**
```litex
# Given: prop is_perpendicular(a, b, c, d): 
#           a != b
#           c != d  
#           dot(vec(a, b), vec(c, d)) = 0

thm perpendicular_symmetric:
    ? forall a, b, c, d cart(R, R):
        is_perpendicular(a, b, c, d)
        =>:
            is_perpendicular(c, d, a, b)
    dot(vec(c, d), vec(a, b)) = dot(vec(a, b), vec(c, d))  # Dot product commutativity
    dot(vec(a, b), vec(c, d)) = 0   # Use condition
    0 = 0
```

Key: Equations given by conditions are **available knowledge**, use them directly in the equation chain, don't redeclare them.

## 5. Equation Chain Proofs

**Continuous equations** (recommended, concise):
```litex
a = (a + c) - c = (b + c) - c = b
```

**Step-by-step equations** (each line must be a complete equation, left = right):
```litex
a = (a + c) - c
(a + c) - c = (b + c) - c
(b + c) - c = b
```

**❌ Error 1: Cannot write left side alone**:
```litex
a           # Error! Expected operator or $prop in fact
= (a + c) - c
= (b + c) - c
```

**❌ Error 2: Don't repeat intermediate terms**:
```litex
a = (a + c) - c
(a + c) - c              # Error! Don't repeat
= (b + c) - c
(b + c) - c              # Error! Don't repeat
= b
```

**✅ Correct: Right side of previous line = left side of next line**:
```litex
a = (a + c) - c          # a to (a + c) - c
(a + c) - c = (b + c) - c    # (a + c) - c to (b + c) - c
(b + c) - c = b          # (b + c) - c to b
```

**Referencing theorems**:
```litex
by thm theorem_name(arg1, arg2, arg3)
```

**Important Rules**:
- Each equation must have both left and right sides: `left = right`
- Step-by-step equations: right side of previous line should equal left side of next line
- Don't write the right side alone on the next line

**Important Technique: Avoid Large Jumps**

When the relationship between two expressions is not obvious, don't directly write `A = B`. Use an equation chain to expand intermediate steps:

**❌ Error: Jump too large**:
```litex
det(vec(p, r), vec(p, q)) = -det(vec(p, q), vec(p, r))  # litex cannot verify
```

**✅ Correct: Use equation chain to expand**:
```litex
# First expand both det definitions
det(vec(p, r), vec(p, q)) = vec(p, r)(1) * vec(p, q)(2) - vec(p, r)(2) * vec(p, q)(1)
det(vec(p, q), vec(p, r)) = vec(p, q)(1) * vec(p, r)(2) - vec(p, q)(2) * vec(p, r)(1)

# Then connect with equation chain (multiple steps in one line)
det(vec(p, r), vec(p, q)) = vec(p, r)(1) * vec(p, q)(2) - vec(p, r)(2) * vec(p, q)(1) = -(vec(p, q)(1) * vec(p, r)(2) - vec(p, q)(2) * vec(p, r)(1)) = -det(vec(p, q), vec(p, r))
```

**Multiple-step connections in equation chains**:
You can use multiple `=` to connect intermediate steps in one line, as long as each step can be verified by litex:
```litex
A = B = C = D = E
```
Equivalent to:
```litex
A = B
B = C
C = D
D = E
```

## 6. Using Function Definitions

**Key Rule: When using function definitions in proofs, you must first declare the expanded form of that definition.**

LiteX does not automatically expand functions defined with `have fn`. If you want to use the concrete form of a function in a proof, you must first write the expansion as an equation.

**❌ Error: Directly using function definition**:
```litex
# Seed library has: have fn vec(A, B cart(R, R)) cart(R, R) = (B(1) - A(1), B(2) - A(2))

thm my_theorem:
    ? forall A, B cart(R, R):
        ...
    distance_sq(A, B) = dot(vec(A, B), vec(A, B))
    dot(vec(A, B), vec(A, B)) = (B(1) - A(1)) * (B(1) - A(1)) + ...  # ❌ Error!
    # LiteX doesn't know vec(A, B) = (B(1) - A(1), B(2) - A(2))
```

**✅ Correct: Declare definition first, then use**:
```litex
thm my_theorem:
    ? forall A, B cart(R, R):
        ...
    vec(A, B) = (B(1) - A(1), B(2) - A(2))              # ← Declare expansion first
    vec(B, A) = (A(1) - B(1), A(2) - B(2))              # ← Declare another if needed
    distance_sq(A, B) = dot(vec(A, B), vec(A, B))
    dot(vec(A, B), vec(A, B)) = dot((B(1) - A(1), B(2) - A(2)), (B(1) - A(1), B(2) - A(2)))
    dot((B(1) - A(1), B(2) - A(2)), (B(1) - A(1), B(2) - A(2))) = (B(1) - A(1)) * (B(1) - A(1)) + ...
```

**Another example:**
```litex
# Seed library has: have fn det(u, v cart(R, R)) R = u(1) * v(2) - u(2) * v(1)

thm det_antisymmetric:
    ? forall u, v cart(R, R):
        det(v, u) = -det(u, v)
    det(u, v) = u(1) * v(2) - u(2) * v(1)    # ← Declare det definition first
    det(v, u) = v(1) * u(2) - v(2) * u(1)    # ← Also declare reversed form
    v(1) * u(2) - v(2) * u(1) = -(u(1) * v(2) - u(2) * v(1))
    -(u(1) * v(2) - u(2) * v(1)) = -det(u, v)
```

**Reason:**
`have fn` only gives a definition, but LiteX won't automatically substitute it in proofs. You need to explicitly write the equation for LiteX to consider it an available fact.

## 7. Variable Naming Rules

**Avoid variable name conflicts:**

Variables bound in `forall` are valid throughout the entire theorem scope. Don't rebind the same variable names in the proof.

**❌ Error: Variable name conflict**:
```litex
thm is_collinear_symmetric:
    ? forall P, Q, R cart(R, R):          # P, Q, R already bound
        is_collinear(P, Q, R)
        =>:
            is_collinear(P, R, Q)
    forall P, Q, R cart(R, R):            # ❌ Error! P, Q, R already exist
        det(vec(P, R), vec(P, Q)) = 0
```

Error message: `name 'Q' is already active in this scope and cannot be rebound`

**✅ Correct: Use already-bound variables directly**:
```litex
thm is_collinear_symmetric:
    ? forall P, Q, R cart(R, R):          # P, Q, R already bound
        is_collinear(P, Q, R)
        =>:
            is_collinear(P, R, Q)
    det(vec(P, Q), vec(P, R)) = 0         # ✅ Use P, Q, R directly
    det(vec(P, R), vec(P, Q)) = -det(vec(P, Q), vec(P, R))
    -det(vec(P, Q), vec(P, R)) = -0
    -0 = 0
```

**✅ Or use different variable names**:
```litex
thm is_collinear_symmetric:
    ? forall A, B, C cart(R, R):          # Use A, B, C
        is_collinear(A, B, C)
        =>:
            is_collinear(A, C, B)
    det(vec(A, B), vec(A, C)) = 0
    det(vec(A, C), vec(A, B)) = -det(vec(A, B), vec(A, C))
    -det(vec(A, B), vec(A, C)) = -0
    -0 = 0
```

## 8. Common Errors

### 8.1 Syntax Errors

❌ Don't use Python/Lean style:
```litex
def vec(A, B: cart(R, R)) -> cart(R, R):  # Error!
    return (B(1) - A(1), B(2) - A(2))
```

❌ Don't use tactic-style proofs:
```litex
thm name: ? goal
proof
    unfold definition
    apply lemma
end
```

❌ Don't use prove: keyword:
```litex
thm name:
    prove:  # Error! Should use ?
        forall x. P(x)
```

❌ Don't write theorem declaration without proof:
```litex
thm name: ? forall x. P(x)  # Error! Must have proof body
```

✅ Correct LiteX style:
```litex
have fn vec(A, B cart(R, R)) cart(R, R) = (B(1) - A(1), B(2) - A(2))

thm name:
    ? forall x Type:
        P(x)
    proof_steps_here
```

### 8.2 Verification Errors and Solutions

When the compiler returns verification errors, understanding the error types can help you find the right solution:

#### VerifyError: atomic fact unknown
**Meaning**: You directly asserted an equation (atomic fact), but the verifier cannot determine why it holds.

**Example**:
```litex
thm parallel_transitive:
    ? forall a, b, c, d, f, g cart(R, R):
        $is_parallel(a, b, c, d),
        $is_parallel(c, d, f, g)
        =>:
            $is_parallel(a, b, f, g)
    det(vec(a, b), vec(f, g)) = 0  # ❌ atomic fact unknown
```

**Reason**:
- Premises: `det(vec(a, b), vec(c, d)) = 0` and `det(vec(c, d), vec(f, g)) = 0`
- Conclusion: `det(vec(a, b), vec(f, g)) = 0`
- This **is not a simple algebraic identity**, it needs complex proof

**Solutions**:
1. **Provide complete proof chain**: Expand all intermediate steps, don't jump
2. **Use auxiliary constructions**: Construct verifiable equations by multiplying non-zero terms
3. **Add extra premises**: Some theorems need additional non-zero conditions

**Correct proof strategy**:
```litex
thm parallel_transitive:
    ? forall a, b, c, d, x, y cart(R, R):
        $is_parallel(a, b, c, d),
        $is_parallel(c, d, x, y),
        distance_sq(c, d) != 0           # ← Add extra premise
        =>:
            $is_parallel(a, b, x, y)
    # Expand all definitions
    vec(a, b) = (b(1) - a(1), b(2) - a(2))
    vec(c, d) = (d(1) - c(1), d(2) - c(2))
    vec(x, y) = (y(1) - x(1), y(2) - x(2))
    
    # Construct auxiliary term: det * distance_sq (can be algebraically expanded)
    det(vec(a, b), vec(x, y)) * distance_sq(c, d) = ...(long algebraic expansion)...
    
    # Prove auxiliary term equals 0
    ...(more steps)... = 0
    
    # Finally derive conclusion through division
    det(vec(a, b), vec(x, y)) = 0
```

#### VerifyError: chain fact unknown
**Meaning**: A step in the equation chain is too large a jump; the verifier cannot understand the intermediate derivation.

**Example**:
```litex
det(vec(p, r), vec(p, q)) = -det(vec(p, q), vec(p, r))  # ❌ chain fact unknown
```

**Solution**: Break large steps into smaller steps, explicitly expand intermediate algebraic operations:
```litex
det(vec(p, r), vec(p, q)) = vec(p, r)(1) * vec(p, q)(2) - vec(p, r)(2) * vec(p, q)(1)
vec(p, r)(1) * vec(p, q)(2) - vec(p, r)(2) * vec(p, q)(1) = -(vec(p, q)(1) * vec(p, r)(2) - vec(p, q)(2) * vec(p, r)(1))
-(vec(p, q)(1) * vec(p, r)(2) - vec(p, q)(2) * vec(p, r)(1)) = -det(vec(p, q), vec(p, r))
```

#### ParseError: name already active
**Meaning**: You rebind the same variable name in the same scope.

**Solution**: Use different variable names, or directly use already-bound variables (see Section 7).

#### TypeError: type mismatch
**Meaning**: Expression types don't match, e.g., using a point as a vector.

**Solution**: Check the type of each expression, ensure function parameter types are correct.

### 8.3 Proof Strategy Tips

For complex transitivity theorems (such as parallel transitivity, congruence transitivity), common proof techniques:

1. **Multiply by auxiliary non-zero terms**: Transform goal `A = 0` into `A * B = 0`, where `B != 0` is known
2. **Add non-zero premises**: Such as `distance_sq(c, d) != 0` to allow division
3. **Fully expand algebra**: Expand all function definitions into coordinate form, then connect with algebraic identities
4. **Use intermediate lemmas**: First prove auxiliary lemmas, then reference them in the main theorem

## 9. Common Techniques (Battle-Tested Experience)

### 9.1 Break down in natural language first, then write Litex

Before solving a problem, write out your approach in natural language, then map it to code. It's recommended to put **brief natural language process** at the beginning of the code as comments, serving as a proof outline:

```litex
# Approach: angle congruence ⇒ cos numerators are proportional; multiply both sides by denominators for cross-multiplication;
#       then use |u|^2|v|^2 - (u·v)^2 = det^2 to substitute both sides and derive the result
thm angle_congruence_det_ratio:
    ? forall ...
```

In the outline, write clearly:

1. **Given** / **Goal**
2. **Initial approach** for computation (for pure computational problems, it's often just expansion + algebraic identities, no need for detours)
3. Then translate to Litex lines

Don't start by piling up `by thm` immediately.

### 9.2 Definitions aim for convenience, first instinct isn't always best

For the same geometric concept, choose **the definition that's easiest to prove later**.

Classic comparison for `is_midpoint`:

```litex
# ❌ Heavy: collinearity + equidistance (later theorems become heavy)
prop is_midpoint(p, a, b cart(R, R)):
    $is_collinear(a, p, b)
    distance_sq(a, p) = distance_sq(p, b)

# ✅ Convenient: coordinate average (expansion is just algebra)
prop is_midpoint(p, a, b cart(R, R)):
    p(1) = (a(1) + b(1)) / 2
    p(2) = (a(2) + b(2)) / 2
```

Principle: Definitions should serve the subsequent reasoning, not just “sound geometrically right”.

### 9.3 Fix where you're stuck; if stuck, change approach

- When verification fails: Only fix **the first** error or equation chain breakpoint, don't rewrite the whole section.
- Still stuck: Change approach, for example
  - Change definition shape (wrapper layer `dot(vec(...))` → direct coordinates)
  - Change proof strategy (forward equation chain → `by contra`)
  - Align with Builtin shapes (see Section 11), rather than guessing rule names

Typical pitfall (`point_difference_norm_pos`):

```litex
# ❌ Mixing = and > in one step, and jump too large
dot(vec(a, b), vec(a, b)) = (b(1)-a(1))*(b(1)-a(1)) + (b(2)-a(2))*(b(2)-a(2)) > 0

# ✅ First chain equations for expansion, write positivity separately, align with x^2 / sum of squares
#    Writing goal as (b(1)-a(1))^2 + (b(2)-a(2))^2 > 0 is often smoother
```

### 9.4 Build framework first, use axiom when stuck, then fill in gradually

For library construction: **First establish interface and dependency skeleton, then fill in proof details**.

If a certain `thm` repeatedly fails to prove but will be used later: Don't leave it empty (later `by thm ...` will fail to find it). First write it as an `axiom` with the same name and statement, allowing the library to continue growing:

```litex
# When proof fails, use this as a placeholder; debt = how many such axioms remain in the library
axiom point_difference_norm_pos:
    ? forall a, b cart(R, R):
        a != b
        =>:
            (b(1) - a(1))^2 + (b(2) - a(2))^2 > 0
```

Principles:

- axiom must be **statements you believe are true**, just not proven yet
- Each axiom records a trust debt, to be changed back to `thm` + proof later
- This is a progression tool, not an endpoint: skeleton first, details later
- Automated experiment runner already uses `litex -session` + `try` for incremental verification; theorems that fail multiple times are automatically replaced with axioms to maintain the library

### 9.5 Litex is fact-oriented: fewer `by thm`, more “facts that need to hold”

**Litex is fundamentally a fact-oriented language.** The encouraged code format is to directly write **what to prove** (equations/conditions that need to hold), rather than piling up a series of **how to prove** reference steps.

For expanding `have fn` / `prop`, **directly writing equations is often shorter and more readable** (see Section 6). The verifier recognizes fact shapes, not “which name you referenced”.

Therefore: **Don't write in Lean style** — a series of `by thm xxx` only declaring “used a certain lemma”, without laying out the intermediate facts.

**Pure computation / identity problems**: Natural language first approach is usually “expand definitions → algebraic manipulation”. Then **just compute directly following this approach**, don't force-insert a series of `by thm` just to “use the library”.

```litex
# ❌ how-to piling: simple cross multiplication but first by thm a bunch
by thm dot_det_eliminate(...)
by thm vec_dot_self_is_distance(...)
...

# ✅ what-to-prove: write approach clearly in comments, main text directly writes facts that need to hold
# Approach: both sides |u×v|^2 * den' = ...; use |u|^2|v|^2-(u·v)^2 to substitute
angle_cos_num(a, b, c) = dot(vec(b, a), vec(b, c))
...
det(...) * det(...) * angle_cos_den(...) = ... = ...
```

When to use `by thm`:

- **Large theorems / non-trivial reasoning** (transitivity, auxiliary construction, contra conclusions), not simple expansion or elementary algebra
- Or when the same non-trivial step needs to be reused many times

Motto: **Source code writes what to prove; `by thm` is for large theorems. If you can write out a clear fact, write the fact.**

### 9.6 For every line you write, first ask: is the source for it established?

Before outputting each Litex fact, think clearly about **why this statement holds**:

1. **What is the source**: Definition expansion? Known premise? Equation already written earlier? Some `by thm` / Builtin shape?
2. **Is the source already in context**: In the library, in the premises, or already written earlier in this proof
3. **If source isn't there yet**: Write/prove the source first, then write this line; don't skip a step on intuition

Motto: **Source first, then conclusion.** If verifier gets stuck on `atomic fact unknown` / `chain fact unknown`, it's usually because the source for some line wasn't laid out properly.

## 10. Building LitexGeo from Scratch: Three Minimal Concepts

Library construction order: **Base functions → Relational predicates → Geometric predicates**. All subsequent concepts like perpendicularity, congruence, and parallelism build on these three layers.

### 10.1 Base: vec and dot

Points are coordinate pairs; `vec` transforms two points into a vector; `dot` transforms vectors into scalars. Same layer also has `det` (for collinearity).

```litex
have points set = cart(R, R)

have fn vec(A, B cart(R, R)) cart(R, R) = (B(1) - A(1), B(2) - A(2))
have fn dot(u, v cart(R, R)) R = u(1) * v(1) + u(2) * v(2)
have fn det(u, v cart(R, R)) R = u(1) * v(2) - u(2) * v(1)
```

### 10.2 Relations: is_collinear

Geometric meaning: three points are collinear. Use determinant equals zero, can be expanded and verified.

```litex
prop is_collinear(p, q, r cart(R, R)):
    det(vec(p, q), vec(p, r)) = 0
```

### 10.3 Geometric predicates: is_midpoint

Even with collinearity, don't pile up complexity; for midpoint use coordinate average (see 9.2).

```litex
prop is_midpoint(p, a, b cart(R, R)):
    p(1) = (a(1) + b(1)) / 2
    p(2) = (a(2) + b(2)) / 2
```

### 10.4 Summary

| Concept | Form | Dependencies | Unlocks |
|------|------|------|------|
| `vec` / `dot` (+`det`) | `have fn` | Coordinates | Length, perpendicularity, collinearity computations |
| `is_collinear` | `prop` | `vec`,`det` | Positional relationships |
| `is_midpoint` | `prop` | Coordinates | Midpoint-related theorems |

## 11. Common Builtin Shapes (Quick Reference)

Builtin is **not** `by builtin xxx`. You write facts matching the shape, and the verifier matches them automatically. When stuck, prioritize **rewriting the shape**.

### Algebra and Equation Chains

| Shape | How to Write |
|------|------|
| Polynomial identity | `(x+1)*(x-1) = x^2 - 1` |
| Difference | `a = b` ⇒ `a - b = 0`; `a - b != 0` ⇒ `a != b` |

### Squares and Positivity (most common in geometry)

| Shape | How to Write |
|------|------|
| Square non-negative | `0 <= x^2` (`x * x` also often recognized, prefer `^2`) |
| Base non-zero ⇒ square positive | Given `x != 0` ⇒ `0 < x^2` |
| Sum of squares non-zero | Given `a != 0` ⇒ `a^2 + b^2 != 0` |
| Sum of squares zero | `a^2 + b^2 = 0` ⇒ `a = 0`, `b = 0` |

Motto: For positivity, first expand to `dx^2 + dy^2`; **don't** write `=` and `>` in the same chain.

### Products and Elimination

| Shape | How to Write |
|------|------|
| Product zero | `a * b = 0` and `a != 0` ⇒ `b = 0` |
| Product non-zero | `a != 0`, `b != 0` ⇒ `a * b != 0` |
| Division to multiplication | `a / b = c` and `b != 0` ⇒ `a = c * b` |

### Order and Coordinates

| Shape | How to Write |
|------|------|
| Weaken | `a < b` ⇒ `a <= b` |
| Non-negative sum | `0 <= a`, `0 <= b` ⇒ `0 <= a + b` |
| Components ⇒ point equality | `a(1) = b(1)`, `a(2) = b(2)` ⇒ `a = b` |
