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
