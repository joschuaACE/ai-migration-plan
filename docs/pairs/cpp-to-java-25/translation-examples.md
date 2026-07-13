# C++ → Java Translation Examples

These are concrete worked examples. Translators should use these as reference for style,
structure, and testing patterns.

Examples are illustrative, not normative mappings. Before reusing one, apply
`translation-patterns.md`, the C++ semantic-hazard analysis, Java 25 runtime guidance, and
the selected output profile. The source behavior, not the example's framework or class
shape, remains authoritative. Any changed numeric, ownership, concurrency, error, encoding,
or serialization semantics requires a decision and behavior-linked evidence.

---

## Service Example

### C++ Input: `OrderHandler.h` / `OrderHandler.cpp`

```cpp
#pragma once
#include <string>
#include <optional>
#include "DatabaseClient.h"

struct OrderResult {
    bool success;
    std::string order_id;
    double total;
    std::string error;
};

class OrderHandler {
public:
    explicit OrderHandler(DatabaseClient* db) : db_(db) {}

    OrderResult process(const std::string& customer_id,
                        const std::string& item,
                        int quantity,
                        double unit_price) {
        if (customer_id.empty() || item.empty()) {
            return {false, "", 0.0, "Invalid input: customer and item required"};
        }
        if (quantity <= 0 || unit_price <= 0.0) {
            return {false, "", 0.0, "Invalid input: quantity and price must be positive"};
        }

        double total = quantity * unit_price;
        std::string order_id = db_->insert_order(customer_id, item, quantity, total);
        if (order_id.empty()) {
            return {false, "", 0.0, "Database error: failed to persist order"};
        }
        return {true, order_id, total, ""};
    }

private:
    DatabaseClient* db_;
};
```

### Java Output

#### Domain Model: `Order.java`

```java
package com.company.orders.domain.model;

import java.math.BigDecimal;

/// An order placed by a customer for a specific item.
public record Order(
    OrderId id,
    CustomerId customerId,
    String item,
    int quantity,
    BigDecimal total
) {
    public Order {
        if (item == null || item.isBlank()) {
            throw new IllegalArgumentException("Item must not be blank");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("Quantity must be positive");
        }
        if (total == null || total.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Total must be positive");
        }
    }
}
```

#### Domain Value Objects: `OrderId.java`, `CustomerId.java`

```java
package com.company.orders.domain.model;

public record OrderId(String value) {
    public OrderId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("OrderId must not be blank");
        }
    }
}
```

```java
package com.company.orders.domain.model;

public record CustomerId(String value) {
    public CustomerId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("CustomerId must not be blank");
        }
    }
}
```

#### Driving Port: `ProcessOrderUseCase.java`

```java
package com.company.orders.domain.port.in;

import com.company.orders.application.dto.ProcessOrderCommand;
import com.company.orders.application.dto.OrderResponse;

/// Processes a new order — validates, computes total, and persists.
public interface ProcessOrderUseCase {
    OrderResponse execute(ProcessOrderCommand command);
}
```

#### Driven Port: `OrderRepository.java`

```java
package com.company.orders.domain.port.out;

import com.company.orders.domain.model.Order;
import com.company.orders.domain.model.OrderId;

/// Persistence port for orders.
public interface OrderRepository {
    OrderId save(Order order);
}
```

#### Application DTOs

```java
package com.company.orders.application.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import java.math.BigDecimal;

public record ProcessOrderCommand(
    @NotBlank String customerId,
    @NotBlank String item,
    @Positive int quantity,
    @Positive BigDecimal unitPrice
) {}
```

```java
package com.company.orders.application.dto;

import java.math.BigDecimal;

public record OrderResponse(String orderId, BigDecimal total) {}
```

#### Use Case Implementation: `ProcessOrderService.java`

```java
package com.company.orders.application.usecase;

import com.company.orders.application.dto.OrderResponse;
import com.company.orders.application.dto.ProcessOrderCommand;
import com.company.orders.domain.model.CustomerId;
import com.company.orders.domain.model.Order;
import com.company.orders.domain.model.OrderId;
import com.company.orders.domain.port.in.ProcessOrderUseCase;
import com.company.orders.domain.port.out.OrderRepository;
import io.micrometer.observation.annotation.Observed;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

@Service
@Observed(name = "process.order")
class ProcessOrderService implements ProcessOrderUseCase {

    private final OrderRepository orderRepository;

    ProcessOrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @Override
    @Transactional
    public OrderResponse execute(ProcessOrderCommand command) {
        var total = command.unitPrice().multiply(BigDecimal.valueOf(command.quantity()));

        var order = new Order(
            null,
            new CustomerId(command.customerId()),
            command.item(),
            command.quantity(),
            total
        );

        OrderId savedId = orderRepository.save(order);
        return new OrderResponse(savedId.value(), total);
    }
}
```

#### REST Controller: `OrderController.java`

```java
package com.company.orders.adapter.in.web;

import com.company.orders.application.dto.OrderResponse;
import com.company.orders.application.dto.ProcessOrderCommand;
import com.company.orders.domain.port.in.ProcessOrderUseCase;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
class OrderController {

    private final ProcessOrderUseCase processOrder;

    OrderController(ProcessOrderUseCase processOrder) {
        this.processOrder = processOrder;
    }

    @PostMapping
    ResponseEntity<OrderResponse> create(@Valid @RequestBody ProcessOrderCommand command) {
        var result = processOrder.execute(command);
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }
}
```

#### Unit Test: `ProcessOrderServiceTest.java`

```java
package com.company.orders.application.usecase;

import com.company.orders.application.dto.ProcessOrderCommand;
import com.company.orders.domain.model.OrderId;
import com.company.orders.domain.port.out.OrderRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class ProcessOrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    private ProcessOrderService service;

    @BeforeEach
    void setUp() {
        service = new ProcessOrderService(orderRepository);
    }

    @Test
    void should_compute_total_and_persist_order() {
        given(orderRepository.save(any())).willReturn(new OrderId("ORD-001"));

        var command = new ProcessOrderCommand("CUST-1", "Widget", 3, BigDecimal.valueOf(10.00));
        var response = service.execute(command);

        assertThat(response.orderId()).isEqualTo("ORD-001");
        assertThat(response.total()).isEqualByComparingTo(BigDecimal.valueOf(30.00));
    }

    @Test
    void should_reject_invalid_quantity_via_domain_model() {
        var command = new ProcessOrderCommand("CUST-1", "Widget", -1, BigDecimal.valueOf(10.00));

        org.assertj.core.api.Assertions.assertThatThrownBy(() -> service.execute(command))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("positive");
    }
}
```

#### Slice Test: `OrderControllerTest.java`

```java
package com.company.orders.adapter.in.web;

import com.company.orders.application.dto.OrderResponse;
import com.company.orders.application.dto.ProcessOrderCommand;
import com.company.orders.domain.port.in.ProcessOrderUseCase;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockbean.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProcessOrderUseCase processOrder;

    @Test
    void should_return_201_with_order_response() throws Exception {
        given(processOrder.execute(any(ProcessOrderCommand.class)))
                .willReturn(new OrderResponse("ORD-001", BigDecimal.valueOf(30.00)));

        mockMvc.perform(post("/api/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                            {
                                "customerId": "CUST-1",
                                "item": "Widget",
                                "quantity": 3,
                                "unitPrice": 10.00
                            }
                            """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.orderId").value("ORD-001"))
                .andExpect(jsonPath("$.total").value(30.00));
    }

    @Test
    void should_return_400_when_customer_id_blank() throws Exception {
        mockMvc.perform(post("/api/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                            {
                                "customerId": "",
                                "item": "Widget",
                                "quantity": 3,
                                "unitPrice": 10.00
                            }
                            """))
                .andExpect(status().isBadRequest());
    }
}
```

---

## Library Example

### C++ Input: `DataParser.h` / `DataParser.cpp`

```cpp
#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <stdexcept>

struct ParseResult {
    std::vector<std::string> fields;
    int record_count;
    bool has_errors;
    std::string error_message;
};

class DataParser {
public:
    explicit DataParser(char delimiter = ',') : delimiter_(delimiter) {}

    ParseResult parse(const std::string& input) const {
        if (input.empty()) {
            return ParseResult{std::vector<std::string>{}, 0, true, "Input must not be empty"};
        }

        std::vector<std::string> fields;
        std::istringstream stream(input);
        std::string token;
        while (std::getline(stream, token, delimiter_)) {
            if (!token.empty()) {
                fields.push_back(token);
            }
        }

        if (fields.empty()) {
            return ParseResult{std::vector<std::string>{}, 0, true, "No valid fields found in input"};
        }
        return {fields, static_cast<int>(fields.size()), false, ""};
    }

private:
    char delimiter_;
};
```

### Java Output (Simple Layered Architecture)

#### Public API Interface: `DataParserApi.java`

```java
package com.company.parser.api;

/// Parses delimited text input into structured fields.
///
/// Thread-safe: instances are safe to use from multiple threads concurrently.
public interface DataParserApi {

    /// Parse the given input string into individual fields.
    ///
    /// @param input the delimited text to parse (must not be null or blank)
    /// @return result containing parsed fields and metadata
    /// @throws IllegalArgumentException if input is null or blank
    ParseResult parse(String input);

    /// Create a parser with the default comma delimiter.
    static DataParserApi ofComma() {
        return new com.company.parser.internal.DefaultDataParser(',');
    }

    /// Create a parser with a custom delimiter.
    ///
    /// @param delimiter the character to split fields on
    static DataParserApi of(char delimiter) {
        return new com.company.parser.internal.DefaultDataParser(delimiter);
    }
}
```

#### Public API Result: `ParseResult.java`

```java
package com.company.parser.api;

import java.util.List;

/// Result of parsing delimited text input.
///
/// @param fields the extracted non-empty fields
/// @param recordCount number of fields extracted
/// @param hasErrors whether parsing encountered errors
/// @param errorMessage description of error, or empty string if none
public record ParseResult(
    List<String> fields,
    int recordCount,
    boolean hasErrors,
    String errorMessage
) {
    public ParseResult {
        fields = List.copyOf(fields); // defensive immutable copy
    }

    /// Convenience factory for a successful result.
    static ParseResult success(List<String> fields) {
        return new ParseResult(fields, fields.size(), false, "");
    }

    /// Convenience factory for a failed result.
    static ParseResult failure(String errorMessage) {
        return new ParseResult(List.of(), 0, true, errorMessage);
    }
}
```

#### Internal Implementation: `DefaultDataParser.java`

```java
package com.company.parser.internal;

import com.company.parser.api.DataParserApi;
import com.company.parser.api.ParseResult;

import java.util.Arrays;
import java.util.List;

/// Default implementation — splits input by delimiter, filters empty tokens.
public final class DefaultDataParser implements DataParserApi {

    private final char delimiter;

    public DefaultDataParser(char delimiter) {
        this.delimiter = delimiter;
    }

    @Override
    public ParseResult parse(String input) {
        if (input == null || input.isBlank()) {
            throw new IllegalArgumentException("Input must not be null or blank");
        }

        List<String> fields = Arrays.stream(input.split(String.valueOf(delimiter)))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();

        if (fields.isEmpty()) {
            return ParseResult.failure("No valid fields found in input");
        }
        return ParseResult.success(fields);
    }
}
```

#### Module Descriptor: `module-info.java`

```java
module com.company.parser {
    exports com.company.parser.api;
    // com.company.parser.internal is NOT exported — encapsulated by default

    requires org.slf4j;
}
```

#### Unit Test: `DefaultDataParserTest.java`

```java
package com.company.parser.internal;

import com.company.parser.api.DataParserApi;
import com.company.parser.api.ParseResult;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DefaultDataParserTest {

    private final DataParserApi parser = DataParserApi.ofComma();

    @Test
    void should_parse_comma_separated_fields() {
        var result = parser.parse("alice,bob,charlie");

        assertThat(result.hasErrors()).isFalse();
        assertThat(result.recordCount()).isEqualTo(3);
        assertThat(result.fields()).containsExactly("alice", "bob", "charlie");
    }

    @Test
    void should_skip_empty_tokens() {
        var result = parser.parse("alice,,bob,,,charlie");

        assertThat(result.fields()).containsExactly("alice", "bob", "charlie");
    }

    @Test
    void should_return_failure_when_no_valid_fields() {
        var result = parser.parse(",,,");

        assertThat(result.hasErrors()).isTrue();
        assertThat(result.errorMessage()).contains("No valid fields");
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "   "})
    void should_throw_on_blank_input(String input) {
        assertThatThrownBy(() -> parser.parse(input))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("must not be null or blank");
    }

    @Test
    void should_throw_on_null_input() {
        assertThatThrownBy(() -> parser.parse(null))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void should_support_custom_delimiter() {
        var pipeParser = DataParserApi.of('|');
        var result = pipeParser.parse("one|two|three");

        assertThat(result.fields()).containsExactly("one", "two", "three");
    }
}
```

---

## CLI Example

### C++ Input: `main.cpp`

```cpp
#include <iostream>
#include <string>
#include <getopt.h>
#include "FileConverter.h"

void print_usage() {
    std::cerr << "Usage: convert -i <input> -o <output> -f <format>\n"
              << "  -i  Input file path\n"
              << "  -o  Output file path\n"
              << "  -f  Target format (json, csv, xml)\n";
}

int main(int argc, char* argv[]) {
    std::string input_path, output_path, format;
    int opt;

    while ((opt = getopt(argc, argv, "i:o:f:")) != -1) {
        switch (opt) {
            case 'i': input_path = optarg; break;
            case 'o': output_path = optarg; break;
            case 'f': format = optarg; break;
            default: print_usage(); return 2;
        }
    }

    if (input_path.empty() || output_path.empty() || format.empty()) {
        print_usage();
        return 2;
    }

    FileConverter converter;
    auto result = converter.convert(input_path, output_path, format);
    if (!result.success) {
        std::cerr << "Error: " << result.error_message << "\n";
        return 1;
    }

    std::cout << "Converted " << result.records_written << " records\n";
    return 0;
}
```

### Java Output

#### Domain Port: `ConvertFileUseCase.java`

```java
package com.company.convert.domain.port.in;

import com.company.convert.application.dto.ConvertFileCommand;
import com.company.convert.application.dto.ConvertFileResult;

/// Converts a file from one format to another.
public interface ConvertFileUseCase {
    ConvertFileResult execute(ConvertFileCommand command);
}
```

#### Application DTOs

```java
package com.company.convert.application.dto;

import java.nio.file.Path;

public record ConvertFileCommand(
    Path inputPath,
    Path outputPath,
    String targetFormat
) {
    public ConvertFileCommand {
        if (inputPath == null) {
            throw new IllegalArgumentException("Input path must not be null");
        }
        if (outputPath == null) {
            throw new IllegalArgumentException("Output path must not be null");
        }
        if (targetFormat == null || targetFormat.isBlank()) {
            throw new IllegalArgumentException("Target format must not be blank");
        }
    }
}
```

```java
package com.company.convert.application.dto;

public record ConvertFileResult(
    boolean success,
    int recordsWritten,
    String errorMessage
) {
    public static ConvertFileResult success(int recordsWritten) {
        return new ConvertFileResult(true, recordsWritten, "");
    }

    public static ConvertFileResult failure(String errorMessage) {
        return new ConvertFileResult(false, 0, errorMessage);
    }
}
```

#### CLI Adapter: `ConvertCommand.java`

```java
package com.company.convert.adapter.in.cli;

import com.company.convert.application.dto.ConvertFileCommand;
import com.company.convert.domain.port.in.ConvertFileUseCase;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.nio.file.Path;
import java.util.concurrent.Callable;

@Command(name = "convert", mixinStandardHelpOptions = true,
         version = "1.0.0",
         description = "Convert files between formats (json, csv, xml)")
class ConvertCommand implements Callable<Integer> {

    private final ConvertFileUseCase convertFile;

    @Option(names = {"-i", "--input"}, required = true,
            description = "Input file path")
    private Path inputPath;

    @Option(names = {"-o", "--output"}, required = true,
            description = "Output file path")
    private Path outputPath;

    @Option(names = {"-f", "--format"}, required = true,
            description = "Target format: ${COMPLETION-CANDIDATES}",
            completionCandidates = FormatCandidates.class)
    private String format;

    ConvertCommand(ConvertFileUseCase convertFile) {
        this.convertFile = convertFile;
    }

    @Override
    public Integer call() {
        try {
            var command = new ConvertFileCommand(inputPath, outputPath, format);
            var result = convertFile.execute(command);

            if (!result.success()) {
                System.err.println("Error: " + result.errorMessage());
                return 1;
            }

            System.out.printf("Converted %d records%n", result.recordsWritten());
            return 0;

        } catch (IllegalArgumentException e) {
            System.err.println("Error: " + e.getMessage());
            return 2;
        }
    }
}
```

#### App Entry Point: `App.java`

```java
package com.company.convert;

import com.company.convert.adapter.in.cli.ConvertCommand;
import picocli.CommandLine;

public class App {
    public static void main(String[] args) {
        int exitCode = new CommandLine(new ConvertCommand(createUseCase()))
                .execute(args);
        System.exit(exitCode);
    }

    private static com.company.convert.domain.port.in.ConvertFileUseCase createUseCase() {
        // Wire dependencies — in production, use a DI container or manual wiring
        var fileReader = new com.company.convert.adapter.out.filesystem.LocalFileReader();
        var fileWriter = new com.company.convert.adapter.out.filesystem.LocalFileWriter();
        return new com.company.convert.application.usecase.ConvertFileService(fileReader, fileWriter);
    }
}
```

#### Unit Test: `ConvertCommandTest.java`

```java
package com.company.convert.adapter.in.cli;

import com.company.convert.application.dto.ConvertFileResult;
import com.company.convert.domain.port.in.ConvertFileUseCase;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import picocli.CommandLine;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class ConvertCommandTest {

    @Mock
    private ConvertFileUseCase convertFile;

    private CommandLine cmd;

    @BeforeEach
    void setUp() {
        cmd = new CommandLine(new ConvertCommand(convertFile));
    }

    @Test
    void should_return_0_on_successful_conversion() {
        given(convertFile.execute(any()))
                .willReturn(ConvertFileResult.success(42));

        int exitCode = cmd.execute("-i", "input.csv", "-o", "output.json", "-f", "json");

        assertThat(exitCode).isZero();
    }

    @Test
    void should_return_1_on_conversion_failure() {
        given(convertFile.execute(any()))
                .willReturn(ConvertFileResult.failure("Unsupported format"));

        int exitCode = cmd.execute("-i", "input.csv", "-o", "output.xml", "-f", "xml");

        assertThat(exitCode).isEqualTo(1);
    }

    @Test
    void should_return_2_when_required_options_missing() {
        int exitCode = cmd.execute("-i", "input.csv");

        assertThat(exitCode).isEqualTo(2);
    }
}
```
