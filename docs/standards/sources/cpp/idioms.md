# C++ Idioms and Patterns

C++ idioms and patterns that require special attention during source analysis. Each entry
describes what the idiom is, how to detect it in code, and what architectural concern
it raises for migration planning.

An idiom label is not a translation rule. Determine its intent, reachable instantiations,
ownership and error semantics, and build-variant behavior before selecting a target form.
Apply `semantic-hazards.md` whenever an idiom touches lifetime, object layout, evaluation
order, concurrency, ABI, or environment-dependent behavior.

---

## RAII (Resource Acquisition Is Initialization)

### What It Is

Resources (memory, file handles, locks, sockets, database connections) are tied to object
lifetime. The constructor acquires; the destructor releases. Guarantees cleanup even when
exceptions occur.

### Detection Signals

- Destructors (`~ClassName()`) that release resources (close, free, delete, unlock, release)
- Constructor bodies that open/allocate/acquire
- `std::lock_guard`, `std::unique_lock`, `std::scoped_lock`
- `std::unique_ptr`, `std::shared_ptr` with custom deleters
- Classes wrapping handles (file descriptors, HANDLE, socket fd)
- Patterns like `FileGuard`, `ScopeExit`, `AutoClose`

### Migration Concern

The target language may not have deterministic destruction. Resource release timing changes
from "end of scope" to "whenever GC runs." Every RAII class must be analyzed for whether
timing-sensitive cleanup is required (locks, flushes, connections) vs. memory-only cleanup.

---

## CRTP (Curiously Recurring Template Pattern)

### What It Is

A class derives from a template parameterized by itself: `class Derived : public Base<Derived>`.
Used for static polymorphism — compile-time dispatch without virtual function overhead.

### Detection Signals

- Template base class with derived class as template parameter
- Pattern: `class X : public Something<X>`
- Typically combined with `static_cast<Derived*>(this)` in the base
- Used in: expression templates, mixin injection, static interface enforcement

### Migration Concern

Combines inheritance with generics in a way most languages cannot express directly.
The intent must be decomposed: is it static dispatch (use composition/generics), mixin
behavior (use interfaces/default methods), or compile-time code generation (needs redesign)?
Each CRTP hierarchy requires individual architectural analysis.

---

## Pimpl (Pointer to Implementation)

### What It Is

A class holds a pointer to a private implementation class, hiding internals from the
public header. Reduces compile-time coupling and preserves ABI stability.

### Detection Signals

- Forward declaration of an `Impl` or `Private` class in the header
- `std::unique_ptr<Impl> pImpl;` or raw `Impl* impl;` member
- All method bodies in the .cpp file delegating to `pImpl->`
- Naming: `*Impl`, `*Private`, `*D`, `*Data`
- Header has no private data members except the pimpl pointer

### Migration Concern

Pimpl exists to solve C++ header/compilation problems that don't exist in most target
languages. The indirection is usually unnecessary after migration. However, the separation
may reveal a meaningful architectural boundary (public API vs. internal state) that should
be preserved differently.

---

## Copy-and-Swap Idiom

### What It Is

A technique for implementing exception-safe copy assignment by:
1. Taking the parameter by value (invokes copy constructor)
2. Swapping contents with the copy
3. Old state destroyed when the copy goes out of scope

### Detection Signals

- `operator=(ClassName other)` — parameter by value, not reference
- `swap()` member or friend function
- Often paired with a `friend void swap(ClassName&, ClassName&) noexcept`
- Assignment operator body is just `swap(*this, other); return *this;`

### Migration Concern

Implies the class has non-trivial resource ownership requiring careful copy semantics.
The underlying concern (deep copy of resources) must be analyzed — does the migrated type
need value semantics, reference semantics, or immutability?

---

## Rule of Five

### What It Is

If a class defines any of: destructor, copy constructor, copy assignment operator, move
constructor, or move assignment operator — it likely needs all five. Indicates the class
manages resources manually.

### Detection Signals

- Explicit `~ClassName()`
- Explicit `ClassName(const ClassName&)` (copy constructor)
- Explicit `ClassName(ClassName&&)` (move constructor)
- Explicit `operator=(const ClassName&)` (copy assignment)
- Explicit `operator=(ClassName&&)` (move assignment)
- `= delete` on any of the above (explicitly disabled operations)
- `= default` with custom destructor (partially defaulted)

### Migration Concern

Every Rule-of-Five class manages resources. The migration must determine: what resource,
what ownership model (unique, shared, weak), whether move semantics are performance-critical,
and whether the target language's memory model handles it automatically or needs explicit
lifecycle management.

---

## SFINAE / Tag Dispatch / Expression Templates

### What It Is

**SFINAE** (Substitution Failure Is Not An Error): Template overload resolution that silently
discards candidates whose type substitution fails. Used to enable/disable functions based on type traits.

**Tag Dispatch:** Using empty structs as type tags to select function overloads at compile time.

**Expression Templates:** Template-heavy technique that builds an expression tree as a type at
compile time, evaluated lazily. Common in math libraries (Eigen, Blaze).

### Detection Signals

- SFINAE: `std::enable_if`, `std::void_t`, `decltype(...)` in return types or template params,
  trailing return types with `decltype`, `if constexpr` (C++17 replacement)
- Tag dispatch: Empty structs (`struct input_iterator_tag {}`), function overloads taking tag params
- Expression templates: Deeply nested template types, operator overloading returning proxy objects,
  `template<typename Expr>` parameters in arithmetic, lazy evaluation patterns

### Migration Concern

These are compile-time metaprogramming techniques with no direct equivalent in most
languages. The *intent* must be recovered: conditional API availability (use overloading/generics),
performance optimization (profile whether it matters), or type-level computation (simplify
or use code generation). Expression templates may indicate performance-critical numeric
code requiring specialized handling.

---

## Template Metaprogramming

### What It Is

Using the template system as a compile-time computation engine: type lists, compile-time
conditionals, recursive template instantiation, constexpr functions, and type traits.

### Detection Signals

- Recursive template specializations
- `template<typename... Args>` (variadic templates)
- `std::tuple`, `std::index_sequence`, parameter packs
- `constexpr` functions doing complex computation
- Type traits usage: `std::is_same`, `std::decay`, `std::conditional`
- Template template parameters: `template<template<typename> class Container>`
- Heavy use of `<type_traits>` header

### Migration Concern

Template metaprogramming generates specialized code at compile time. The migrated code
must achieve the same behavior through the target's generics, code generation, or runtime
polymorphism. Compile-time guarantees may become runtime checks. Performance characteristics
may change significantly if specialization is eliminated.

---

## Multiple Inheritance

### What It Is

A class inherits from more than one base class. C++ supports full multiple inheritance
including diamond inheritance (resolved with virtual inheritance).

### Detection Signals

- `class Derived : public Base1, public Base2`
- Virtual inheritance: `class Derived : virtual public Base`
- Diamond patterns: multiple paths to same ancestor
- Mixin-style classes (small, focused bases providing specific behavior)

### Migration Concern

Most target languages support only single class inheritance. Each multiple inheritance
use must be decomposed: interface extraction (pure virtual bases → interfaces), mixin
decomposition (behavioral bases → composition or default interface methods), and diamond
resolution (virtual bases → explicit delegation). The disambiguation logic (`Base1::method`
vs `Base2::method`) must be preserved.

---

## Operator Overloading

### What It Is

Custom behavior for operators (`+`, `-`, `*`, `[]`, `()`, `<<`, `==`, `<`, etc.)
allowing user-defined types to work with built-in syntax.

### Detection Signals

- `operator+`, `operator-`, `operator*`, `operator/` (arithmetic)
- `operator==`, `operator!=`, `operator<`, `operator<=>` (comparison)
- `operator[]` (subscript)
- `operator()` (function call — functors)
- `operator<<`, `operator>>` (stream I/O or bitshift)
- `operator*`, `operator->` (dereference — smart pointers/iterators)
- `operator Type()` (implicit/explicit conversion)
- Free-standing operator functions (non-member)

### Migration Concern

Most target languages have limited or no operator overloading. Each overloaded operator
must be converted to a named method. The concern is API ergonomics: code that reads
naturally with operators (`matrix * vector`, `stream << obj`) becomes verbose with
method calls. Also, implicit conversions (`operator bool()`, `operator int()`) may hide
logic that becomes explicit and changes call sites.

---

## Friend Functions

### What It Is

Functions or classes declared as `friend` can access private/protected members of the
granting class, bypassing encapsulation.

### Detection Signals

- `friend class ClassName;`
- `friend void functionName(args);`
- `friend std::ostream& operator<<(std::ostream&, const ClassName&);`
- Commonly used with operator overloading, factory patterns, serialization

### Migration Concern

Friend access violates encapsulation boundaries. The migration must determine why the
friendship exists: testing access (use test-specific accessors), operator overloading
(becomes methods anyway), factory creation (constructor access), or tight coupling
between classes (redesign relationship). Each friend declaration reveals a coupling
relationship that must be made explicit in the target architecture.

---

## Global and Static State

### What It Is

State that persists across function calls and has program-wide visibility: global variables,
static class members, static local variables (Meyer's singleton), and namespace-scope objects.

### Detection Signals

- Global variables in `.cpp` files or `extern` declarations in headers
- `static` class members (data)
- `static` local variables (particularly in functions returning references — singletons)
- Namespace-scope objects with constructors (static initialization order fiasco risk)
- `std::once_flag` / `std::call_once` patterns
- Thread-local storage: `thread_local`

### Migration Concern

Global/static state creates hidden dependencies, complicates testing, causes initialization
ordering issues, and makes concurrent access dangerous. The migration must catalog all
global state, determine its scope (truly global vs. application-scoped vs. thread-scoped),
and plan explicit lifecycle management. Static initialization order between translation
units is a known C++ hazard that should not be replicated.

---

## Manual Memory Management

### What It Is

Direct control of heap allocation and deallocation: `new`/`delete`, `malloc`/`free`,
placement new, custom allocators, and memory pools. Also includes smart pointers that
encode ownership semantics.

### Detection Signals

- **Raw management:** `new`, `delete`, `new[]`, `delete[]`, `malloc`, `free`, `realloc`
- **Smart pointers:** `std::unique_ptr` (unique ownership), `std::shared_ptr` (shared ownership),
  `std::weak_ptr` (non-owning observer)
- **Custom allocators:** Classes with `allocate()`/`deallocate()` methods, `std::allocator` specializations
- **Placement new:** `new (ptr) Type(args)` — constructing in pre-allocated memory
- **Memory pools / arenas:** Fixed-size block allocators, bump allocators, slab allocators
- **Intrusive containers:** Objects containing `next`/`prev` pointers for list membership

### Migration Concern

Memory management is the largest semantic gap between C++ and garbage-collected languages.
Raw `new`/`delete` usually maps to simple object creation. Smart pointer ownership graphs
(`unique_ptr` trees, `shared_ptr` cycles) encode architectural relationships that must be
preserved logically. Custom allocators exist for performance — the migration must determine
if the target's memory model provides adequate performance or if pooling/caching patterns
are still needed. Weak references may need explicit handling to avoid leaks in cyclic structures.
