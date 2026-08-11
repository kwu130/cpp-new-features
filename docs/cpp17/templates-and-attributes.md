# 模板参数与属性

C++17 允许 `auto` 非类型模板参数，并标准化了 `[[nodiscard]]`、`[[maybe_unused]]` 和 `[[fallthrough]]` 等常用属性。

<!-- example id="cpp17-templates-attributes" std="c++17" file="main.cpp" kind="single" compilers="all" output="medium" -->
```cpp
#include <iostream>
#include <string>

template <auto Value>
constexpr auto twice = Value * 2;

[[nodiscard]] int classify(int value) {
    return value < 10 ? 1 : 2;
}

int main() {
    [[maybe_unused]] constexpr auto answer = twice<21>;
    switch (classify(12)) {
    case 1:
        std::cout << "small\n";
        break;
    case 2:
        std::cout << "medium";
        [[fallthrough]];
    default:
        std::cout << '\n';
    }
}
```

属性主要表达意图和触发诊断，不应依赖编译器忽略返回值警告来保证业务正确性。非类型模板参数仍受允许类型范围约束，这一范围在 C++20 中继续扩大。

