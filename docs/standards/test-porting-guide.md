# C++ Test Framework → JUnit 5 Translation Guide

When porting C++ tests, use this mapping to produce idiomatic JUnit 5 + AssertJ tests.

## Google Test (gtest) → JUnit 5

### Assertion Mapping

| gtest Macro | JUnit 5 / AssertJ Equivalent | Notes |
|---|---|---|
| ASSERT_EQ(a, b) | assertThat(a).isEqualTo(b) | Fatal in gtest, all assertions fatal in JUnit |
| EXPECT_EQ(a, b) | assertThat(a).isEqualTo(b) | Non-fatal in gtest; use SoftAssertions if needed |
| ASSERT_NE(a, b) | assertThat(a).isNotEqualTo(b) | |
| ASSERT_TRUE(x) | assertThat(x).isTrue() | |
| ASSERT_FALSE(x) | assertThat(x).isFalse() | |
| ASSERT_NULL(p) | assertThat(p).isNull() | |
| ASSERT_NOT_NULL(p) | assertThat(p).isNotNull() | |
| ASSERT_THROW(stmt, E) | assertThatThrownBy(() -> stmt).isInstanceOf(E.class) | |
| ASSERT_NO_THROW(stmt) | assertThatCode(() -> stmt).doesNotThrowAnyException() | |
| ASSERT_NEAR(a, b, eps) | assertThat(a).isCloseTo(b, within(eps)) | |
| ASSERT_GT/LT/GE/LE | assertThat(a).isGreaterThan(b) etc. | |
| ASSERT_STREQ(a, b) | assertThat(a).isEqualTo(b) | Java strings use .equals() |
| EXPECT_THAT(x, matcher) | assertThat(x).<appropriate method> | Map Hamcrest-style to AssertJ |

### Test Structure Mapping

| gtest Pattern | JUnit 5 Equivalent |
|---|---|
| TEST(Suite, Name) | @Test void name() |
| TEST_F(Fixture, Name) | Class extends fixture or @BeforeEach setup |
| SetUp() / TearDown() | @BeforeEach / @AfterEach |
| SetUpTestSuite() / TearDownTestSuite() | @BeforeAll / @AfterAll (static) |
| INSTANTIATE_TEST_SUITE_P | @ParameterizedTest + @MethodSource or @CsvSource |
| TEST_P(Suite, Name) | @ParameterizedTest method |
| TYPED_TEST | @ParameterizedTest with type token or separate test per type |
| ::testing::Values(1,2,3) | @ValueSource(ints = {1, 2, 3}) or @MethodSource |
| SCOPED_TRACE(msg) | // context comment or custom assertion message |
| GTEST_SKIP() | Assumptions.assumeTrue(condition) |

### Fixture Pattern

C++ (gtest fixture):
```cpp
class OrderProcessorTest : public ::testing::Test {
protected:
    void SetUp() override {
        db_ = std::make_unique<MockDatabase>();
        processor_ = std::make_unique<OrderProcessor>(db_.get());
    }
    std::unique_ptr<MockDatabase> db_;
    std::unique_ptr<OrderProcessor> processor_;
};

TEST_F(OrderProcessorTest, ProcessesValidOrder) {
    Order order{"item1", 2, 29.99};
    auto result = processor_->process(order);
    ASSERT_TRUE(result.success());
    ASSERT_EQ(result.total(), 59.98);
}
```

Java (JUnit 5 + Mockito + AssertJ):
```java
@ExtendWith(MockitoExtension.class)
class OrderProcessorServiceTest {

    @Mock
    private OrderRepository orderRepository;

    private ProcessOrderService processor;

    @BeforeEach
    void setUp() {
        processor = new ProcessOrderService(orderRepository);
    }

    @Test
    void should_process_valid_order() {
        var command = new ProcessOrderCommand("item1", 2, BigDecimal.valueOf(29.99));
        var result = processor.execute(command);
        assertThat(result.success()).isTrue();
        assertThat(result.total()).isEqualByComparingTo(BigDecimal.valueOf(59.98));
    }
}
```

## Catch2 → JUnit 5

### Assertion Mapping

| Catch2 | JUnit 5 / AssertJ |
|---|---|
| REQUIRE(expr) | assertThat(expr).isTrue() or direct assertion |
| CHECK(expr) | SoftAssertions (non-fatal) |
| REQUIRE_THAT(x, Matcher) | assertThat(x).<matcher method> |
| REQUIRE_THROWS(expr) | assertThatThrownBy(() -> expr) |
| REQUIRE_THROWS_AS(expr, T) | assertThatThrownBy(() -> expr).isInstanceOf(T.class) |
| REQUIRE_NOTHROW(expr) | assertThatCode(() -> expr).doesNotThrowAnyException() |
| REQUIRE_FALSE(expr) | assertThat(expr).isFalse() |
| INFO(msg) | // logged context, or use assertThat(...).as(msg) |
| SECTION("name") | Separate @Test method or @Nested class |
| GENERATE(range) | @ParameterizedTest + @MethodSource |

### Structure Mapping

| Catch2 | JUnit 5 |
|---|---|
| TEST_CASE("name", "[tag]") | @Test @Tag("tag") void name() |
| SECTION("name") | @Nested class or separate @Test |
| TEMPLATE_TEST_CASE | @ParameterizedTest with type |
| Generators / GENERATE | @MethodSource or @ArgumentsSource |

## Doctest → JUnit 5

| Doctest | JUnit 5 / AssertJ |
|---|---|
| CHECK(x == y) | assertThat(x).isEqualTo(y) |
| REQUIRE(x == y) | assertThat(x).isEqualTo(y) |
| SUBCASE("name") | @Nested class or separate @Test |
| TEST_CASE("name") | @Test void name() |
| CHECK_THROWS(expr) | assertThatThrownBy(() -> expr) |

## General Porting Rules

1. **One TEST_F/TEST_CASE → one @Test method** (don't combine)
2. **EXPECT (non-fatal) → SoftAssertions** if multiple assertions should all run
3. **C++ SECTION nesting → @Nested classes** in JUnit 5
4. **Parameterized tests → @ParameterizedTest** with appropriate source
5. **Test fixtures with inheritance → @BeforeEach** setup or JUnit @ExtendWith
6. **Mocks: gmock → Mockito** (when/verify pattern maps directly)
7. **Floating point comparison → isCloseTo()** with explicit tolerance
8. **String comparison → isEqualTo()** (Java strings are value-compared)
9. **Pointer null checks → isNull() / isNotNull()** (no pointer semantics in Java)
10. **RAII cleanup → @AfterEach** or try-with-resources in test
