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

萃取的参数类型应与最终调用中的值类别一致。用 `T`、`T&` 和 `T&&` 查询可能得到不同结果，因为调用运算符可以带引用限定符，参数转换也不同。转发包装器通常以 `F&&`、`Args&&...` 查询并在真实表达式里使用相同的 `forward` 形式，避免“萃取说可调用，函数体却采用了另一种值类别”。

`is_invocable_r<R>` 检查的是调用结果可转换为 `R`，不是必须精确等于 `R`。若框架协议需要精确返回类型，应再结合 `is_same`；若 `R` 是 `void`，可调用结果可以被丢弃，这也应是有意的接口决定。

## `apply` 的展开机制

`apply(function, tuple)` 概念上生成 `0..N-1` 的索引序列，再调用 `invoke(function, get<I>(tuple)...)`。因此它不仅支持 `tuple`，也支持满足 tuple 协议的 `pair`、`array` 和用户类型。

元组的值类别会传播给元素：传右值元组可能把元素作为右值交给函数。透明适配器应正确转发元组，否则会发生额外复制或无法调用只移动参数。

元组长度由 `tuple_size` 在编译期决定，每个元素通过 `get<I>` 取出，所以 `apply` 不能展开长度只在运行期知道的 `vector`。它解决的是固定异构积类型到参数列表的适配，而不是一般容器迭代。

把左值元组传入时，元素通常以左值表达式进入调用；`const` 左值产生只读元素；右值元组允许元素按右值转发。若元组仍会被使用，不要为了调用可移动参数而盲目 `std::move(tuple)`。

`make_from_tuple<T>(tuple)` 是相邻设施：它把元组元素展开给 `T` 的构造函数并返回对象。它适合反序列化固定字段或工厂适配，但构造函数的显式性、可访问性与异常仍按普通直接初始化规则处理。

### tuple-like 定制边界

在 C++17 中，标准设施明确支持标准 tuple-like 类型；让用户类型参与相关协议通常涉及 `tuple_size`、`tuple_element` 与 `get<I>` 的一致定义。错误地只提供长度而缺少某个索引访问，会在模板实例化深处产生诊断。每个索引的元素类型、const 传播和值类别应互相一致，不能让 `tuple_element_t<I, T>` 宣称一种类型而 `get<I>` 返回不相容引用。

空元组同样可以用于 `apply`，其效果是无参数调用目标。该边界对通用命令分派很有用，也提醒包装器不能假定参数包至少包含一个元素。

### 手工展开的实现模型

一个典型实现先用 `tuple_size<remove_reference_t<Tuple>>::value` 得到编译期长度，创建 `index_sequence<I...>`，再执行近似 `invoke(forward<F>(f), get<I>(forward<Tuple>(t))...)` 的表达式。索引包只存在于类型系统，不会在运行期循环访问元组。

因此编译成本随元组元素和实例化组合增长，而运行时通常只是一次普通调用。若把巨大 tuple-like 类型通过许多不同访问器展开，需关注编译时间和代码体积；这不是动态反射机制。

## 异常与返回类型

两者的异常和返回值来自底层调用，不会自行捕获。条件 `noexcept` 包装器可以用 `is_nothrow_invocable` 表达保证。若底层返回引用，`invoke`/`apply` 也保留引用，调用方必须继续遵守生命周期。

C++17 的 `invoke` 返回类型写作 `invoke_result_t` 所描述的类型，`void` 返回同样被正确处理。统一调用层不要把结果无条件存进 `auto value`，否则 `void` 调用不合法、引用结果也可能被意外复制；可以用 `if constexpr` 按结果类别分支。

成员指针本身不拥有对象。将成员函数指针和临时对象排入异步队列时，即便表达式在类型上可调用，执行时仍可能悬空。调度器应明确对象所有权，必要时保存 `shared_ptr` 或具有稳定生命周期的句柄。

调用空函数指针、空成员指针，或让指针式对象实参解引用无效地址，均不会因为经过 `invoke` 而得到保护。`invoke` 统一的是语法和类型规则，不是动态有效性检查。

返回成员数据时结果可能是左值引用、const 引用或在临时对象情形下形成不同值类别。若包装函数简单写成 `auto` 返回，会丢失引用；需要透明传播时应使用 `decltype(auto)`，并同时证明返回引用不会指向即将销毁的临时对象。

## 与 `function`、直接调用的关系

`std::function` 做运行期类型擦除并拥有可复制调用目标；`invoke` 是编译期语法统一，不存储任何目标。模板算法若已知 `F` 类型，通常直接转发并 `invoke`，不必先包装成 `function`，从而保留内联机会和移动语义。

普通 `f(args...)` 对函数对象已经最清楚。只有代码还要覆盖成员指针等完整 INVOKE 协议，或者需要与标准可调用性萃取保持一致时，`std::invoke` 才体现价值。

## 示例解析与使用边界

示例先由 `apply` 展开二元素元组，Lambda 内再用 `invoke` 调用成员函数指针。真实代码若只调用一个已知成员，直接语法更清楚；这些工具应集中用于任务调度器、反射式字段适配、元组反序列化等真正需要统一调用协议的层。

## 调用协议速查

| 设施 | 关键语义 |
| --- | --- |
| `invoke(f,args...)` | 调普通函数、函数对象和 Lambda |
| 成员函数指针 | 首个对象实参可为对象、reference_wrapper 或指针式对象 |
| 成员数据指针 | 返回成员访问表达式并保留引用类别 |
| `invoke_result_t` | 在未求值语境得到 INVOKE 结果类型 |
| `is_invocable_v` | 检查表达式形成，不验证运行期前置条件 |
| `is_invocable_r_v<R>` | 检查结果可转换为 R，不要求精确相同 |
| `is_nothrow_invocable_v` | 检查调用表达式 noexcept 性质 |
| `apply(f,tuple)` | 用 get<I> 展开固定 tuple-like 参数 |
| 右值 tuple | 元素值类别可转发为右值 |
| `make_from_tuple<T>` | 展开元素直接构造 T |

## 权威资料

- [P0209R2：invoke](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0209r2.html)
- [工作草案：Function object wrappers](https://eel.is/c++draft/function.objects)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
