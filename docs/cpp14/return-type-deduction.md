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

## `auto` 返回值推导

普通函数的 `auto` 返回类型在定义可见时由 `return` 表达式推导，规则类似变量 `auto`：顶层引用和 cv 限定通常被移除。递归函数在第一次递归调用前必须已经出现足以推导返回类型的语句，否则编译器无法确定调用签名。

所有非丢弃 `return` 必须推导为同一类型，不会像条件运算符那样自动寻找公共类型。只有裸 `return;` 的函数推导为 `void`。由于调用方编译时需要看到函数体，返回类型推导不适合隐藏实现的传统二进制接口。

## `decltype(auto)` 的精确传播

`decltype(auto)` 使用整个返回表达式的 `decltype` 结果。返回变量名 `return value;` 得到声明类型，返回 `(value)` 则因为括号表达式是左值而得到引用。它适合转发容器元素或包装另一个 API，却也容易无意返回局部引用。

对于 `operator[]` 等可能返回代理对象的接口，`decltype(auto)` 会原样传播代理类型及生命周期约束；普通 `auto` 可能把它复制为代理，也未必得到业务期望的值类型。透明包装器必须明确是否要保持精确类型，还是要物化为值。

## ABI、生命周期与性能

推导发生在编译期，不引入运行时标签。保留引用可以避免复制，但把被包装对象的生命周期和别名暴露给调用方；返回值则更安全地拥有结果，并可利用复制消除和移动。

公开库中若返回类型是实现细节，改变函数体可能改变推导类型并破坏调用方重新编译或 ABI 假设。稳定接口宜显式写返回类型，局部泛型辅助函数更适合推导。

## 示例解析与检查清单

主示例中 `first` 返回带括号的 `front()` 左值，因此调用结果是 `int&`，赋值直接修改容器。检查每个 `decltype(auto)` 返回路径的值类别、被引用对象寿命和代理语义；若不需要透明转发，优先用明确返回类型。

## 权威资料

- [N3638：返回类型推导](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3638.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
