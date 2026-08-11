# 可变参数模板与类型别名

可变参数模板允许模板接受任意数量的类型或值参数。别名模板用 `using` 为一族类型定义更易读的名称。

<!-- example id="cpp11-variadic-templates" std="c++11" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <iostream>
#include <memory>

template <typename T>
T sum(T value) {
    return value;
}

template <typename T, typename... Rest>
T sum(T first, Rest... rest) {
    return first + sum(rest...);
}

template <typename T>
using Owner = std::unique_ptr<T>;

int main() {
    Owner<int> result(new int(sum(1, 2, 3)));
    std::cout << *result << '\n';
}
```

C++11 中通常通过递归展开参数包，并提供终止重载。C++17 的折叠表达式会显著简化这种代码。参数包展开的上下文和求值顺序需要单独确认，不要假设函数实参按书写顺序求值。

