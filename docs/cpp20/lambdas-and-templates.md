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

## 显式模板参数列表

C++14 泛型 Lambda 的每个 `auto` 参数对应隐式模板参数，却无法方便地命名其基础类型。C++20 允许在捕获列表后写 `[]<typename T>(...)`，其规则接近普通函数模板，可声明类型、非类型和参数包，并添加 Concepts 约束。

这使多个参数共享同一 T、显式取得数组长度、对参数包整体约束等模式更直接。闭包类型仍是唯一的匿名类，调用运算符成为成员函数模板；运行期没有新增反射信息。

## 捕获 `this` 的演进

C++20 中在 `[=]` 下隐式捕获 `this` 被弃用，因为它表面像按值捕获，实际只复制指针。需要成员访问时应显式写 `[this]`，需要对象快照则使用 `[*this]`，并考虑复制成本与多态切片语义。

初始化捕获还可配合参数包展开，把一组对象分别移入闭包。每个捕获成员的可复制/可移动性质共同决定闭包特殊成员。

## 模板 Lambda 作为局部算法

显式模板 Lambda 很适合只在一个函数内使用的类型算法，避免为小逻辑创建命名辅助模板。若约束、重载或文档需求增长，应提升为命名 Concept 和函数，防止局部表达式变成难以诊断的大型模板。

## 示例解析与成本

示例把参数约束为 `integral`，并在函数体内以同一 T 保存累加结果。每种整数向量类型会实例化独立调用运算符，编译器通常内联循环。大量不同 T 仍会导致模板代码膨胀，应与普通命名模板一样关注构建成本。

## 工程检查清单

简单独立参数用 `auto`；需要复用类型名或约束时用显式列表；长期闭包明确 `this` 所有权；接口级逻辑优先命名模板；为约束失败和大对象捕获添加测试与性能检查。

## 权威资料

- [P0428R2：Lambda 模板参数列表](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0428r2.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
