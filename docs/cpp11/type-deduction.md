# 类型推导：`auto` 与 `decltype`

## 为什么需要

模板和迭代器类型往往很长。`auto` 根据初始化表达式推导变量类型，`decltype` 则在不求值表达式的情况下取得其类型，使代码既简洁又保持静态类型检查。

## 核心语义

- `auto` 的规则与模板实参推导接近，通常会丢弃顶层 `const` 和引用；需要引用时应显式写 `auto&` 或 `const auto&`。
- `decltype(name)` 对未加括号的变量名给出声明类型。
- `decltype((expression))` 根据表达式值类别可能得到引用类型。

<!-- example id="cpp11-type-deduction" std="c++11" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <iostream>
#include <type_traits>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3};
    auto iterator = values.begin();
    const auto& first = values.front();

    int number = 6;
    decltype(number) copy = number;
    static_assert(std::is_same<decltype((number)), int&>::value,
                  "a parenthesized lvalue produces a reference");
    static_assert(std::is_same<decltype(first), const int&>::value,
                  "the explicit reference is retained");

    std::cout << (*iterator + copy - first) << '\n';
}
```

## 实践建议

当类型由右侧表达式自然决定时使用 `auto`；当具体类型本身表达业务含义时保留显式类型。遍历容器中的大型对象时优先使用 `const auto&`，避免无意复制。

## 易错点

`auto value = {1, 2, 3};` 推导为 `std::initializer_list<int>`，并非普通整数。不要仅为缩短一个清晰的基础类型而滥用 `auto`。

