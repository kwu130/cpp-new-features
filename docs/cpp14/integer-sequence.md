# `integer_sequence`

`integer_sequence` 和 `index_sequence` 在编译期表示整数序列，常用于按索引展开元组或参数包。

<!-- example id="cpp14-integer-sequence" std="c++14" file="main.cpp" kind="single" compilers="all" output="Ada 37" -->
```cpp
#include <cstddef>
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename Tuple, std::size_t... Indexes>
void print_tuple(const Tuple& values, std::index_sequence<Indexes...>) {
    using expand = int[];
    (void)expand{0, ((std::cout << (Indexes == 0 ? "" : " ")
                                 << std::get<Indexes>(values)), 0)...};
    std::cout << '\n';
}

template <typename... Values>
void print_tuple(const std::tuple<Values...>& values) {
    print_tuple(values, std::index_sequence_for<Values...>{});
}

int main() {
    print_tuple(std::make_tuple(std::string("Ada"), 37));
}
```

这种展开方式在 C++17 中通常可由折叠表达式简化。编写公共接口时优先隐藏索引序列，让调用者只面对普通参数。

## 编译期序列是什么

`integer_sequence<T, values...>` 只在类型中携带一组整数，不保存运行期数组。`index_sequence` 是以 `size_t` 为元素类型的别名，`make_index_sequence<N>` 生成 `0` 到 `N-1`，`index_sequence_for<Ts...>` 则按类型包长度生成索引。

它解决了“参数包没有内建下标”的问题：先生成索引包，再把每个索引放入 `get<I>` 等需要编译期常量的位置。序列对象本身通常是空对象，优化后没有运行时成本。

## 展开过程

示例中二元素元组让 `Indexes...` 成为 `0, 1`。初始化列表里的模式会生成两条输出表达式。C++11/14 初始化列表保证元素从左到右求值，因此常被用来实现带副作用的有序包展开；前置的 `0` 让空包时数组仍合法。

这种技巧可读性有限，C++17 折叠表达式能直接表达逗号折叠。但索引序列本身仍广泛用于元组转换、结构化序列化和调用适配。

## 用索引序列解包元组

C++14 没有 `std::apply`。若要把一个元组的每个元素作为独立实参传给可调用对象，需要先生成与元组长度相同的索引序列，再在实现函数中展开 `get<Indexes>(tuple)...`。这是 `integer_sequence` 最具代表性的用途。

<!-- example id="cpp14-index-sequence-invoke" std="c++14" file="main.cpp" kind="single" compilers="all" output="result=14" -->
```cpp
#include <cstddef>
#include <iostream>
#include <tuple>
#include <type_traits>
#include <utility>

int weighted_sum(int first, int second, int third) {
    return first + 2 * second + 3 * third;
}

template <typename Function, typename Tuple, std::size_t... Indexes>
auto invoke_tuple_impl(Function&& function, Tuple&& arguments,
                       std::index_sequence<Indexes...>)
    -> decltype(std::forward<Function>(function)(
        std::get<Indexes>(std::forward<Tuple>(arguments))...)) {
    return std::forward<Function>(function)(
        std::get<Indexes>(std::forward<Tuple>(arguments))...);
}

template <typename Function, typename Tuple>
auto invoke_tuple(Function&& function, Tuple&& arguments)
    -> decltype(invoke_tuple_impl(
        std::forward<Function>(function),
        std::forward<Tuple>(arguments),
        std::make_index_sequence<
            std::tuple_size<typename std::decay<Tuple>::type>::value>{})) {
    using tuple_type = typename std::decay<Tuple>::type;
    constexpr std::size_t size = std::tuple_size<tuple_type>::value;
    return invoke_tuple_impl(std::forward<Function>(function),
                             std::forward<Tuple>(arguments),
                             std::make_index_sequence<size>{});
}

int main() {
    const auto arguments = std::make_tuple(1, 2, 3);
    std::cout << "result=" << invoke_tuple(weighted_sum, arguments) << '\n';
}
```

外层 `invoke_tuple` 负责从 `tuple_size` 取得长度，生成 `index_sequence<0, 1, 2>`；内层函数才真正展开调用。两层都使用转发引用，使右值元组中的元素仍能按右值传递。`decay` 仅用于移除引用和 cv 限定，以便查询 `tuple_size`，并不会复制实参。

尾置返回类型中的 `decltype` 同时承担返回类型推导和约束作用：只有展开后的调用表达式有效，该函数模板才可用。这个 C++14 写法在错误场景下诊断可能较长；C++17 的 `std::apply` 封装了同一模式，业务代码通常应直接使用标准设施。

## 接口成员与类型不变量

`integer_sequence<T, Ints...>` 暴露 `value_type`，并提供静态 `size()` 返回序列长度。序列中的每个值都必须能表示为 `T`；`make_integer_sequence<T, N>` 要求 `N` 非负，生成半开区间 `[0, N)`。它生成的是类型而非某个全局表，因此同一序列可以直接用 `{}` 构造空对象作为重载标签。

`index_sequence_for<Ts...>` 只关心类型包的元素数量，不读取这些类型的任何性质。对于 `index_sequence_for<A, B, C>`，结果就是 `index_sequence<0, 1, 2>`。它特别适合某个类型包与另一个值包按位置一一对应的场景。

## 典型实现原理

概念性实现可递归地把 `N-1` 追加到较短序列末尾，直到零。但线性递归会产生 O(N) 层模板实例化深度。标准只规定生成结果，不规定算法；实现可以使用分治、编译器内建或其他方式减少实例化深度。

序列展开后，编译器看到的是一组普通模板实参。`get<0>`、`get<1>` 等调用分别实例化，优化器通常能完全消除用于传递序列的空对象。所谓“零运行时开销”主要指索引生成与分派发生在编译期，不代表被展开的每个操作本身没有成本。

## 边界与误用

- 空序列合法；实现必须避免创建零长度原生数组等非标准结构。
- `integer_sequence<int, 2, 4>` 可以表达非连续序列，但 `make_integer_sequence` 只生成从零开始的连续序列。
- 不要把很大的运行期数据规模硬编码成索引包；每个索引都可能触发模板实例化并放大编译成本。
- 若只是对函数参数包执行同一种操作，可以直接展开参数包，无需先制造索引。
- 当索引对应多个异构结构时，应在入口处用 `static_assert` 检查长度一致，避免深层 `get<I>` 才报错。

## 编译成本与错误信息

长度 N 的序列会参与模板实例化，过大的序列可能增加编译时间和符号数量。现代标准库通常采用高效的编译器内建或分治生成策略；手写线性递归生成器可能很快达到模板递归深度。

索引越界会在 `get<I>` 实例化处产生长错误。公共包装函数应先用 `static_assert` 验证数量关系，并把复杂实现放入 `detail` 层，让调用者看到更直接的诊断。

## 工程实践

只在确需把类型包映射到位置时使用索引序列；能直接按类型展开就不要引入索引。对外接口隐藏辅助序列参数，并测试空元组、单元素和多元素边界。

## 权威资料

- [N3658：整数序列](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3658.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
