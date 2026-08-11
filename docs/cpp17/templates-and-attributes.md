# 模板参数与属性

C++17 允许 `auto` 非类型模板参数，并标准化了 `[[nodiscard]]`、`[[maybe_unused]]` 和 `[[fallthrough]]` 等常用属性。

<!-- example id="cpp17-templates-attributes" std="c++17" file="main.cpp" kind="single" compilers="all" output="medium" -->
```cpp
#include <iostream>
#include <string>

template <auto Value>
constexpr auto twice = Value * 2;

[[nodiscard]] int classify(int value) {
    return value < 10 ? 1 : 2;
}

int main() {
    [[maybe_unused]] constexpr auto answer = twice<21>;
    switch (classify(12)) {
    case 1:
        std::cout << "small\n";
        break;
    case 2:
        std::cout << "medium";
        [[fallthrough]];
    default:
        std::cout << '\n';
    }
}
```

属性主要表达意图和触发诊断，不应依赖编译器忽略返回值警告来保证业务正确性。非类型模板参数仍受允许类型范围约束，这一范围在 C++20 中继续扩大。

## `auto` 非类型模板参数

非类型模板参数把一个编译期值纳入类型身份。C++14 以前必须先写明值的类型，C++17 的 `template<auto Value>` 让编译器从实参推导类型。`twice<21>` 中参数类型是 `int`，而 `twice<21L>` 会形成不同模板实例。

允许的值仍受非类型模板参数规则限制，主要覆盖整数、枚举、指针等当时可表示的结构。值必须是合适的常量表达式。因为值参与符号和类型身份，大量不同取值会产生大量实例，增加编译与代码尺寸成本。

## 标准属性的语义边界

属性为实现提供结构化元信息。编译器必须识别标准属性的语法，但多数属性影响诊断或优化提示，不改变程序核心语义。

- `[[nodiscard]]` 提醒调用方不要丢弃重要结果；是否诊断及诊断级别由实现决定。
- `[[maybe_unused]]` 抑制有意未使用实体的警告，适合平台条件编译和断言只在调试构建存在的变量。
- `[[fallthrough]]` 只能放在 switch 分支末尾附近，声明落入下一分支是有意行为。

属性放置位置决定它修饰声明、类型还是语句。随意移动可能改变含义或不再合法，应靠近意图对象。

## 底层与性能

`nodiscard` 和 `maybe_unused` 通常只影响前端诊断，不生成运行时代码。`fallthrough` 也主要消除警告，实际控制流仍是普通贯穿。不要把属性当作安全机制；API 仍需通过类型和控制流保证正确。

## 示例解析与工程实践

示例用值模板生成常量，用 `nodiscard` 标记必须处理的分类结果，并显式声明 switch 贯穿。库作者应把 `nodiscard` 用在错误码、资源句柄和纯计算结果上，但避免为所有函数机械添加导致警告疲劳；使用方不应通过无意义强制转换掩盖真正遗漏。

## 权威资料

- [P0127R2：auto 非类型模板参数](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0127r2.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
