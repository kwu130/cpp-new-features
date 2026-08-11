# `apply` 与 `invoke`

`apply` 把元组展开为函数实参，`invoke` 以统一语法调用普通函数、函数对象和成员指针。

<!-- example id="cpp17-invoke-apply" std="c++17" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <functional>
#include <iostream>
#include <tuple>

struct Calculator {
    int multiply(int left, int right) const { return left * right; }
};

int main() {
    const Calculator calculator;
    const auto arguments = std::make_tuple(6, 7);
    const int result = std::apply(
        [&calculator](int left, int right) {
            return std::invoke(&Calculator::multiply, calculator, left, right);
        },
        arguments);
    std::cout << result << '\n';
}
```

这些工具适合泛型适配层。普通直接调用仍然更清晰，不必为了统一形式而无条件使用 `invoke`。

