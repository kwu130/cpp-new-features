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

## 编译成本与错误信息

长度 N 的序列会参与模板实例化，过大的序列可能增加编译时间和符号数量。现代标准库通常采用高效的编译器内建或分治生成策略；手写线性递归生成器可能很快达到模板递归深度。

索引越界会在 `get<I>` 实例化处产生长错误。公共包装函数应先用 `static_assert` 验证数量关系，并把复杂实现放入 `detail` 层，让调用者看到更直接的诊断。

## 工程实践

只在确需把类型包映射到位置时使用索引序列；能直接按类型展开就不要引入索引。对外接口隐藏辅助序列参数，并测试空元组、单元素和多元素边界。
