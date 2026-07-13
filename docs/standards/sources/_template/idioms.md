# [LANGUAGE_NAME] Idioms and Semantic Hazards

Describe source-language intent and detection. Do not include target-language code or a
canonical translation; target candidates belong to pair profiles.

## Idiom Record

For every important idiom use:

### [IDIOM NAME]

**Intent:** What problem the idiom solves in [LANGUAGE_NAME].

**Detection:** Syntax, APIs, build flags, generated code, and caller patterns.

**Semantics:** Ownership/lifetime, errors, concurrency, evaluation order, type/numeric,
serialization, ABI, and performance guarantees that may be observable.

**Variants:** Language/toolchain/platform versions and common alternative forms.

**Hazards:** Undefined, unspecified, implementation-defined, environment-dependent, or
commonly misunderstood behavior.

**Evidence:** Source locations, build variants, tests/analysis needed to characterize it.

## Required Areas

- allocation, ownership, borrowing, resource lifetime, and cleanup;
- errors, exceptions/results, cancellation, and partial effects;
- threading/async, synchronization, memory model, and shutdown;
- type system, generics/metaprogramming, reflection, and generated code;
- values, numeric conversion/overflow, equality/hash/order, and collections;
- text/bytes, encoding/locale/time/filesystem, and serialization;
- modules/packages/public API, ABI/FFI/plugins, and platform conditionals; and
- global/static state, initialization/destruction, callbacks, and side effects.

## Disposition Inputs

For each reachable occurrence capture stable finding IDs, callers/consumers, affected
behavior IDs, evidence confidence, and whether a pair must preserve, normalize, remove,
defer, or block the behavior. The source profile records facts; it does not choose the
target disposition alone.
