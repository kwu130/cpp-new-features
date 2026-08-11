# 类模板实参推导

类模板实参推导（CTAD）根据构造实参和推导指引推断模板参数，减少重复类型书写。

<!-- example id="cpp17-ctad" std="c++17" file="main.cpp" kind="single" compilers="all" output="items=3" -->
```cpp
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename T>
class Box {
public:
    explicit Box(T value) : value_(std::move(value)) {}
    const T& get() const { return value_; }

private:
    T value_;
};

Box(const char*) -> Box<std::string>;

int main() {
    Box box("items=3");
    std::pair point(2, 5);
    std::tuple record(1, std::string("Ada"));
    (void)point;
    (void)record;
    std::cout << box.get() << '\n';
}
```

CTAD 只省略类模板实参，不会把类模板变成普通类型。自定义推导指引应反映构造函数的自然语义，避免同一调用产生意外类型。

## 推导候选如何产生

编译器为类模板的构造函数形成一组虚拟函数模板候选，再结合用户定义推导指引、复制推导候选等规则进行重载解析。选中候选的返回类型就是最终类模板特化类型，之后才真正调用该特化的构造函数。

因此“推导类型”和“构造对象”是两个阶段。推导指引没有函数体，也不在运行时执行；它只声明从参数类型到类模板实参的映射。

## 为什么需要自定义指引

字符串字面量直接按模板推导容易得到 `const char*` 或数组相关类型，而业务容器可能希望拥有 `std::string`。示例的 `Box(const char*) -> Box<std::string>` 把这种策略写在类型接口旁边。

指引过宽会产生悬空或意外复制。例如把任意 `T&` 推导成保存引用的包装器，需要确保包装器语义和生命周期明确。标准库也提供大量指引，让 `pair(1, 2.0)`、`tuple(...)` 等自然工作。

## 与函数模板推导的差异

CTAD 只用于声明对象等需要类类型的语境，不能在函数参数里单独写裸模板名来表达任意特化。复制初始化列表、聚合模板和别名模板的支持还会随标准版本演进，阅读代码时应确认最低语言版本。

## ABI 与可维护性

调用点省略的类型仍是静态具体类型，运行时没有额外成本。但新增构造函数或推导指引可能改变旧调用的重载结果，属于源代码兼容性风险。公共库应测试关键推导表达式的 `decltype`。

## 工程检查清单

只有自然且唯一的类型映射才让用户依赖 CTAD；所有权包装器谨慎处理字符串字面量和引用；用 `static_assert(is_same_v<...>)` 固化重要推导；当显式模板实参更能表达业务含义时不要追求省字。

## 权威资料

- [P0091R3：类模板实参推导](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0091r3.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
