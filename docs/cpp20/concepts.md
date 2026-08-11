# Concepts 与约束

Concepts 为模板参数声明可读、可组合的约束，让重载选择更明确，也能把模板错误定位到接口边界。

<!-- example id="cpp20-concepts" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <concepts>
#include <iostream>

template <typename T>
concept Arithmetic = std::integral<T> || std::floating_point<T>;

template <Arithmetic T>
T twice(T value) {
    return value + value;
}

template <typename T>
requires std::integral<T> && (sizeof(T) >= 4)
T add(T left, T right) {
    return left + right;
}

int main() {
    static_assert(Arithmetic<double>);
    std::cout << add(twice(10), 22) << '\n';
}
```

Concept 应描述调用者真正依赖的语义能力，而不是只罗列碰巧使用的具体类型。优先复用标准 Concept，并把复杂约束拆成有业务含义的命名 Concept。

## 从 SFINAE 到约束系统

C++20 之前常把 `enable_if` 放进返回类型或模板参数，通过替换失败移除候选。这能工作，但接口难读，失败位置可能深入实现。Concept 把“哪些类型可用”提升为声明的一部分，编译器在重载解析期间规范化并比较约束。

约束失败不是函数体编译失败：不满足的模板通常不会成为可行候选，诊断能指出哪个原子约束为假。函数体仍应只使用约束承诺的操作，否则错误依然会出现在实例化深处。

## 定义与使用形式

Concept 是产生布尔常量的命名模板，可由类型萃取、其他 Concept 和 requires-expression 组成。使用方式包括受约束模板参数、尾部 `requires`、缩写函数模板参数以及 `requires` 子句。

`requires` 表达式可以检查表达式是否有效、返回类型是否满足 Concept、操作是否 `noexcept`，而不真正执行表达式。它描述的是语法和部分静态性质；诸如“加法满足结合律”这样的语义要求只能由文档和测试约束。

## 约束规范化与偏序

编译器把约束拆成原子约束并进行合取、析取规范化。更受约束的候选可在重载中优先，但逻辑上等价的不同写法未必产生相同原子身份。应复用命名 Concept，而不是到处重写相似布尔表达式，否则可能出现意外歧义。

短路规则让 `A<T> && B<T>` 在 A 不满足时不实例化 B，这对于先验证类型存在某成员、再检查成员性质很重要。

## 编译器与运行时成本

Concept 完全在编译期工作，不为对象增加标签或虚调用。它可能增加约束检查工作，也常通过更早终止无效实例化改善诊断和构建体验。满足约束后的函数仍是普通模板实例。

## 示例解析与设计检查

示例把算术类别命名为 `Arithmetic`，又在 `add` 上增加“整数且至少四字节”的约束。真实 Concept 应尽量基于操作能力而非 `sizeof` 等偶然表示。审查时确认名称表达语义、约束不强于实现需要、重载之间存在明确偏序，并为不满足调用保留可理解诊断。

## 权威资料

- [约束与 Concepts](https://eel.is/c++draft/temp.constr)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
