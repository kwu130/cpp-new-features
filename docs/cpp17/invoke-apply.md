# `apply` 与 `invoke`

`apply` 把元组展开为函数实参，`invoke` 以统一语法调用普通函数、函数对象和成员指针。

<!-- example id="cpp17-invoke-apply" std="c++17" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <functional>
#include <iostream>
#include <tuple>

struct Calculator {
    int multiply(int left, int right) const { return left * right; }
};

int main() {
    const Calculator calculator;
    const auto arguments = std::make_tuple(6, 7);
    const int result = std::apply(
        [&calculator](int left, int right) {
            return std::invoke(&Calculator::multiply, calculator, left, right);
        },
        arguments);
    std::cout << result << '\n';
}
```

这些工具适合泛型适配层。普通直接调用仍然更清晰，不必为了统一形式而无条件使用 `invoke`。

## `invoke` 统一了哪些调用

泛型代码面对的可调用对象可能是函数、函数指针、函数对象、Lambda、成员函数指针或成员数据指针。成员指针还可以配合对象、指针或 `reference_wrapper`。`std::invoke` 把这些分支统一成一个表达式，并按标准规则选择正确语法。

它不会进行运行期类型擦除；传入类型在编译期已知，调用通常可内联。`invoke_result`、`is_invocable` 等萃取可在不真正调用的情况下查询结果类型和可调用性，是通用回调框架的基础。

成员函数指针需要一个“对象实参”，该实参可以是对象/派生对象、`reference_wrapper`，或可解引用后得到合适对象的指针式类型。成员数据指针采用同一对象解析规则，但结果是成员访问表达式而不是函数调用。

<!-- example id="cpp17-invoke-member-data" std="c++17" file="main.cpp" kind="single" compilers="all" output="before=7, after=9" -->
```cpp
#include <functional>
#include <iostream>
#include <type_traits>

struct Record {
    int value;
};

int main() {
    Record record{7};
    int& member = std::invoke(&Record::value, std::ref(record));
    static_assert(std::is_same_v<decltype(member), int&>);

    std::cout << "before=" << member;
    member = 9;
    std::cout << ", after=" << record.value << '\n';
}
```

调用成员数据指针保留引用和值类别。示例通过 `reference_wrapper<Record>` 找到原对象，得到 `int&` 并修改成员。若对象是 `const Record`，相应结果会带 `const`，不能通过 `invoke` 绕过 const 正确性。

### `invoke_result` 与可调用性萃取

`invoke_result_t<F, Args...>` 给出按 `invoke` 规则调用后的结果类型，替代旧 `result_of` 的许多使用场景。`is_invocable_v` 检查表达式是否形成，`is_invocable_r_v<R, ...>` 还检查结果是否可转换为 `R`；`is_nothrow_invocable_v` 系列检查调用是否为不抛表达式。

这些萃取基于未求值语境，不执行函数。它们适合 SFINAE、静态断言和条件 `noexcept`，但不能保证运行期前置条件，例如指针非空、对象仍存活或业务参数范围正确。

## `apply` 的展开机制

`apply(function, tuple)` 概念上生成 `0..N-1` 的索引序列，再调用 `invoke(function, get<I>(tuple)...)`。因此它不仅支持 `tuple`，也支持满足 tuple 协议的 `pair`、`array` 和用户类型。

元组的值类别会传播给元素：传右值元组可能把元素作为右值交给函数。透明适配器应正确转发元组，否则会发生额外复制或无法调用只移动参数。

元组长度由 `tuple_size` 在编译期决定，每个元素通过 `get<I>` 取出，所以 `apply` 不能展开长度只在运行期知道的 `vector`。它解决的是固定异构积类型到参数列表的适配，而不是一般容器迭代。

把左值元组传入时，元素通常以左值表达式进入调用；`const` 左值产生只读元素；右值元组允许元素按右值转发。若元组仍会被使用，不要为了调用可移动参数而盲目 `std::move(tuple)`。

`make_from_tuple<T>(tuple)` 是相邻设施：它把元组元素展开给 `T` 的构造函数并返回对象。它适合反序列化固定字段或工厂适配，但构造函数的显式性、可访问性与异常仍按普通直接初始化规则处理。

## 异常与返回类型

两者的异常和返回值来自底层调用，不会自行捕获。条件 `noexcept` 包装器可以用 `is_nothrow_invocable` 表达保证。若底层返回引用，`invoke`/`apply` 也保留引用，调用方必须继续遵守生命周期。

C++17 的 `invoke` 返回类型写作 `invoke_result_t` 所描述的类型，`void` 返回同样被正确处理。统一调用层不要把结果无条件存进 `auto value`，否则 `void` 调用不合法、引用结果也可能被意外复制；可以用 `if constexpr` 按结果类别分支。

成员指针本身不拥有对象。将成员函数指针和临时对象排入异步队列时，即便表达式在类型上可调用，执行时仍可能悬空。调度器应明确对象所有权，必要时保存 `shared_ptr` 或具有稳定生命周期的句柄。

## 与 `function`、直接调用的关系

`std::function` 做运行期类型擦除并拥有可复制调用目标；`invoke` 是编译期语法统一，不存储任何目标。模板算法若已知 `F` 类型，通常直接转发并 `invoke`，不必先包装成 `function`，从而保留内联机会和移动语义。

普通 `f(args...)` 对函数对象已经最清楚。只有代码还要覆盖成员指针等完整 INVOKE 协议，或者需要与标准可调用性萃取保持一致时，`std::invoke` 才体现价值。

## 示例解析与使用边界

示例先由 `apply` 展开二元素元组，Lambda 内再用 `invoke` 调用成员函数指针。真实代码若只调用一个已知成员，直接语法更清楚；这些工具应集中用于任务调度器、反射式字段适配、元组反序列化等真正需要统一调用协议的层。

## 权威资料

- [P0209R2：invoke](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0209r2.html)
- [工作草案：Function object wrappers](https://eel.is/c++draft/function.objects)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
