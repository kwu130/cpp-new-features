# 范围 `for`

范围 `for` 直接遍历数组或提供 `begin`/`end` 的对象，消除了手写迭代器边界的样板代码。

<!-- example id="cpp11-range-for" std="c++11" file="main.cpp" kind="single" compilers="all" output="2 4 6" -->
```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3};
    for (auto& value : values) {
        value *= 2;
    }

    for (const auto& value : values) {
        std::cout << value << (value == values.back() ? '\n' : ' ');
    }
}
```

只读遍历通常写成 `const auto&`，原地修改写成 `auto&`。直接写 `auto` 会复制每个元素。遍历期间不要执行可能使当前迭代器失效的容器修改操作。

## 学习目标与展开模型

范围 `for` 不是一种新的容器协议，而是编译器生成普通迭代器循环的语法糖。理解展开形式有助于判断生命周期、查找 `begin`/`end` 的方式以及修改容器时的风险。

C++11 的概念性展开可写成：

```text
auto&& range = range_expression;
for (auto begin = begin-expr, end = end-expr; begin != end; ++begin) {
    item-declaration = *begin;
    loop-body
}
```

数组使用内建边界；类类型优先查找成员 `begin()`/`end()`；其他类型通过关联查找找到自由函数。这里不是简单调用 `std::begin`，因此为自定义类型实现同命名自由函数时应放在类型关联命名空间。

## 生命周期与引用选择

隐藏变量 `auto&& range` 会延长直接绑定临时范围的生命周期。例如遍历一个按值返回的 `vector` 是安全的。但在 C++23 之前，临时范围内部某些中间临时对象的生命周期未必一并延长；链式调用返回内部引用时尤其要小心。

循环变量决定每次解引用后的行为：

- `auto item`：复制元素，修改副本不影响容器。
- `auto& item`：引用可修改元素，不能绑定返回纯右值的迭代器代理。
- `const auto& item`：不复制且只读，是最常用选择。
- `auto&& item`：保留代理和值类别，泛型范围代码更通用。

## 性能与失效规则

语法糖本身没有额外运行时开销，`begin` 和 `end` 通常只求值一次。真正成本来自循环变量是否复制，以及迭代器操作。容器扩容、删除当前元素或重排元素可能使隐藏迭代器失效；此时应改用显式迭代器循环并采用该容器规定的删除模式。

## 示例解析与检查清单

主示例第一轮使用 `auto&` 原地加倍，第二轮使用 `const auto&` 读取。实践中还要确认范围表达式只求值一次是否符合预期、自定义 `begin/end` 是否返回兼容哨兵，以及循环体是否改变容器结构。

## 权威资料

- [范围 for 语句](https://eel.is/c++draft/stmt.ranged)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
