# `consteval`、`constinit` 与扩展 `constexpr`

`consteval` 函数必须在编译期求值；`constinit` 保证静态或线程存储期对象进行静态初始化，但不会让对象自动变成常量。C++20 继续扩大 `constexpr` 可执行操作范围。

<!-- example id="cpp20-compile-time" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <array>
#include <iostream>

consteval int twice(int value) {
    return value * 2;
}

constexpr int sum(std::array<int, 3> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

constinit int runtime_counter = twice(20);

int main() {
    constexpr int offset = sum({0, 1, 1});
    ++runtime_counter;
    std::cout << runtime_counter + offset - 1 << '\n';
}
```

`constinit` 与 `constexpr` 解决不同问题：前者约束初始化时机，后者约束对象可变性与常量表达式资格。只在调用本质上必须编译期完成时使用 `consteval`。

