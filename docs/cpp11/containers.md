# 容器增强

C++11 增加了固定长度 `array`、哈希容器，以及直接在容器存储区构造元素的 `emplace` 系列接口。

<!-- example id="cpp11-containers" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada=37, sum=6" -->
```cpp
#include <array>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>

int main() {
    std::array<int, 3> values{{1, 2, 3}};
    std::unordered_map<std::string, int> ages;
    ages.emplace("Ada", 37);

    int sum = 0;
    for (const auto& value : values) {
        sum += value;
    }
    std::cout << "Ada=" << ages.at("Ada") << ", sum=" << sum << '\n';
}
```

`array` 大小属于类型的一部分且存储连续。无序容器只保证平均常数复杂度，不保证遍历顺序。`emplace` 可以避免临时对象，但并不天然比移动插入更快，应优先考虑可读性。

## `array` 的对象模型

`std::array<T, N>` 是包裹内建数组的聚合式容器，没有独立堆分配。它提供迭代器、`size()`、比较和赋值等标准容器接口，同时大小 `N` 参与类型系统。不同长度的 `array` 不是同一类型，适合固定协议字段和栈上小型集合。

元素连续并不等于对象一定在栈上：作为类成员或动态对象成员时，它跟随宿主对象存储。`at()` 检查边界并抛异常，`operator[]` 越界是未定义行为。

## 无序容器的典型实现

`unordered_map` 通常由桶数组和节点组成。哈希值决定桶，再通过相等比较解决碰撞。平均查找复杂度 O(1)，最坏可退化为 O(n)。负载因子超过阈值时会 rehash，重新组织桶并使迭代器失效。

键类型必须满足：相等的键产生相同哈希值。修改已存储键会破坏桶不变量，因此键以 `const` 暴露。哈希随机化、桶数量和遍历顺序都不是可移植接口，不能用无序容器输出稳定序列。

## `emplace` 的构造路径

`emplace(args...)` 把参数转发给元素构造函数，允许直接在节点或目标存储位置构造。对于 `vector`，扩容仍可能移动已有元素；对于关联容器，键已存在时是否已经构造临时节点取决于具体接口和实现。C++17 的 `try_emplace` 更明确地避免已存在键时构造映射值。

直接 `push_back(value)` 对已有对象通常更清晰，移动优化后成本也可能相同。不要为了“看起来更快”而把所有插入改成 `emplace`，尤其要警惕它允许显式构造函数参与，从而接受原本会被接口阻止的隐式输入。

## 失效、异常与容量

容器选择必须同时考虑引用稳定性、连续性、查找模式和分配次数。`vector` 扩容会使全部指针、引用、迭代器失效；节点式关联容器通常只使被删除节点失效；无序容器 rehash 会使迭代器失效，但元素引用通常仍有效。

工程中应提前 `reserve` 降低可预测扩容，在暴露容器元素引用前记录失效条件，并用需求选择容器，而不是只按渐进复杂度表格选择。

## 哈希策略接口

无序容器公开 `bucket_count`、`load_factor`、`max_load_factor`、`reserve` 和 `rehash`，让调用方观察或影响桶策略。`reserve(n)` 面向期望元素数量，容器据最大负载因子选择足够桶；`rehash(n)` 直接要求桶数量至少满足约束。

调用 `reserve` 不是正确性的要求，而是性能规划。它可能立即分配并使迭代器失效。元素引用和指针在 rehash 后仍保持有效，但依赖遍历顺序的代码本来就不具备可移植性。

<!-- example id="cpp11-unordered-emplace" std="c++11" file="main.cpp" kind="single" compilers="all" output="inserted=true, existing=false, size=2" -->
```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>

int main() {
    std::unordered_map<std::string, int> values;
    values.reserve(8);
    const std::pair<std::unordered_map<std::string, int>::iterator, bool> first =
        values.emplace("answer", 42);
    const std::pair<std::unordered_map<std::string, int>::iterator, bool> duplicate =
        values.emplace("answer", 100);
    values.emplace("year", 2011);

    std::cout << std::boolalpha
              << "inserted=" << first.second
              << ", existing=" << duplicate.second
              << ", size=" << values.size() << '\n';
}
```

`emplace` 返回的布尔值说明是否真正插入。C++11 中即使键重复，实参表达式也已经在调用前求值，且实现可能构造候选元素；不能把它当作延迟计算接口。C++17 的 `try_emplace` 更明确地避免在键已存在时构造映射值。

## 选择容器的接口问题

如果调用方需要连续字节、稳定索引或与 C API 互操作，应优先连续容器；需要稳定节点地址和频繁中间插入时再考虑节点容器；只为“查找快”选择无序容器前，还要确认键哈希质量、最坏情况、安全输入和输出稳定性。

## 权威资料

- [容器库要求](https://eel.is/c++draft/containers)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
