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

## `apply` 的展开机制

`apply(function, tuple)` 概念上生成 `0..N-1` 的索引序列，再调用 `invoke(function, get<I>(tuple)...)`。因此它不仅支持 `tuple`，也支持满足 tuple 协议的 `pair`、`array` 和用户类型。

元组的值类别会传播给元素：传右值元组可能把元素作为右值交给函数。透明适配器应正确转发元组，否则会发生额外复制或无法调用只移动参数。

## 异常与返回类型

两者的异常和返回值来自底层调用，不会自行捕获。条件 `noexcept` 包装器可以用 `is_nothrow_invocable` 表达保证。若底层返回引用，`invoke`/`apply` 也保留引用，调用方必须继续遵守生命周期。

## 示例解析与使用边界

示例先由 `apply` 展开二元素元组，Lambda 内再用 `invoke` 调用成员函数指针。真实代码若只调用一个已知成员，直接语法更清楚；这些工具应集中用于任务调度器、反射式字段适配、元组反序列化等真正需要统一调用协议的层。
