# `constexpr` 与 `static_assert`

`constexpr` 允许值在满足条件时参与编译期计算，`static_assert` 用于在编译期验证不变量。

<!-- example id="cpp11-compile-time" std="c++11" file="main.cpp" kind="single" compilers="all" output="120" -->
```cpp
#include <iostream>

constexpr unsigned factorial(unsigned value) {
    return value <= 1 ? 1 : value * factorial(value - 1);
}

int main() {
    constexpr unsigned result = factorial(5);
    static_assert(result == 120, "factorial must be evaluated correctly");
    int values[result == 120 ? 1 : -1] = {0};
    std::cout << (result + static_cast<unsigned>(values[0])) << '\n';
}
```

C++11 的 `constexpr` 函数体限制严格，通常只能包含单个返回语句；后续标准逐步放宽。`constexpr` 函数也能在运行期调用，是否常量求值取决于调用上下文和实参。

