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

## 学习目标

读完本章后，应能判断 `auto` 是否保留 `const`、引用和数组属性，能解释 `decltype(x)` 与 `decltype((x))` 的差别，并能在泛型代码中选择值、左值引用或转发引用。

## 推导规则拆解

把 `auto` 想象成模板形参 `T` 很有帮助。对于 `auto value = expression`，编译器近似执行按值形参推导，因此顶层 `const` 和引用被去掉；表达式指向对象的底层 `const` 仍然保留。对于 `auto&`，引用本身不会成为对象类型的一部分，但被引用对象的 cv 限定会保留。

| 声明 | 初始化表达式类型 | 推导结果 |
| --- | --- | --- |
| `auto x = const_int` | `const int` 左值 | `int` |
| `const auto& x = value` | `int` 左值 | `const int&` |
| `auto* x = pointer` | `const int*` | `const int*` |
| `auto&& x = lvalue` | `int` 左值 | `int&`（引用折叠后） |
| `auto&& x = temporary` | `int` 右值 | `int&&` |

`decltype` 不执行模板式推导。若操作数是未加括号的名字或成员访问，它直接返回该实体的声明类型；其他表达式则按值类别决定结果：纯右值得到 `T`，将亡值得到 `T&&`，左值得到 `T&`。因此多一层括号可能改变 API 的返回类型。

## 编译器视角与成本

类型推导完全发生在编译期。编译器在语义分析阶段确定具体类型，之后生成的代码与手写该类型通常没有区别；`auto` 不是 JavaScript 式动态类型，也不会在对象里保存运行期类型标签。

推导后的类型仍参与重载解析、模板实例化和生命周期规则。若推导结果发生变化，源代码虽然仍写着 `auto`，ABI、重载选择或复制成本却可能改变，所以公共接口返回类型的变更仍应按接口变更审查。

## 示例解析

主示例中的迭代器类型由 `values.begin()` 决定。`first` 显式写成 `const auto&`，既不复制元素又阻止修改。两个 `static_assert` 分别验证括号表达式产生左值引用，以及显式引用声明保留底层常量性。

## 常见错误

- 使用 `auto item` 遍历大型对象会逐项复制。
- `std::vector<bool>` 的元素是代理对象；`auto value = bits[0]` 未必得到 `bool`。
- 数组按值推导会退化为指针，使用 `auto&` 才能保留数组类型和长度。
- 从函数返回的代理类型使用 `auto` 保存，可能让临时依赖对象提前失效。

## 工程检查清单

先问“这里需要值还是引用”，再决定是否写 `&`；确认生命周期比引用长；对可能是代理对象的表达式查阅返回类型；在模板边界用 `static_assert` 或类型萃取验证关键推导结论。

## 数组、函数与代理类型

按值推导会执行数组到指针、函数到函数指针的退化。引用形式不会退化，所以泛型函数可以通过数组引用保留长度。这个差异不仅影响类型名称，还决定 `sizeof`、重载和模板参数能否看到原始边界。

`decltype` 不会执行数组退化：对数组变量名使用 `decltype` 得到完整数组类型。对函数名使用 `decltype` 得到函数类型，而不是函数指针。需要声明“与表达式完全一致”的中间类型时，它比 `auto` 更精确。

标准库中的代理引用是另一个高风险区域。`vector<bool>::reference`、某些迭代器解引用结果和表达式模板对象看起来像普通值，却可能只保存对底层对象的间接访问。使用 `auto` 会保存代理本身；若要立即取得业务值，应显式写目标类型。

<!-- example id="cpp11-auto-decltype-arrays" std="c++11" file="main.cpp" kind="single" compilers="all" output="length=3, first=9" -->
```cpp
#include <cstddef>
#include <iostream>
#include <type_traits>

template <std::size_t Size>
std::size_t array_length(const int (&)[Size]) {
    return Size;
}

int main() {
    int values[3] = {1, 2, 3};
    auto pointer = values;
    auto& array = values;
    decltype((values[0])) first = values[0];
    first = 9;

    static_assert(std::is_same<decltype(pointer), int*>::value,
                  "by-value auto decays an array");
    static_assert(std::is_same<decltype(array), int (&)[3]>::value,
                  "auto reference keeps the bound");
    std::cout << "length=" << array_length(array)
              << ", first=" << values[0] << '\n';
}
```

## 选择 `auto` 还是 `decltype`

局部变量由初始化表达式自然决定且不关心精确引用属性时使用 `auto`。需要复制表达式的声明类型、编写尾置返回类型或验证值类别时使用 `decltype`。若接口必须稳定，显式业务类型通常比两者都更容易审查。

## 权威资料

- [自动类型推导与占位类型](https://eel.is/c++draft/dcl.spec.auto)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
