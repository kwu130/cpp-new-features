# Lambda 与模板增强

C++20 允许 Lambda 使用显式模板参数列表，复杂泛型回调可以直接命名参数类型，并对它们施加约束。

<!-- example id="cpp20-lambda-templates" std="c++20" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <concepts>
#include <iostream>
#include <vector>

int main() {
    const auto sum = []<std::integral T>(const std::vector<T>& values) {
        T result{};
        for (const T value : values) {
            result += value;
        }
        return result;
    };

    std::cout << sum(std::vector<int>{1, 2, 3}) << '\n';
}
```

显式模板列表适合需要引用同一模板参数多次或添加约束的 Lambda；简单场景继续使用 `auto` 参数通常更清晰。

