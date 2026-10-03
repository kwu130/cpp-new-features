# `integer_sequence`

阅读前建议先了解：[参数包](../cpp11/templates.md)、[tuple 访问](../cpp11/functional-tools.md#先分别使用-tuple-与类型萃取)。本篇介绍的新增能力属于 C++14；后续版本差异会另行标注。

## 为什么普通循环不够用

访问一个 tuple 的两个元素，可以手写 `std::get<0>(record)`、`std::get<1>(record)`。但想处理任意长度的 tuple 时，不能简单把它改成 `std::get<i>(record)`：普通 for 循环中的 `i` 在运行时变化，而 `get` 的下标必须在编译期确定。

`integer_sequence` 提供一组可以放进模板参数的整数。最常用的 `make_index_sequence<3>` 表示 `0, 1, 2`。先生成这些索引，再用参数包展开，就能生成 `get<0>`、`get<1>` 等访问。

固定的两个字段直接访问即可；只有要按位置处理任意长度参数包时，才需要这个工具。

## 最小示例：先看生成了哪些索引

先不处理 tuple。下面把索引包放进数组，观察生成结果：

```cpp example id="cpp14-index-sequence-basic" std="c++14" file="main.cpp" kind="single" compilers="all" output="0 1 2"
#include <array>
#include <cstddef>
#include <iostream>
#include <utility>

template <std::size_t... Indexes>
void print_indices(std::index_sequence<Indexes...>) {
    const std::array<std::size_t, sizeof...(Indexes)> values{{Indexes...}};
    for (std::size_t i = 0; i < values.size(); ++i) {
        std::cout << (i == 0 ? "" : " ") << values[i];
    }
    std::cout << '\n';
}

int main() {
    print_indices(std::make_index_sequence<3>{});
}
```

`make_index_sequence<3>{}` 创建的参数让编译器推导出 `Indexes...` 为 `0, 1, 2`。因此数组初始化相当于 `values{{0, 1, 2}}`，普通循环最终打印三个数字。

这里有两个不同的步骤：索引包在编译时展开；for 循环在运行时输出数组。索引序列本身没有数组、迭代器或 `operator[]`，示例中的数组是我们另行创建的。

## 用生成的索引逐项访问 tuple

下面处理一个姓名和年龄组成的 tuple。先看 `main`，再看两个 `print_tuple`：外层只负责生成索引，内层用索引取元素。

```cpp example id="cpp14-integer-sequence" std="c++14" file="main.cpp" kind="single" compilers="all" output="Ada 37"
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

对本例而言，`index_sequence_for<Values...>` 生成 `0, 1`，`get<Indexes>(values)...` 的访问位置就对应姓名和年龄。输出为 `Ada 37`。

难读的部分是 C++14 的有序输出技巧，可以单独拆开理解：

- `using expand = int[]` 给整数数组类型起一个名字。
- `(输出表达式, 0)` 先输出，再得到整数 0，供数组初始化使用。
- 初始化列表中的元素从左到右求值，因而按索引顺序输出。
- 最前面的 `0` 让空 tuple 也不会产生不合法的零长度原生数组。

这段技巧不是索引序列的核心。C++17 可以用[逗号折叠](../cpp17/fold-expressions.md)简化输出，但 `get<I>` 仍然需要索引包。

## 自定义顺序和选取

生成器给出从零开始的连续索引；也可以直接写 `index_sequence<2, 0>`，只访问第三项和第一项。

```cpp example id="cpp14-index-sequence-select" std="c++14" file="main.cpp" kind="single" compilers="all" output="third first"
#include <cstddef>
#include <iostream>
#include <string>
#include <tuple>
#include <utility>

template <typename Tuple, std::size_t... Indexes>
void print_selected(const Tuple& values, std::index_sequence<Indexes...>) {
    using expand = int[];
    bool first = true;
    (void)expand{0, ((std::cout << (first ? "" : " ")
                               << std::get<Indexes>(values),
                      first = false), 0)...};
    std::cout << '\n';
}

int main() {
    const auto words = std::make_tuple(
        std::string("first"), std::string("second"), std::string("third"));
    print_selected(words, std::index_sequence<2, 0>{});
}
```

输出 `third first`，中间元素没有被访问。实际接口可以由字段映射生成这个序列，不必让业务调用者手写索引。

## 进阶：用索引序列解包元组

如果只是要把 tuple 元素传给函数，C++17 起可以使用 [`std::apply`](../cpp17/invoke-apply.md)。下面保留 C++14 实现，供理解库内部工作方式；第一次阅读可以先跳过。

```cpp example id="cpp14-index-sequence-invoke" std="c++14" file="main.cpp" kind="single" compilers="all" output="result=14"
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

把这个例子分三层看：

1. `main` 希望执行 `weighted_sum(1, 2, 3)`，只是实参保存在 tuple 中。
2. 外层 `invoke_tuple` 查询 tuple 长度，生成 `index_sequence<0, 1, 2>`。`decay` 在此去掉引用及 cv 限定，便于查询类型；它没有复制实参。
3. 内层 `invoke_tuple_impl` 把 `get<Indexes>(arguments)...` 展开为三个实参，计算 `1 + 2 * 2 + 3 * 3`，得到 14。

两层的 `forward` 保留左值或右值的传递方式。返回类型中的 `decltype` 获取调用结果类型；替换模板参数时若该表达式无效，对应重载会退出候选，这种机制称为 SFINAE。理解索引生成时不必同时掌握这部分，可以稍后结合[完美转发](../cpp11/move-semantics.md#完美转发与引用折叠)阅读。

## 注意事项

空序列是合法的；使用者要确保展开零项仍有意义。手写序列可以重复、逆序或越界，序列类型不会替目标 tuple 检查下标。对右值 tuple 重复选取同一元素，可能把同一对象移动两次。

C++14 中，把 `get<I>(tuple)...` 展开成函数实参，不保证实参从左到右求值；有顺序要求的副作用应使用保证顺序的方式，例如上面的初始化列表。同时展开多个参数包时，它们的长度必须匹配。

如果数据类型相同、数量在运行时变化，普通容器和循环通常更合适。巨大索引包会增加模板实例化和代码体积，不能因为索引在编译期生成就认为所有操作都没有成本。

## 深入理解：接口和生成过程

| 写法 | 含义 |
| --- | --- |
| `integer_sequence<T, Values...>` | 用整数类型 T 表示给定值包 |
| `index_sequence<Indexes...>` | T 固定为 `std::size_t` |
| `make_integer_sequence<T, N>` | 生成 T 类型的 `0` 到 `N-1`；N 必须是非负常量 |
| `make_index_sequence<N>` | 生成 `std::size_t` 类型的 `0` 到 `N-1` |
| `index_sequence_for<Types...>` | 按类型数量生成索引，不读取各类型的内容 |
| `Sequence::value_type` | 序列的整数类型 |
| `Sequence::size()` | 值的数量，不是最大索引加一 |

序列值存放在模板参数中，对象通常为空。传一个这样的对象，是为了让辅助函数从其类型中推导整数包；也可以用类模板特化匹配它，无需创建对象。

标准规定生成结果，不规定算法。简单实现可以逐层递归追加整数，但模板深度随 N 增长；库实现也可以采用分治或编译器内建。生成本身即使很快，后续 N 次访问仍要逐项检查类型，编译成本并不会消失。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp14/integer-sequence.md
```

## 权威资料

- [N3658：整数序列](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3658.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
