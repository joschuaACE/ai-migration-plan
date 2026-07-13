# C++ Test Frameworks

Reference for identifying and understanding C++ test frameworks in source code.

---

## Google Test (gtest) / Google Mock (gmock)

### Detection Signals

- Include: `#include <gtest/gtest.h>`, `#include <gmock/gmock.h>`
- CMake: `find_package(GTest)`, `gtest_discover_tests()`, `target_link_libraries(... GTest::gtest)`
- Conan: `gtest/1.x` in requires
- vcpkg: `"gtest"` in dependencies
- Binary: `libgtest.a`, `libgmock.a`

### File Naming Conventions

- `*_test.cpp`, `*_unittest.cpp`, `test_*.cpp`
- Test directories: `test/`, `tests/`, `unittest/`
- Mock headers: `mock_*.h`, `*_mock.h`

### Structure Patterns

```cpp
// Basic test
TEST(SuiteName, TestName) {
    EXPECT_EQ(actual, expected);
    ASSERT_TRUE(condition);
}

// Fixture-based test
class MyFixture : public ::testing::Test {
protected:
    void SetUp() override { /* per-test setup */ }
    void TearDown() override { /* per-test cleanup */ }
};
TEST_F(MyFixture, TestName) { /* uses fixture members */ }

// Parameterized test
class MyParam : public ::testing::TestWithParam<int> {};
TEST_P(MyParam, TestName) { GetParam(); }
INSTANTIATE_TEST_SUITE_P(Prefix, MyParam, ::testing::Values(1, 2, 3));

// Typed test
template <typename T>
class TypedTest : public ::testing::Test {};
TYPED_TEST_SUITE(TypedTest, MyTypes);
TYPED_TEST(TypedTest, TestName) { TypeParam value; }

// Death test
TEST(DeathTest, Crashes) {
    EXPECT_DEATH(function(), "expected message");
}
```

### Assertion Macros

| Category | Fatal (stops test) | Non-fatal (continues) |
|----------|-------------------|----------------------|
| Boolean | `ASSERT_TRUE`, `ASSERT_FALSE` | `EXPECT_TRUE`, `EXPECT_FALSE` |
| Equality | `ASSERT_EQ`, `ASSERT_NE` | `EXPECT_EQ`, `EXPECT_NE` |
| Comparison | `ASSERT_LT`, `ASSERT_LE`, `ASSERT_GT`, `ASSERT_GE` | `EXPECT_LT`, `EXPECT_LE`, `EXPECT_GT`, `EXPECT_GE` |
| String | `ASSERT_STREQ`, `ASSERT_STRNE` | `EXPECT_STREQ`, `EXPECT_STRNE` |
| Float | `ASSERT_FLOAT_EQ`, `ASSERT_DOUBLE_EQ`, `ASSERT_NEAR` | `EXPECT_FLOAT_EQ`, `EXPECT_DOUBLE_EQ`, `EXPECT_NEAR` |
| Exception | `ASSERT_THROW`, `ASSERT_NO_THROW`, `ASSERT_ANY_THROW` | `EXPECT_THROW`, `EXPECT_NO_THROW`, `EXPECT_ANY_THROW` |

### Google Mock Patterns

```cpp
class MockService : public Service {
public:
    MOCK_METHOD(ReturnType, MethodName, (args), (specifiers));
};

EXPECT_CALL(mock, Method(Eq(value)))
    .Times(1)
    .WillOnce(Return(result));
```

### Test Main

```cpp
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
```

Or linked with `gtest_main` library (no explicit main needed).

---

## Catch2

### Detection Signals

- Include: `#include <catch2/catch_test_macros.hpp>` (v3), `#include "catch.hpp"` (v2)
- CMake: `find_package(Catch2)`, `catch_discover_tests()`
- Conan: `catch2/3.x` in requires
- Single-header v2: `catch.hpp` in project

### File Naming Conventions

- `*_test.cpp`, `test_*.cpp`, `*_tests.cpp`
- Often a single `test_main.cpp` with `#define CATCH_CONFIG_MAIN`

### Structure Patterns

```cpp
// Basic test case
TEST_CASE("Description", "[tag1][tag2]") {
    REQUIRE(expression);
    CHECK(expression);
}

// Sections (nested sub-tests, each runs from the top)
TEST_CASE("Feature") {
    // shared setup runs before each SECTION
    int x = 1;

    SECTION("first path") {
        REQUIRE(x == 1);
    }
    SECTION("second path") {
        x = 2;
        REQUIRE(x == 2);
    }
}

// BDD-style
SCENARIO("description", "[tag]") {
    GIVEN("initial state") {
        WHEN("action") {
            THEN("result") {
                REQUIRE(condition);
            }
        }
    }
}

// Generators (parameterized - Catch2 v3)
TEST_CASE("Parameterized") {
    auto value = GENERATE(1, 2, 3, range(10, 20));
    REQUIRE(value > 0);
}

// Template test
TEMPLATE_TEST_CASE("Typed", "[template]", int, float, double) {
    TestType x = GENERATE(1, 2);
    REQUIRE(x > 0);
}
```

### Assertion Macros

| Macro | Behavior |
|-------|----------|
| `REQUIRE(expr)` | Fatal — stops test on failure |
| `CHECK(expr)` | Non-fatal — continues on failure |
| `REQUIRE_FALSE(expr)` | Fatal — expression must be false |
| `CHECK_FALSE(expr)` | Non-fatal — expression must be false |
| `REQUIRE_THROWS(expr)` | Fatal — must throw any exception |
| `REQUIRE_THROWS_AS(expr, Type)` | Fatal — must throw specific type |
| `REQUIRE_NOTHROW(expr)` | Fatal — must not throw |
| `REQUIRE_THAT(expr, matcher)` | Fatal — with Catch2 matchers |
| `CHECK_THAT(expr, matcher)` | Non-fatal — with Catch2 matchers |

### Test Main

```cpp
// v2 single-header: #define CATCH_CONFIG_MAIN before include
// v3: link with Catch2::Catch2WithMain
```

---

## doctest

### Detection Signals

- Include: `#include <doctest/doctest.h>` or `#include "doctest.h"`
- CMake: `find_package(doctest)`, `doctest_discover_tests()`
- Single header: `doctest.h` in project (very common — lightweight)
- Often embedded directly in source files alongside production code

### File Naming Conventions

- `*_test.cpp`, `test_*.cpp`
- **Unique trait:** Tests may live in production `.cpp` files (behind `#ifdef DOCTEST_CONFIG_IMPLEMENT`)

### Structure Patterns

```cpp
// Basic test
TEST_CASE("Description") {
    CHECK(expression);
    REQUIRE(expression);
}

// Subcases (similar to Catch2 SECTIONs)
TEST_CASE("Feature") {
    int x = 0;
    SUBCASE("path A") { x = 1; }
    SUBCASE("path B") { x = 2; }
    // each subcase runs independently
}

// Test suite grouping
TEST_SUITE("SuiteName") {
    TEST_CASE("in suite") { /* ... */ }
}

// Parameterized (via TEST_CASE_TEMPLATE)
TEST_CASE_TEMPLATE("Typed", T, int, float, double) {
    T x = T(1);
    CHECK(x > T(0));
}
```

### Assertion Macros

| Macro | Behavior |
|-------|----------|
| `CHECK(expr)` | Non-fatal |
| `REQUIRE(expr)` | Fatal |
| `CHECK_EQ(a, b)`, `CHECK_NE`, `CHECK_LT`, etc. | Non-fatal comparison |
| `REQUIRE_EQ(a, b)`, `REQUIRE_NE`, etc. | Fatal comparison |
| `CHECK_THROWS(expr)` | Non-fatal — must throw |
| `CHECK_THROWS_AS(expr, Type)` | Non-fatal — specific exception |
| `CHECK_NOTHROW(expr)` | Non-fatal — must not throw |
| `WARN(expr)` | Log only — never fails |

### Test Main

```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
// or: custom main with doctest::Context
```

---

## Boost.Test

### Detection Signals

- Include: `#include <boost/test/unit_test.hpp>`, `#include <boost/test/included/unit_test.hpp>`
- CMake: `find_package(Boost COMPONENTS unit_test_framework)`
- Link: `-lboost_unit_test_framework`
- Conan: `boost/1.x` with `unit_test_framework` component

### File Naming Conventions

- `*_test.cpp`, `test_*.cpp`, `*_ut.cpp`
- Often one file per test suite

### Structure Patterns

```cpp
// Auto-registered test case
#define BOOST_TEST_MODULE MyModule
#include <boost/test/unit_test.hpp>

BOOST_AUTO_TEST_CASE(test_name) {
    BOOST_CHECK(condition);
    BOOST_REQUIRE(condition);
}

// Test suite
BOOST_AUTO_TEST_SUITE(suite_name)
    BOOST_AUTO_TEST_CASE(test1) { /* ... */ }
    BOOST_AUTO_TEST_CASE(test2) { /* ... */ }
BOOST_AUTO_TEST_SUITE_END()

// Fixture
struct MyFixture {
    MyFixture() { /* setup */ }
    ~MyFixture() { /* teardown */ }
};
BOOST_FIXTURE_TEST_CASE(test_name, MyFixture) { /* uses fixture members */ }

// Parameterized (data-driven)
BOOST_DATA_TEST_CASE(test_name, boost::unit_test::data::make({1,2,3}), value) {
    BOOST_CHECK(value > 0);
}

// Template test
BOOST_AUTO_TEST_CASE_TEMPLATE(test_name, T, type_list) {
    T x{};
    BOOST_CHECK(x == T{});
}
```

### Assertion Macros

| Macro | Behavior |
|-------|----------|
| `BOOST_CHECK(expr)` | Non-fatal |
| `BOOST_REQUIRE(expr)` | Fatal |
| `BOOST_WARN(expr)` | Warning only |
| `BOOST_CHECK_EQUAL(a, b)` | Non-fatal equality |
| `BOOST_CHECK_CLOSE(a, b, tol)` | Floating point within tolerance |
| `BOOST_CHECK_THROW(expr, Type)` | Must throw specific exception |
| `BOOST_CHECK_NO_THROW(expr)` | Must not throw |
| `BOOST_CHECK_MESSAGE(expr, msg)` | With custom message |

---

## CppUnit

### Detection Signals

- Include: `#include <cppunit/TestCase.h>`, `#include <cppunit/extensions/HelperMacros.h>`
- Link: `-lcppunit`
- CMake: `find_package(CppUnit)` or manual `-lcppunit`
- **Note:** Legacy framework — newer projects rarely adopt it

### File Naming Conventions

- `*Test.cpp`, `*TestCase.cpp`
- Header + source pairs for test classes

### Structure Patterns

```cpp
#include <cppunit/extensions/HelperMacros.h>

class MyTest : public CppUnit::TestFixture {
    CPPUNIT_TEST_SUITE(MyTest);
    CPPUNIT_TEST(testMethod1);
    CPPUNIT_TEST(testMethod2);
    CPPUNIT_TEST_EXCEPTION(testThrows, std::runtime_error);
    CPPUNIT_TEST_SUITE_END();

public:
    void setUp() override { /* per-test setup */ }
    void tearDown() override { /* per-test cleanup */ }

    void testMethod1() {
        CPPUNIT_ASSERT(condition);
        CPPUNIT_ASSERT_EQUAL(expected, actual);
    }
    void testMethod2() {
        CPPUNIT_ASSERT_DOUBLES_EQUAL(expected, actual, delta);
    }
};

CPPUNIT_TEST_SUITE_REGISTRATION(MyTest);
```

### Assertion Macros

| Macro | Purpose |
|-------|---------|
| `CPPUNIT_ASSERT(expr)` | Boolean assertion |
| `CPPUNIT_ASSERT_EQUAL(expected, actual)` | Equality |
| `CPPUNIT_ASSERT_DOUBLES_EQUAL(exp, act, delta)` | Float equality |
| `CPPUNIT_ASSERT_THROW(expr, Type)` | Must throw |
| `CPPUNIT_ASSERT_NO_THROW(expr)` | Must not throw |
| `CPPUNIT_ASSERT_MESSAGE(msg, expr)` | With message |
| `CPPUNIT_FAIL(msg)` | Unconditional failure |

### Test Runner

```cpp
#include <cppunit/ui/text/TestRunner.h>
int main() {
    CppUnit::TextUi::TestRunner runner;
    runner.addTest(MyTest::suite());
    return runner.run() ? 0 : 1;
}
```

---

## Framework Comparison Summary

| Feature | gtest | Catch2 | doctest | Boost.Test | CppUnit |
|---------|-------|--------|---------|------------|---------|
| Fixtures | Class-based (`TEST_F`) | SECTIONs | SUBCASEs | Class or `BOOST_FIXTURE_TEST_CASE` | Class-based |
| Parameterized | `TEST_P` + `INSTANTIATE` | `GENERATE()` | `TEST_CASE_TEMPLATE` | `BOOST_DATA_TEST_CASE` | Manual |
| Mocking | gmock (integrated) | External | External | Turtle (external) | External |
| BDD style | No | `SCENARIO`/`GIVEN`/`WHEN`/`THEN` | No | No | No |
| Header-only | No | Yes (v2), lib (v3) | Yes | Optional | No |
| Tags/labels | `--gtest_filter` | `[tag]` syntax | `TEST_SUITE` | Suites | Suites |
| Death tests | `EXPECT_DEATH` | `REQUIRE_THROWS` | `CHECK_THROWS` | `BOOST_CHECK_THROW` | `CPPUNIT_TEST_EXCEPTION` |
