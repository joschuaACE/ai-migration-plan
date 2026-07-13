# C++ Dependency Catalog

Known C++ libraries — what they are, how to detect them, and what they provide.
Used during source analysis to identify the technology surface of a C++ codebase.

---

## Boost

Meta-library providing foundational utilities across many domains. Components are
individually usable.

### Boost.Asio

| Field | Value |
|-------|-------|
| Category | Networking / Async I/O |
| Detection | `#include <boost/asio.hpp>`, `boost::asio::`, CMake `Boost::asio` |
| Provides | Asynchronous I/O, TCP/UDP sockets, timers, strand-based concurrency, SSL streams |

### Boost.Beast

| Field | Value |
|-------|-------|
| Category | Networking (HTTP/WebSocket) |
| Detection | `#include <boost/beast.hpp>`, `boost::beast::`, built on Asio |
| Provides | HTTP/1.1 and WebSocket protocol implementations over Asio |

### Boost.Filesystem

| Field | Value |
|-------|-------|
| Category | File system |
| Detection | `#include <boost/filesystem.hpp>`, `boost::filesystem::`, `-lboost_filesystem` |
| Provides | Path manipulation, directory iteration, file operations. Superseded by `<filesystem>` in C++17 |

### Boost.Log

| Field | Value |
|-------|-------|
| Category | Logging |
| Detection | `#include <boost/log/*>`, `boost::log::`, `-lboost_log` |
| Provides | Structured logging, sinks, formatters, filters, severity levels |

### Boost.Test

| Field | Value |
|-------|-------|
| Category | Testing |
| Detection | `#include <boost/test/*>`, `BOOST_AUTO_TEST_CASE`, `-lboost_unit_test_framework` |
| Provides | Unit testing framework with fixtures, parameterized tests, assertions |

### Boost.Math

| Field | Value |
|-------|-------|
| Category | Numerics |
| Detection | `#include <boost/math/*>`, `boost::math::` |
| Provides | Special functions, statistical distributions, numeric utilities |

### Boost.Serialization

| Field | Value |
|-------|-------|
| Category | Serialization |
| Detection | `#include <boost/serialization/*>`, `#include <boost/archive/*>` |
| Provides | Object serialization to/from binary, XML, text archives |

### Boost.Thread

| Field | Value |
|-------|-------|
| Category | Threading |
| Detection | `#include <boost/thread.hpp>`, `-lboost_thread` |
| Provides | Thread management, mutexes, condition variables. Largely superseded by C++11 `<thread>` |

### Boost.Program_options

| Field | Value |
|-------|-------|
| Category | CLI argument parsing |
| Detection | `#include <boost/program_options.hpp>`, `boost::program_options::`, `-lboost_program_options` |
| Provides | Command-line and config file option parsing |

### Boost.Interprocess

| Field | Value |
|-------|-------|
| Category | IPC |
| Detection | `#include <boost/interprocess/*>`, `boost::interprocess::` |
| Provides | Shared memory, memory-mapped files, named mutexes, message queues |

---

## GUI Frameworks

### Qt

| Field | Value |
|-------|-------|
| Category | GUI / Application framework |
| Detection | `#include <Q*>`, `#include <Qt*/*>`, `.ui` files, `.pro`/`CMakeLists.txt` with Qt, `moc_*.cpp`, `Q_OBJECT` macro |
| Provides | Cross-platform GUI, signals/slots, networking, SQL, multimedia, widgets, QML |

### wxWidgets

| Field | Value |
|-------|-------|
| Category | GUI |
| Detection | `#include <wx/*>`, `wx*` class prefixes, `-lwx*` link flags |
| Provides | Cross-platform native-look GUI widgets, event system |

### GTK / gtkmm

| Field | Value |
|-------|-------|
| Category | GUI |
| Detection | `#include <gtk/gtk.h>` (C), `#include <gtkmm.h>` (C++), `pkg-config gtk*` |
| Provides | Cross-platform GUI toolkit, GObject type system (C), C++ bindings (gtkmm) |

### FLTK

| Field | Value |
|-------|-------|
| Category | GUI |
| Detection | `#include <FL/*>`, `Fl_*` class prefixes, `-lfltk` |
| Provides | Lightweight cross-platform GUI, small binary size |

### Dear ImGui

| Field | Value |
|-------|-------|
| Category | GUI (immediate mode) |
| Detection | `#include "imgui.h"`, `ImGui::` namespace, source files `imgui.cpp`, `imgui_draw.cpp` |
| Provides | Immediate-mode GUI for tools/debug interfaces, renderer-agnostic |

---

## Cryptography

### OpenSSL

| Field | Value |
|-------|-------|
| Category | Cryptography / TLS |
| Detection | `#include <openssl/*>`, `-lssl`, `-lcrypto`, CMake `find_package(OpenSSL)` |
| Provides | TLS/SSL, symmetric/asymmetric encryption, hashing, X.509, PKCS |

### libsodium

| Field | Value |
|-------|-------|
| Category | Cryptography |
| Detection | `#include <sodium.h>`, `-lsodium`, CMake `find_package(sodium)` |
| Provides | Modern crypto: authenticated encryption, key exchange, hashing, signatures |

### Botan

| Field | Value |
|-------|-------|
| Category | Cryptography |
| Detection | `#include <botan/*>`, `-lbotan-2` or `-lbotan-3`, CMake `find_package(Botan)` |
| Provides | TLS, X.509, symmetric/asymmetric crypto, hashing, KDF, RNG |

---

## Math / Science / Numerics

### Eigen

| Field | Value |
|-------|-------|
| Category | Linear algebra |
| Detection | `#include <Eigen/*>`, `Eigen::Matrix`, `Eigen::Vector`, header-only |
| Provides | Matrix/vector operations, decompositions, solvers, geometry. Header-only, template-heavy |

### OpenCV

| Field | Value |
|-------|-------|
| Category | Computer vision |
| Detection | `#include <opencv2/*>`, `cv::Mat`, `-lopencv_*`, CMake `find_package(OpenCV)` |
| Provides | Image processing, video capture, object detection, ML, camera calibration |

### BLAS / LAPACK

| Field | Value |
|-------|-------|
| Category | Linear algebra (low-level) |
| Detection | `#include <cblas.h>`, `#include <lapacke.h>`, `-lblas`, `-llapack` |
| Provides | Basic linear algebra subroutines, matrix factorizations, eigenvalue solvers |

### FFTW

| Field | Value |
|-------|-------|
| Category | Signal processing |
| Detection | `#include <fftw3.h>`, `-lfftw3` |
| Provides | Fast Fourier Transform — 1D, 2D, 3D, real and complex |

---

## Networking / Communication

### ZeroMQ (ØMQ)

| Field | Value |
|-------|-------|
| Category | Messaging / IPC |
| Detection | `#include <zmq.hpp>` (cppzmq), `#include <zmq.h>` (libzmq), `-lzmq` |
| Provides | Async message queues, pub/sub, req/rep, push/pull, inproc/IPC/TCP transport |

### gRPC

| Field | Value |
|-------|-------|
| Category | RPC framework |
| Detection | `#include <grpcpp/grpcpp.h>`, `.proto` files with `service` definitions, CMake `find_package(gRPC)` |
| Provides | HTTP/2-based RPC, protobuf serialization, streaming, deadlines, interceptors |

### libcurl

| Field | Value |
|-------|-------|
| Category | HTTP client |
| Detection | `#include <curl/curl.h>`, `-lcurl`, CMake `find_package(CURL)` |
| Provides | HTTP/HTTPS client, FTP, SMTP, multi-protocol transfers, async multi interface |

### cpp-httplib

| Field | Value |
|-------|-------|
| Category | HTTP client/server |
| Detection | `#include <httplib.h>`, header-only |
| Provides | Lightweight HTTP/HTTPS server and client, single-header |

---

## Logging

### spdlog

| Field | Value |
|-------|-------|
| Category | Logging |
| Detection | `#include <spdlog/*>`, `spdlog::info()`, `spdlog::logger`, header-only or `-lspdlog` |
| Provides | Fast structured logging, multiple sinks, formatting (fmt-based), async logging |

### glog (Google Logging)

| Field | Value |
|-------|-------|
| Category | Logging |
| Detection | `#include <glog/logging.h>`, `LOG(INFO)`, `CHECK_*`, `-lglog` |
| Provides | Severity-based logging, conditional logging, CHECK macros, stack traces on crash |

### log4cxx

| Field | Value |
|-------|-------|
| Category | Logging |
| Detection | `#include <log4cxx/*>`, `log4cxx::LoggerPtr`, `-llog4cxx` |
| Provides | Apache-style logging (port of Log4j), XML/properties config, appenders, layouts |

---

## Serialization

### Protocol Buffers (protobuf)

| Field | Value |
|-------|-------|
| Category | Serialization / IDL |
| Detection | `#include <google/protobuf/*>`, `.proto` files, `protoc` compiler, `-lprotobuf` |
| Provides | Language-neutral binary serialization, schema evolution, code generation |

### FlatBuffers

| Field | Value |
|-------|-------|
| Category | Serialization |
| Detection | `#include <flatbuffers/*>`, `.fbs` schema files, `flatc` compiler |
| Provides | Zero-copy deserialization, schema-based binary format, no parsing overhead |

### nlohmann/json

| Field | Value |
|-------|-------|
| Category | JSON |
| Detection | `#include <nlohmann/json.hpp>`, `nlohmann::json`, header-only |
| Provides | Intuitive JSON manipulation, STL-like access, serialization/deserialization |

### RapidJSON

| Field | Value |
|-------|-------|
| Category | JSON |
| Detection | `#include <rapidjson/*>`, `rapidjson::Document`, header-only |
| Provides | High-performance JSON parsing/generation, SAX and DOM APIs |

### yaml-cpp

| Field | Value |
|-------|-------|
| Category | YAML |
| Detection | `#include <yaml-cpp/yaml.h>`, `-lyaml-cpp` |
| Provides | YAML parsing and emitting |

### pugixml

| Field | Value |
|-------|-------|
| Category | XML |
| Detection | `#include <pugixml.hpp>`, header-only or `-lpugixml` |
| Provides | Fast XML parsing (DOM), XPath queries, small footprint |

---

## Memory Allocators

### jemalloc

| Field | Value |
|-------|-------|
| Category | Memory allocation |
| Detection | `#include <jemalloc/jemalloc.h>`, `-ljemalloc`, `LD_PRELOAD` usage |
| Provides | High-performance general-purpose allocator, reduced fragmentation, profiling |

### tcmalloc

| Field | Value |
|-------|-------|
| Category | Memory allocation |
| Detection | `#include <gperftools/tcmalloc.h>`, `-ltcmalloc`, gperftools dependency |
| Provides | Thread-caching allocator, heap profiling, leak detection |

---

## Compression

### zlib

| Field | Value |
|-------|-------|
| Category | Compression |
| Detection | `#include <zlib.h>`, `-lz`, CMake `find_package(ZLIB)` |
| Provides | DEFLATE compression/decompression, gzip format support |

### LZ4

| Field | Value |
|-------|-------|
| Category | Compression |
| Detection | `#include <lz4.h>`, `-llz4` |
| Provides | Extremely fast compression, block and frame formats |

### Zstandard (zstd)

| Field | Value |
|-------|-------|
| Category | Compression |
| Detection | `#include <zstd.h>`, `-lzstd`, CMake `find_package(zstd)` |
| Provides | High-ratio compression with fast decompression, dictionary support, streaming |

### Snappy

| Field | Value |
|-------|-------|
| Category | Compression |
| Detection | `#include <snappy.h>`, `-lsnappy` |
| Provides | Fast compression/decompression optimized for speed over ratio |

---

## Database Clients

### SQLite

| Field | Value |
|-------|-------|
| Category | Embedded database |
| Detection | `#include <sqlite3.h>`, `-lsqlite3`, often bundled as `sqlite3.c` amalgamation |
| Provides | Serverless SQL database, single-file storage, full ACID transactions |

### libpq (PostgreSQL)

| Field | Value |
|-------|-------|
| Category | Database client |
| Detection | `#include <libpq-fe.h>`, `-lpq`, CMake `find_package(PostgreSQL)` |
| Provides | PostgreSQL C client library, connection management, query execution, async queries |

### mysqlclient

| Field | Value |
|-------|-------|
| Category | Database client |
| Detection | `#include <mysql.h>`, `#include <mysql/mysql.h>`, `-lmysqlclient`, CMake `find_package(MySQL)` |
| Provides | MySQL/MariaDB C client library, prepared statements, connection pooling |

### MongoDB C++ Driver (mongocxx)

| Field | Value |
|-------|-------|
| Category | Database client |
| Detection | `#include <mongocxx/*>`, `#include <bsoncxx/*>`, CMake `find_package(mongocxx)` |
| Provides | MongoDB CRUD operations, aggregation, BSON document building, connection pooling |

### ODBC

| Field | Value |
|-------|-------|
| Category | Database abstraction |
| Detection | `#include <sql.h>`, `#include <sqlext.h>`, `-lodbc` |
| Provides | Database-agnostic SQL access via drivers, connection management |

---

## CLI Argument Parsing

### CLI11

| Field | Value |
|-------|-------|
| Category | CLI parsing |
| Detection | `#include <CLI/CLI.hpp>`, `CLI::App`, header-only |
| Provides | Modern C++ argument parser, subcommands, validators, INI config support |

### cxxopts

| Field | Value |
|-------|-------|
| Category | CLI parsing |
| Detection | `#include <cxxopts.hpp>`, `cxxopts::Options`, header-only |
| Provides | Lightweight argument parsing, positional args, grouped options |

### Boost.Program_options

| Field | Value |
|-------|-------|
| Category | CLI parsing |
| Detection | `#include <boost/program_options.hpp>`, `-lboost_program_options` |
| Provides | Command-line and config file parsing, typed options, validation |

### getopt / getopt_long

| Field | Value |
|-------|-------|
| Category | CLI parsing (C) |
| Detection | `#include <getopt.h>`, `getopt()`, `getopt_long()`, `struct option` |
| Provides | POSIX-standard argument parsing, short and long options |
