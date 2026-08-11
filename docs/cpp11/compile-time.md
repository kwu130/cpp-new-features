# `constexpr` 与 `static_assert`

`constexpr` 允许值在满足条件时参与编译期计算，`static_assert` 用于在编译期验证不变量。

<!-- example id="cpp11-compile-time" std="c++11" file="main.cpp" kind="single" compilers="all" output="120" -->
```cpp
#include <iostream>

constexpr unsigned factorial(unsigned value) {
    return value <= 1 ? 1 : value * factorial(value - 1);
}

int main() {
    constexpr unsigned result = factorial(5);
    static_assert(result == 120, "factorial must be evaluated correctly");
    int values[result == 120 ? 1 : -1] = {0};
    std::cout << (result + static_cast<unsigned>(values[0])) << '\n';
}
```

C++11 的 `constexpr` 函数体限制严格，通常只能包含单个返回语句；后续标准逐步放宽。`constexpr` 函数也能在运行期调用，是否常量求值取决于调用上下文和实参。

## 常量表达式的作用

常量表达式可以参与数组边界、枚举值、非类型模板实参和 `static_assert`。把错误提前到编译期能够缩短反馈周期，也允许编译器预计算结果并把常量直接写入目标文件。

`constexpr` 变量必须由常量表达式初始化且隐含 `const`。`constexpr` 函数表示“具备常量求值资格”，不是“每次调用都发生在编译期”；当实参不是常量或调用上下文不要求常量时，它就是普通函数调用。

## C++11 规则边界

C++11 的非构造 `constexpr` 函数体基本只能包含一条 `return`，因此循环通常写成递归和条件表达式。函数必须返回字面类型，常量求值路径不能执行未定义行为、调用非 `constexpr` 函数或访问不允许的可变状态。

`constexpr` 构造函数使自定义类型成为编译期值对象，但每个成员都必须被初始化，并受到字面类型规则约束。后续标准放宽了函数体、局部变量和标准库可用范围，阅读代码时要核对最低标准版本。

## 编译器求值模型

前端解释执行常量表达式，并监控是否违反常量求值规则。成功时产生一个编译期值；失败并不总是错误——若上下文不要求常量，编译器可以生成运行时代码。只有数组边界、`static_assert` 等强制常量上下文才必须诊断。

常量求值不保证零编译成本。复杂递归会消耗编译器时间、内存和递归深度；把大规模计算搬到编译期应测量整体构建成本。

## `static_assert` 的设计价值

`static_assert(condition, message)` 在模板实例化位置验证类型大小、对齐、能力或业务不变量。相比等待深层表达式失败，它能提供更靠近接口的错误。断言应描述要求和修复方向，不要只重复条件文本。

## 示例解析与实践

示例的 `factorial(5)` 位于 `constexpr` 变量初始化中，强制编译期求值；随后 `static_assert` 再验证结果。普通运行期输入仍可以调用同一函数。实践中应让编译期函数保持纯粹、输入规模受控，并为关键边界增加静态断言。
