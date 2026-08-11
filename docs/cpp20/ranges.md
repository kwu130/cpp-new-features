# Ranges 与 Views

Ranges 算法直接接受范围；Views 则以惰性、非拥有方式组合过滤和转换，管道语法让数据流更清晰。

<!-- example id="cpp20-ranges" std="c++20" file="main.cpp" kind="single" compilers="all" output="4 16" -->
```cpp
#include <iostream>
#include <ranges>
#include <vector>

int main() {
    const std::vector<int> values{1, 2, 3, 4, 5};
    auto squares = values
        | std::views::filter([](int value) { return value % 2 == 0; })
        | std::views::transform([](int value) { return value * value; });

    bool first = true;
    for (const int value : squares) {
        std::cout << (first ? "" : " ") << value;
        first = false;
    }
    std::cout << '\n';
}
```

View 通常不拥有底层数据，必须保证源范围生命周期足够长。惰性求值意味着转换可能在每次迭代时重复执行；需要稳定结果或多次遍历时应考虑物化到容器。
