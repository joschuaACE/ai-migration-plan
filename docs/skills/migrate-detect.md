# migrate-detect

Detect C++ technologies, libraries, patterns, and platform dependencies in the source tree — produces a comprehensive technology inventory with Java migration paths.

## When to Use

- During migrate-init (called automatically as part of initialization)
- When new source files are discovered and the tech inventory needs updating
- With --refresh to update legacy-stack.md after codebase changes

## Inputs

- **Path to scan** (optional) — defaults to source_root from .migration/config.json
- **--deep flag** (optional) — also analyze function-level usage patterns (slower, more thorough)
- **--refresh flag** (optional) — update existing legacy-stack.md rather than overwrite

## Procedure

### Step 1: Build System Detection

Scan project root and subdirectories for:
- `CMakeLists.txt` → CMake (extract version, targets, find_package calls)
- `Makefile` / `GNUmakefile` → Make (extract compiler flags, link libs)
- `*.vcxproj` / `*.sln` → MSBuild/Visual Studio
- `meson.build` → Meson
- `BUILD` / `WORKSPACE` → Bazel
- `conanfile.txt` / `conanfile.py` → Conan package manager
- `vcpkg.json` → vcpkg package manager
- `configure.ac` / `configure` → Autotools

Record: build system name, version (if detectable), configuration mode.

### Step 2: Output Type Detection

Determine what the C++ build produces:

| Build System | Library Signal | Executable Signal |
|-------------|---------------|-------------------|
| CMake | `add_library(SHARED|STATIC|MODULE)` | `add_executable()` |
| Makefile | `-shared` flag, `.so`/`.dll`/`.a` target | Linked executable target |
| MSBuild | `<ConfigurationType>DynamicLibrary|StaticLibrary</ConfigurationType>` | `<ConfigurationType>Application</ConfigurationType>` |
| Meson | `shared_library()` / `static_library()` | `executable()` |
| Bazel | `cc_library` | `cc_binary` |

**Classification logic:**
- If primary target is `add_library` → likely `library` or `sdk`
  - If public headers are installed/exported → likely `sdk`
  - If just built as dependency → likely `library`
- If primary target is `add_executable` with network/server code → `service`
- If primary target is `add_executable` with arg parsing (getopt, CLI11, cxxopts) → `cli`
- If mixed (executable + library targets) → note both, ask user during init

Record detected output type in legacy-stack.md under a '## Detected Output Type' section.

### Step 3: Package/Dependency Detection

From build files, extract declared dependencies:
- CMake: `find_package()`, `target_link_libraries()`, `FetchContent_Declare()`
- Conan: `[requires]` section
- vcpkg: `"dependencies"` array
- Makefile: `-l` flags in LDFLAGS/LIBS

For each dependency found, classify:

| Category | Detection Signal |
|----------|-----------------|
| Networking | boost::asio, socket.h, curl, grpc++, cpp-httplib |
| Database | mysql.h, libpq, sqlite3.h, ODBC headers, mongocxx |
| Serialization | protobuf, nlohmann/json, rapidjson, pugixml, tinyxml2 |
| GUI | Qt headers, wxWidgets, MFC, GTK, FLTK, ImGui |
| Threading | \<thread\>, \<mutex\>, pthread, OpenMP, TBB |
| Testing | gtest, catch2, doctest, boost/test, CppUnit |
| Logging | spdlog, log4cxx, boost/log, glog, plog |
| Crypto | openssl, libsodium, botan, crypto++ |
| Memory | jemalloc, tcmalloc, custom pool headers |
| IPC | ZeroMQ, shared_memory, message_queue, D-Bus |
| Math/Science | Eigen, OpenCV, BLAS/LAPACK, FFTW, Boost.Math |
| Compression | zlib, lz4, zstd, snappy, bzip2 |
| Platform | Win32 API, POSIX, macOS frameworks |

### Step 4: Include Directive Analysis

Scan ALL .cpp/.h/.hpp files for #include directives:
```bash
grep -rh '#include' --include='*.cpp' --include='*.h' --include='*.hpp' | sort | uniq -c | sort -rn
```

Classify each unique include:
- **Standard library** (no migration needed): \<iostream\>, \<vector\>, \<algorithm\>
- **Platform** (needs abstraction): \<windows.h\>, \<unistd.h\>, \<sys/*\>
- **Third-party** (needs Java equivalent): "boost/*", "spdlog/*"
- **Project-internal** (migrates with the code): "src/core/*"

### Step 5: C++ Standard Detection

From compiler flags and code patterns:
- `-std=c++11/14/17/20/23` in build files
- `__cplusplus` macro checks
- Feature usage signals:
  - C++11: auto, nullptr, range-for, lambdas, \<thread\>
  - C++14: generic lambdas, make_unique
  - C++17: std::optional, structured bindings, if constexpr, \<filesystem\>
  - C++20: concepts, ranges, co_await, \<format\>, modules
  - C++23: std::expected, std::print, deducing this

### Step 6: Platform Conditional Detection

Scan for preprocessor platform checks:
```
#ifdef _WIN32 / _MSC_VER / __MINGW32__
#ifdef __linux__ / __unix__
#ifdef __APPLE__ / __MACH__
#ifdef __ANDROID__
```

For each platform block, record:
- Location (file:line)
- Platform(s) targeted
- Functionality provided
- Migration strategy: @Profile / abstraction / eliminate

### Step 7: Produce Output Documents

**legacy-stack.md format:**
```markdown
# Legacy Technology Stack

## Build System
- **CMake 3.21** — project configuration and build

## C++ Standard
- **C++17** — detected from `-std=c++17` flag and std::optional usage

## Detected Output Type
- **Build produces:** <library|executable|both>
- **Confidence:** <high|medium|low>
- **Signals:** <what was detected>
- **Suggested output_type:** <service|library|sdk|cli>

## Dependencies (by category)

### Networking
| Library | Version | Usage Count | Migration Difficulty | Java Equivalent |
|---------|---------|-------------|---------------------|-----------------|
| Boost.Asio | 1.82 | 23 files | 3/5 | Spring WebFlux / Virtual threads |

## Platform Dependencies
| Platform | Files | Migration Strategy |
|----------|-------|-------------------|
| Windows (Win32 API) | 12 | Spring profiles + abstraction |

## Summary
- Total third-party dependencies: N
- High-risk (no direct Java equivalent): M
- Platform-locked code: P files
```

**dependency-map.md format:**
```markdown
# Dependency Migration Map

| C++ Library | Java Equivalent | Confidence | Notes |
|-------------|----------------|-----------|-------|
| Boost.Asio | java.net.http + virtual threads | High | Async I/O patterns map well |
| spdlog | SLF4J + Logback | High | Direct equivalent |
| nlohmann/json | Jackson (auto-configured) | High | Spring Boot default |
| protobuf | protobuf-java + grpc-java | High | Same protocol, Java codegen |
| OpenSSL | Java Security API + BouncyCastle | Medium | API differences |
```

**risk-matrix.md format:**
```markdown
# Migration Risk Matrix

| Risk | Impact (1-5) | Likelihood (1-5) | Score | Mitigation |
|------|:---:|:---:|:---:|------------|
| Platform-specific code breaks on translation | 4 | 3 | 12 | Abstract behind ports, test with profiles |
| Template metaprogramming hard to express in Java | 3 | 2 | 6 | Strategy pattern + generics |
| Performance regression (GC vs manual memory) | 3 | 3 | 9 | Benchmark critical paths, tune GC |
```

## Outputs

- `.migration/research/legacy-stack.md` — technology inventory with migration paths
- `.migration/research/dependency-map.md` — per-dependency migration strategy
- `.migration/research/risk-matrix.md` — risks ranked by impact × likelihood

## Success Criteria

- Build system correctly identified
- C++ standard version detected
- All third-party dependencies cataloged with usage counts
- Each dependency has a Java migration path (or marked "no equivalent")
- Platform-specific code blocks identified with file locations
- Risk matrix populated and ordered by score
- legacy-stack.md, dependency-map.md, risk-matrix.md all written
