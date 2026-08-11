# 返回类型推导与 `decltype(auto)`

C++14 允许普通函数使用 `auto` 推导返回类型。`decltype(auto)` 按 `decltype` 规则保留引用和值类别，适合编写透明包装器。

<!-- example id="cpp14-return-deduction" std="c++14" file="main.cpp" kind="single" compilers="all" output="9" -->
```cpp
#include <iostream>
#include <type_traits>
#include <vector>

auto answer() {
    return 42;
}

template <typename Container>
decltype(auto) first(Container& container) {
    return (container.front());
}

int main() {
    std::vector<int> values{3, 6};
    first(values) = 9;
    static_assert(std::is_same<decltype(first(values)), int&>::value,
                  "decltype(auto) keeps the reference");
    static_assert(std::is_same<decltype(answer()), int>::value,
                  "auto produces a value type");
    std::cout << values.front() << '\n';
}
```

返回类型推导要求同一函数中的所有返回语句推导出一致类型。使用 `decltype(auto)` 时，表达式外是否有括号可能改变结果；不要返回局部变量的引用。

