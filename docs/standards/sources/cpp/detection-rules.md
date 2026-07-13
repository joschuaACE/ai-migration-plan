# C++ Detection Rules

Reference material for identifying build systems, output types, language standard, dependencies,
and platform conditionals in a C++ source tree.

Begin from the deterministic `scope.json.source_snapshot`, not an extension-only search. Reconcile
every snapshotted path with stable source inventory or an exception-backed excluded-file record.
Build metadata and compilation databases refine classification and reachability; they do not
silently remove files from the declared denominator. Unknown or unclassified paths block the
discovery transition.

---

## Build System Detection

Scan project root and subdirectories for these sentinel files:

| Sentinel File | Build System | Key Indicators |
|---------------|-------------|----------------|
| `CMakeLists.txt` | CMake | `find_package()`, `target_link_libraries()`, `FetchContent_Declare()`, `cmake_minimum_required()` |
| `Makefile` / `GNUmakefile` | Make | `-l` flags in LDFLAGS/LIBS, `$(CXX)`, compiler flags |
| `*.vcxproj` / `*.sln` | MSBuild / Visual Studio | XML project definitions, `<ClCompile>`, `<Link>` |
| `meson.build` | Meson | `project()`, `dependency()`, `executable()`, `library()` |
| `BUILD` / `WORKSPACE` | Bazel | `cc_library`, `cc_binary`, `cc_test` |
| `conanfile.txt` / `conanfile.py` | Conan | `[requires]` section, `self.requires()` |
| `vcpkg.json` | vcpkg | `"dependencies"` array, `"name"`, `"version-semver"` |
| `configure.ac` / `configure` | Autotools | `AC_INIT`, `AM_INIT_AUTOMAKE`, `AC_CHECK_LIB` |

Do not assign a universal priority when several systems are present. Determine which files
the supported release/CI process actually invokes, and record wrappers, generators, and
package managers as part of that build graph. A checked-in system may be obsolete, while a
Makefile may be the supported entry point into another generator.

Prefer a per-configuration compilation database (`compile_commands.json`) when available.
It captures the compiler, flags, definitions, include paths, generated directories, and
translation units more reliably than source-tree heuristics. Preserve separate debug,
release, platform, architecture, and feature variants until their semantics are compared.

---

## Output Type Detection

Determine what the build produces by inspecting build targets:

### CMake

| Signal | Output Type |
|--------|-------------|
| `add_library(name SHARED ...)` | Library (shared) |
| `add_library(name STATIC ...)` | Library (static) |
| `add_library(name MODULE ...)` | Plugin/module |
| `add_executable(name ...)` | Executable |
| `install(TARGETS ... EXPORT ...)` + public headers | SDK |

### Makefile

| Signal | Output Type |
|--------|-------------|
| `-shared` flag, `.so`/`.dll`/`.dylib`/`.a` target | Library |
| Linked binary target (no `-shared`) | Executable |

### MSBuild

| Signal | Output Type |
|--------|-------------|
| `<ConfigurationType>DynamicLibrary</ConfigurationType>` | Library (shared) |
| `<ConfigurationType>StaticLibrary</ConfigurationType>` | Library (static) |
| `<ConfigurationType>Application</ConfigurationType>` | Executable |

### Meson

| Signal | Output Type |
|--------|-------------|
| `shared_library()` / `static_library()` / `both_libraries()` | Library |
| `executable()` | Executable |

### Bazel

| Signal | Output Type |
|--------|-------------|
| `cc_library` | Library |
| `cc_binary` | Executable |

### Classification Logic

| Condition | Classification |
|-----------|---------------|
| Primary target is library + public headers installed/exported | **sdk** |
| Primary target is library, built only as internal dependency | **library** |
| Executable + network/server code (listen, accept, bind, serve) | **service** |
| Executable + arg parsing (getopt, getopt_long, CLI11, cxxopts, boost::program_options) | **cli** |
| Mixed (executable + library targets) | Record every releasable artifact; select an output profile per artifact or an approved composite plan |

---

## Language Version Detection

### From Compiler Flags

Search build files for explicit standard flags:

| Flag | Standard |
|------|----------|
| `-std=c++11` / `-std=c++0x` | C++11 |
| `-std=c++14` / `-std=c++1y` | C++14 |
| `-std=c++17` / `-std=c++1z` | C++17 |
| `-std=c++20` / `-std=c++2a` | C++20 |
| `-std=c++23` / `-std=c++2b` | C++23 |
| `/std:c++14` through `/std:c++latest` | MSVC equivalents |

CMake: `set(CMAKE_CXX_STANDARD 17)` or `target_compile_features(name PUBLIC cxx_std_17)`

### From Feature Usage Signals

When compiler flags are absent, infer the minimum standard from code features:

**C++11:** `auto`, `nullptr`, range-for, lambdas, `<thread>`, `<mutex>`, `<atomic>`,
`std::unique_ptr`, `std::shared_ptr`, move semantics (`&&`, `std::move`), `enum class`,
`override`/`final`, variadic templates.

**C++14:** Generic lambdas (`auto` parameters), `std::make_unique`, return type deduction,
binary literals (`0b1010`), `[[deprecated]]`.

**C++17:** `std::optional`, `std::variant`, `std::any`, structured bindings (`auto [x, y] = ...`),
`if constexpr`, `<filesystem>`, `std::string_view`, fold expressions, CTAD,
`[[nodiscard]]`/`[[maybe_unused]]`/`[[fallthrough]]`, inline variables, nested namespaces.

**C++20:** Concepts (`requires`, `concept`), ranges (`std::ranges::`, `std::views::`),
coroutines (`co_await`, `co_yield`, `co_return`), `std::format`, modules (`import`, `export module`),
three-way comparison (`<=>`), `consteval`/`constinit`, `<span>`, designated initializers.

**C++23:** `std::expected`, `std::print`/`std::println`, deducing `this`,
`std::flat_map`/`std::flat_set`, `std::generator`, `[[assume]]`, `std::stacktrace`.

---

## Dependency Category Detection

### Detection Sources

1. **Build files:** `find_package()`, `target_link_libraries()`, `FetchContent`, `-l` flags
2. **Package managers:** Conan `[requires]`, vcpkg `"dependencies"`
3. **Include directives:** `grep -rh '#include' --include='*.cpp' --include='*.h' --include='*.hpp'`

### Categories and Signals

#### Networking

| Signal | Library |
|--------|---------|
| `#include <boost/asio.hpp>` / `boost::asio` | Boost.Asio |
| `#include <boost/beast.hpp>` | Boost.Beast (HTTP/WebSocket) |
| `#include <sys/socket.h>` / `<winsock2.h>` | Raw sockets (POSIX/Win32) |
| `#include <curl/curl.h>` / `-lcurl` | libcurl |
| `#include <grpcpp/grpcpp.h>` / `grpc++` | gRPC |
| `#include <httplib.h>` | cpp-httplib |
| `#include <cpprest/http_client.h>` | C++ REST SDK (Casablanca) |
| `#include <Poco/Net/*>` | POCO Networking |

#### Database

| Signal | Library |
|--------|---------|
| `#include <mysql.h>` / `#include <mysql/mysql.h>` | MySQL C Connector |
| `#include <libpq-fe.h>` / `-lpq` | PostgreSQL (libpq) |
| `#include <sqlite3.h>` / `-lsqlite3` | SQLite |
| `#include <sql.h>` / `#include <sqlext.h>` | ODBC |
| `#include <mongocxx/*>` / `#include <bsoncxx/*>` | MongoDB C++ Driver |
| `#include <hiredis/hiredis.h>` | Redis (hiredis) |

#### Serialization

| Signal | Library |
|--------|---------|
| `#include <google/protobuf/*>` / `.proto` files | Protocol Buffers |
| `#include <nlohmann/json.hpp>` | nlohmann/json |
| `#include <rapidjson/*>` | RapidJSON |
| `#include <flatbuffers/*>` / `.fbs` files | FlatBuffers |
| `#include <pugixml.hpp>` | pugixml |
| `#include <tinyxml2.h>` | TinyXML-2 |
| `#include <yaml-cpp/yaml.h>` | yaml-cpp |
| `#include <msgpack.hpp>` | MessagePack |
| `#include <boost/serialization/*>` | Boost.Serialization |

#### GUI

| Signal | Library |
|--------|---------|
| `#include <Q*>` / `#include <Qt*/*>` / `.ui` files | Qt |
| `#include <wx/*>` | wxWidgets |
| `#include <gtk/*>` / `#include <gtkmm/*>` | GTK / gtkmm |
| `#include <FL/*>` | FLTK |
| `#include "imgui.h"` | Dear ImGui |
| `#include <afxwin.h>` / MFC headers | MFC |

#### Threading / Concurrency

| Signal | Library |
|--------|---------|
| `#include <thread>` / `#include <mutex>` / `#include <future>` | C++ Standard Threading |
| `#include <pthread.h>` / `-lpthread` | POSIX Threads |
| `#pragma omp` / `-fopenmp` | OpenMP |
| `#include <tbb/*>` / `tbb::` | Intel TBB (oneTBB) |
| `#include <boost/thread.hpp>` | Boost.Thread |

#### Testing

| Signal | Library |
|--------|---------|
| `#include <gtest/gtest.h>` / `#include <gmock/gmock.h>` | Google Test / Mock |
| `#include <catch2/*>` / `#include "catch.hpp"` | Catch2 |
| `#include <doctest/doctest.h>` / `#include "doctest.h"` | doctest |
| `#include <boost/test/*>` | Boost.Test |
| `#include <cppunit/*>` | CppUnit |

#### Logging

| Signal | Library |
|--------|---------|
| `#include <spdlog/*>` / `spdlog::` | spdlog |
| `#include <log4cxx/*>` | log4cxx |
| `#include <glog/logging.h>` | Google Logging (glog) |
| `#include <boost/log/*>` | Boost.Log |
| `#include <plog/*>` | plog |

#### Cryptography

| Signal | Library |
|--------|---------|
| `#include <openssl/*>` / `-lssl` / `-lcrypto` | OpenSSL |
| `#include <sodium.h>` / `-lsodium` | libsodium |
| `#include <botan/*>` | Botan |
| `#include <cryptopp/*>` / `#include <crypto++/*>` | Crypto++ |

#### Memory Management

| Signal | Library |
|--------|---------|
| `#include <jemalloc/jemalloc.h>` / `-ljemalloc` | jemalloc |
| `#include <gperftools/tcmalloc.h>` / `-ltcmalloc` | tcmalloc |
| Custom pool allocators, arena patterns | Project-specific |

#### IPC / Messaging

| Signal | Library |
|--------|---------|
| `#include <zmq.hpp>` / `#include <zmq.h>` / `-lzmq` | ZeroMQ |
| `#include <boost/interprocess/*>` | Boost.Interprocess |
| `#include <dbus/*>` | D-Bus |
| `#include <amqp.h>` / `#include <amqpcpp/*>` | RabbitMQ / AMQP |

#### Math / Science / Numerics

| Signal | Library |
|--------|---------|
| `#include <Eigen/*>` | Eigen |
| `#include <opencv2/*>` | OpenCV |
| `#include <cblas.h>` / `#include <lapacke.h>` | BLAS/LAPACK |
| `#include <fftw3.h>` | FFTW |
| `#include <boost/math/*>` | Boost.Math |
| `#include <armadillo>` | Armadillo |

#### Compression

| Signal | Library |
|--------|---------|
| `#include <zlib.h>` / `-lz` | zlib |
| `#include <lz4.h>` / `-llz4` | LZ4 |
| `#include <zstd.h>` / `-lzstd` | Zstandard |
| `#include <snappy.h>` / `-lsnappy` | Snappy |
| `#include <bzlib.h>` / `-lbz2` | bzip2 |

#### Platform APIs

| Signal | Library |
|--------|---------|
| `#include <windows.h>` / Win32 API calls | Windows API |
| `#include <unistd.h>` / `<sys/*>` | POSIX |
| `#include <CoreFoundation/*>` / `<Cocoa/*>` | macOS Frameworks |

---

## Include Classification

When scanning `#include` directives, classify each into:

| Category | Examples | Required inventory follow-up |
|----------|----------|----------------------|
| Standard library | `<iostream>`, `<vector>`, `<algorithm>`, `<memory>` | Record used semantics; pair evaluation chooses any target mapping |
| Platform | `<windows.h>`, `<unistd.h>`, `<sys/socket.h>` | Record platform, ABI, behavior, and portable fallback |
| Third-party | `<boost/*>`, `<spdlog/*>`, `"nlohmann/json.hpp"` | Link to dependency/version/capability inventory |
| Project-internal | `"src/core/engine.h"`, `"../utils.h"` | Link the resolved source unit and build variant |

---

## Platform Conditional Detection

Scan for preprocessor platform checks:

### Windows

```cpp
#ifdef _WIN32          // 32-bit and 64-bit Windows
#ifdef _WIN64          // 64-bit Windows only
#ifdef _MSC_VER        // Microsoft Visual C++ compiler
#ifdef __MINGW32__     // MinGW 32-bit
#ifdef __MINGW64__     // MinGW 64-bit
```

### Linux / Unix

```cpp
#ifdef __linux__       // Linux kernel
#ifdef __unix__        // Any Unix-like system
#ifdef __GLIBC__       // GNU C Library
#ifdef _POSIX_VERSION  // POSIX compliance
```

### macOS / Apple

```cpp
#ifdef __APPLE__       // Apple platforms
#ifdef __MACH__        // Mach kernel (macOS)
#ifdef TARGET_OS_MAC   // macOS specifically (requires TargetConditionals.h)
#ifdef TARGET_OS_IPHONE // iOS
```

### Android

```cpp
#ifdef __ANDROID__     // Android NDK
```

### Compiler-Specific

```cpp
#ifdef __GNUC__        // GCC or compatible
#ifdef __clang__       // Clang
#ifdef _MSC_VER        // MSVC (also used as platform indicator)
#ifdef __INTEL_COMPILER // Intel C++ Compiler
```

### Recording

For each platform conditional block, record:
- **File and line number**
- **Platform(s) targeted**
- **Functionality provided** (e.g., file I/O, networking, threading, GUI)
- **Size** (lines of platform-specific code)
- **Whether a portable fallback exists** (else/elif branch)

---

## Semantic Hazard Signals

Detection creates findings; it does not decide that a construct is safely portable. Scan
all reachable source and generated inputs for at least:

| Hazard | Signals |
|---|---|
| Undefined/implementation-dependent behavior | invalid shifts, signed overflow assumptions, uninitialized reads, aliasing/layout casts, plain `char`, bit fields, packed structs |
| Ownership and lifetime | raw owning pointers, custom deleters, borrowed views, placement `new`, arenas, destructor side effects, static destruction |
| Concurrency | relaxed atomics, fences, condition variables, lock ordering, detached threads, signal handlers, shared non-atomic state |
| Templates and macros | explicit/partial specializations, SFINAE/concepts, CRTP, token pasting, repeated macro evaluation, conditional declarations |
| ABI/native boundaries | exported symbols, `extern "C"`, calling-convention attributes, public layout, `dlopen`/`LoadLibrary`, function-pointer callbacks |
| Serialization and numeric behavior | raw-struct I/O, `reinterpret_cast` buffers, locale-sensitive parsing, float environment, endianness swaps, narrowing |
| Build variants | per-target definitions, generated headers, exception/RTTI toggles, optimization-specific paths, platform/compiler conditionals |

For classification, required evidence, and migration dispositions, apply
`semantic-hazards.md`. A grep match alone is neither proof of reachability nor a complete
analysis.
