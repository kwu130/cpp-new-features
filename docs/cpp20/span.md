# `span`

`span` 是连续内存的非拥有视图，可以统一接收数组、`array`、`vector` 或指针加长度，同时保留元素类型和边界信息。

```cpp example id="cpp20-span" std="c++20" file="main.cpp" kind="single" compilers="all" output="10"
#include <array>
#include <iostream>
#include <span>

int sum(std::span<const int> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

int main() {
    const std::array<int, 4> values{1, 2, 3, 4};
    std::cout << sum(values) << '\n';
}
```

`span` 不拥有内存，底层数据销毁或容器重新分配后视图会失效。只读参数使用 `span<const T>`；固定长度接口可以使用 `span<T, N>` 在类型中表达大小。

## 表示与静态长度

动态长度 `span<T>` 典型保存指针和元素数量；静态长度 `span<T, N>` 可只保存指针，因为 N 已在类型中。两者都不分配、不复制元素，按值传递通常廉价。

`span` 要求元素连续，能从内建数组、`array`、连续容器或指针加长度构造。它不会接受 `list` 等节点容器。长度以元素为单位，`size_bytes()` 才返回字节数。

extent 是 `span` 类型的第二模板参数。缺省值 `dynamic_extent` 表示长度存储在运行期对象中；固定 extent 必须与构造来源长度兼容，允许编译器在类型检查和优化时利用常量。`span<T, 0>` 合法，表示始终为空的固定视图。

固定 span 并不是内建数组所有者。复制 `span<int, 4>` 仍只复制视图，底层四个整数没有复制。静态长度带来的主要变化是类型契约和可能更小的表示，而不是所有权。

`extent` 是元素数量而非字节数量，`size_bytes()` 才返回 `size() * sizeof(element_type)`。固定 extent 为零的 span 是合法类型，它仍不允许解引用；实现可能无需保存有效数据指针。不要用对象尺寸反推 span 内部表示。

`span<T, N>::extent` 是编译期常量，可用于静态断言和选择固定块算法。动态 span 的 `extent` 等于 `dynamic_extent`，运行期 `size()` 才给出实际长度。把动态长度转换为固定长度需要满足构造前置条件，不能因目标类型写了 N 就自动截断。

```cpp example id="cpp20-span-static-subview" std="c++20" file="main.cpp" kind="single" compilers="all" output="middle=2,3 bytes=8"
#include <array>
#include <cstddef>
#include <iostream>
#include <span>

int main() {
    std::array<int, 4> values{1, 2, 3, 4};
    std::span<int, 4> all(values);
    auto middle = all.subspan<1, 2>();
    static_assert(decltype(middle)::extent == 2);

    std::cout << "middle=" << middle[0] << ',' << middle[1]
              << " bytes=" << middle.size_bytes() << '\n';
}
```

编译期 `subspan<1, 2>` 返回 `span<int, 2>`，偏移和计数进入实例化检查。输出中的字节数等于两个 `int` 的对象表示大小；示例验证器运行在标准保证 `sizeof(int)` 为 4 的当前工具链矩阵上，通用代码不应把该数值硬编码为协议常量。

### 构造来源与转换

元素类型转换必须保持数组指针转换兼容性，不能借 span 做逐元素数值转换。`span<int>` 可转换为 `span<const int>`，反向不允许；`span<Derived>` 也不能被当成 `span<Base>`，因为基类子对象并非按 `sizeof(Base)` 连续排列。

从范围构造时要求连续且有大小，并受 borrowed/viewable 等生命周期条件约束。显式的指针加长度构造完全信任调用方：指针必须指向至少给定数量的连续元素，二者不匹配会使后续访问失去保证。

`data()` 对空 span 可返回空或某个不可解引用位置，不能因为 `size()==0` 仍访问 `data()[0]`。`empty()`、`size()` 和 `size_bytes()` 是观察接口，不验证底层所有者仍存在。

从 C 数组和 `std::array<T, N>` 构造时，N 可通过类模板实参推导进入静态 extent；从 `vector` 等运行期容器通常得到动态 extent。局部 `std::span view(array)` 可以保留长度，公共函数形参仍应显式写 `span<const T, N>` 或 `span<const T>` 表达契约。

元素类型转换要求数组元素指针具有相应安全转换，主要用于增加 const。`span<Derived>` 不能转成 `span<Base>`，因为相邻 Derived 对象中的 Base 子对象步长仍是 `sizeof(Derived)`；若允许转换，按 Base 步长迭代会走入错误地址。

来自迭代器与数量/哨兵的构造依赖连续迭代器协议。仅仅一个类型支持 `operator+` 和解引用，不代表底层元素连续；自定义迭代器必须诚实满足 `contiguous_iterator` 及 `to_address` 关系。

## 子视图与边界

`first`、`last`、`subspan` 创建同一存储的窗口，不复制数据。编译期计数版本能把结果长度编码进类型，并在部分情况下提前检查；运行期越界仍违反前置条件，`operator[]` 不负责抛异常。

把对象表示为字节时可用 `as_bytes` 或 `as_writable_bytes`，它们保留合法别名规则接口，但字节序、填充和对象可序列化性仍由调用方处理。不能把任意对象内存直接当成跨平台协议。

`first<Count>()`、`last<Count>()` 与编译期 `subspan<Offset, Count>()` 尽可能返回固定 extent；接收运行期数量的重载返回动态 extent。所有这些操作只产生新窗口，复杂度为常数。

边界不由 `operator[]` 检查，C++20 `span` 也没有标准 `at()`。违反构造或切片的前置条件后，不应期待异常。面向不可信长度的解析器必须先显式验证，再构造/切片 span。

### 字节视图

`as_bytes(span<T>)` 返回只读 `span<const byte>`，长度为原元素数乘 `sizeof(T)`；若原 span 可写且 T 非 const，`as_writable_bytes` 返回可写字节视图。通过 `byte` 观察对象表示是允许的，但写入后对象值是否有效取决于类型表示规则。

对象表示可能含填充字节，填充值可能未指定；整数有字节序，结构体有布局和 ABI 差异，指针/虚表更不能持久化。字节 span 适合哈希已定义字节协议、系统调用缓冲区和显式编码器，不是自动序列化。

## 生命周期与失效

`span` 比裸指针加长度更难把两者传错，却仍不拥有内存。`vector` 扩容、所有者析构、数组离开作用域都会使它失效。返回 span 时必须证明底层存储更长寿；异步保存参数 span 通常危险。

修改 `vector` 大小不一定每次重分配，但只要发生重分配，所有指向旧存储的 span 都悬空。即使容量不变，擦除/插入也会影响相应位置之后元素的对象身份，已有子视图可能不再表示原逻辑数据。

从临时 `array`/容器构造只读视图即便某些语法可形成，完整表达式后所有者销毁也会悬空。类型系统无法追踪这种时间关系。函数若需要把数据放入队列或协程帧，应复制/移动拥有容器，而不是保存 span。

多线程共享 span 等同于共享其指向的元素。span 自身只读不代表元素没有数据竞争；`span<const T>` 禁止经该视图修改，却不能阻止其他别名线程写入。同步责任属于底层对象协议。

## API 设计与性能

只读算法按值接收 `span<const T>`，原地算法接收 `span<T>`。需要接受临时拥有容器并延长寿命时应使用拥有类型，而不是强行转换成 span。静态长度适合矩阵行、加密块等长度属于契约的接口。

示例让同一 `sum` 接受 `array`，生成代码接近指针循环。实践中同时测试空范围、固定长度和切片边界，并在文档中明确调用期间是否保存视图。

固定 extent 是很强的接口信号，例如 `span<const byte, 16>` 表示固定块。调用动态长度 span 转固定长度 span 需要满足长度条件，不能把运行期错误隐藏为模板转换。对外部输入仍应先检查长度并返回领域错误。

`span` 不携带容量，只携带可访问大小，不能作为 `vector` 追加接口。需要输出到调用方缓冲区时，可以接收可写 span 并返回实际写入子 span/长度，让容量检查集中在函数内。

与 `string_view` 相比，span 可表示任意对象元素且可写；与迭代器对相比，它要求连续并提供 O(1) 大小；与 vector 相比，它没有分配器、容量或所有权。根据契约选择最窄抽象。

### 别名与原地算法

两个 span 可以部分或完全重叠。接收输入 span 与输出 span 的算法若不支持重叠，必须把这一点写成前置条件并在可行时检查地址区间；仅类型不同不能证明无别名。复制重叠字节还要选择具有相应语义的算法，不能盲用按不重叠优化的路径。

按值传 span 只复制窗口元数据，适合函数参数。传 `const span<T>&` 只会让窗口对象不能改起点/长度，并不会把元素变 const；元素只读性由 `span<const T>` 表达。这一区别与 `const vector<T>&` 很不一样。

函数若返回输入的子 span，应明确它与哪个参数所有者绑定；多个候选输入时，调用者很难从返回类型判断来源。领域 API 可返回带标签的结果或让调用者提供输出回调，以缩小悬空风险。

## Span 接口速查

| 接口/类型 | 关键语义 |
| --- | --- |
| `span<T>` | 动态 extent，运行期保存长度 |
| `span<T,N>` | 固定 extent，N 进入类型 |
| `dynamic_extent` | 表示运行期长度的特殊常量 |
| `data()` | 返回连续元素首地址，不拥有数据 |
| `size()` | 元素数；`size_bytes` 才是字节数 |
| `first/last` | O(1) 创建首尾子视图 |
| `subspan` | O(1) 创建偏移窗口，编译期版可保留固定 extent |
| `as_bytes` | 只读观察对象表示，不处理字节序/填充 |
| `as_writable_bytes` | 可写对象表示，写后值有效性仍受类型规则限制 |
| `operator[]` | C++20 不检查边界，也没有标准 at() |

## Span 专项审查问题

- 底层数组/容器是否覆盖 span 的完整使用期？
- vector 重分配、插入和擦除后是否仍保存旧 span？
- 固定 extent 是否与真实运行期长度一致并先验证？
- `const span<T>&` 是否被误当作元素只读，而应使用 `span<const T>`？
- 输入输出 span 是否可能重叠，算法是否允许别名？
- 字节视图是否错误忽略端序、填充和对象表示有效性？
- 空 span 是否仍调用 front/back 或解引用 data？
- 切片偏移/数量是否在构造前检查不可信输入？
- 异步保存参数是否应该改为复制拥有容器？
- 返回子 span 的所有者来源是否在 API 契约中明确？

## 权威资料

- [P0122R7：span](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0122r7.pdf)
- [工作草案：span](https://eel.is/c++draft/views.span)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
