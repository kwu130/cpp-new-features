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

概念接口包含：`using value_type = T;`、静态 `size()`，以及模板参数包本身。序列没有 operator[]、迭代器或运行期 data，因为值只存在于类型参数列表中。要在函数体取得每个值，必须通过模板包展开。

`make_integer_sequence<T, N>` 只接受合适的整数类型 T 和可表示的非负 N，结果为 `integer_sequence<T, 0, 1, ..., N-1>`。`make_index_sequence<N>` 是 size_t 版本，`index_sequence_for<Ts...>` 等于按 `sizeof...(Ts)` 生成。

序列对象作为函数参数是一种标签分派：类型携带全部信息，对象通常空。也可直接在类模板偏特化中匹配 integer_sequence，不必创建对象。

## 展开过程

示例中二元素元组让 `Indexes...` 成为 `0, 1`。初始化列表里的模式会生成两条输出表达式。C++11/14 初始化列表保证元素从左到右求值，因此常被用来实现带副作用的有序包展开；前置的 `0` 让空包时数组仍合法。

这种技巧可读性有限，C++17 折叠表达式能直接表达逗号折叠。但索引序列本身仍广泛用于元组转换、结构化序列化和调用适配。

包展开模式中每次出现 Indexes 都被替换成相应值。若模式同时引用另一个参数包，参与同一次展开的包长度必须兼容。索引序列常用来把“类型包长度”转换为“可放进表达式的非类型包”。

初始化列表技巧利用元素求值顺序，并把每个有副作用表达式转换为 int 元素。`(expr, 0)` 确保无论 expr 返回什么，数组元素类型一致。前置 0 处理空包，避免零长度原生数组。

C++17 用逗号折叠可简化有序副作用，但 get<I> 仍需要 I 包；integer_sequence 并没有被折叠表达式取代。C++20 模板 Lambda进一步能在局部命名索引包，底层模式依旧相同。

### 自定义顺序和选取

integer_sequence 不要求值连续或排序，可以直接写 index_sequence<2,0> 选择第三、第一元素。make 系列只是常用连续生成器。

<!-- example id="cpp14-index-sequence-select" std="c++14" file="main.cpp" kind="single" compilers="all" output="third first" -->
```cpp
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

调用者显式给出 2、0，因此输出重新排列且省略中间元素。公共 API 通常不让业务调用者手写序列，而由字段映射、编译期表或包装函数生成这种选择。

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

概念上的线性递归生成器从 N 递减到 0，每层继承/别名追加一个值，模板深度与 N 成正比。分治实现把序列对半合并，可把递归深度降到对数级；编译器内建还能直接生成包。

标准只要求最终类型，不规定生成器的实例化策略。不同标准库/编译器对巨大 N 的编译时间差异明显，库代码不应把百万规模运行期循环展开成模板索引。

每个展开元素可能实例化函数、表达式和诊断路径。即使生成序列很快，后续 N 次 get/调用也是真实前端工作，并可能生成大段直线机器码。

### 错误边界

`tuple_size<decay_t<Tuple>>` 不存在、索引越界或函数不可调用时，错误常出现在 impl 的 decltype 展开。入口可先断言 tuple-like、长度和映射范围；但 C++14 没有 Concepts，检测代码本身也要谨慎 SFINAE。

自定义序列含重复索引是合法的，可能对同一元素操作多次；含降序也合法。算法若要求排列或唯一性，integer_sequence 类型不会自动证明，需额外 constexpr 检查。

对右值 tuple 重复选同一只移动元素会尝试移动多次。转发适配器应把“是否允许重复索引”写入契约，而不是只看类型可编译。

## 工程实践

只在确需把类型包映射到位置时使用索引序列；能直接按类型展开就不要引入索引。对外接口隐藏辅助序列参数，并测试空元组、单元素和多元素边界。

典型用途包括 tuple apply、成员逐字段访问、构造固定数组、生成查表项、按索引 zip 多个 tuple，以及从参数包建立 base class 集合。若数据同质且长度运行期变化，普通循环/容器更合适。

实现函数命名 `_impl`/放 detail 命名空间，外层只接收自然参数并自动生成序列。这既防止调用者传错长度，也让未来替换为 std::apply 等新设施时保持 API。

测试不仅看结果，还要覆盖值类别：左值 tuple 不应意外移动，const tuple 不应获得可写引用，右值 tuple 应能把只移动元素转发给消费函数。

## 生成接口的精确契约

### 标准别名速查

| 名称 | 结果与用途 |
| --- | --- |
| `integer_sequence<T, Vs...>` | 保存类型 T 和编译期值包 Vs |
| `value_type` | 精确等于序列参数 T |
| `size()` | 返回值包元素数量，不检查连续性 |
| `index_sequence<Is...>` | `integer_sequence<size_t, Is...>` 的别名 |
| `make_integer_sequence<T,N>` | 生成 T 类型的 `[0,N)` 值包 |
| `make_index_sequence<N>` | 生成 size_t 类型的 `[0,N)` 索引 |
| `index_sequence_for<Ts...>` | 按类型包长度生成索引，不读取类型内容 |
| 空输入 | 形成 `index_sequence<>`，展开表达式必须能处理零项 |
| 手写重复值 | 合法，但会重复实例化/访问对应位置 |
| 手写越界值 | sequence 自身可形成，使用 `get<I>` 时才失败 |

`make_integer_sequence<T, N>` 生成从 0 到 N-1 的序列；N 为零得到空包，N 必须是合适的非负常量。`make_index_sequence<N>` 固定使用 `size_t`，`index_sequence_for<Ts...>` 只取类型包长度而不检查各类型内容。

`integer_sequence::size()` 返回包中值的数量，不保证等于最后一个值加一。用户可直接构造重复、逆序或稀疏序列，只有 make_* 工厂承诺标准递增形状。

线性递归实现会为每个索引产生中间特化并可能触及模板深度；分治实现把递归深度降为对数级，编译器还可能为标准别名提供内建。运行时代码同为零不代表编译成本相同。

重复索引会重复访问同一元素，若第一次访问移动了对象，后续看到的是已移动状态。把 `get<I>(tuple)...` 展开成函数实参时，C++14 也不能依赖各实参按索引从左到右求值；有顺序副作用应使用保证顺序的初始化列表技巧或显式递归。

## Integer sequence 专项审查

- N 是否是合法非负编译期值？
- 空序列是否能自然展开而不访问首项？
- 手写索引是否可能超出目标 tuple 长度？
- 重复索引是否会二次移动同一元素？
- 展开副作用是否错误依赖函数实参顺序？
- 自定义序列的 value_type 是否适合目标索引 API？
- 多个同步展开参数包长度是否一致？
- 线性递归实现是否触发模板深度限制？
- 大型同质数据是否本应使用运行期循环？
- 错误是否可通过更近的 static_assert 提前诊断？

## 权威资料

- [N3658：整数序列](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3658.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
