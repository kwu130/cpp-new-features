# 容器增强

阅读前建议先了解：[迭代器与算法](../prerequisites.md#迭代器与算法)；emplace 部分结合[移动与转发](move-semantics.md)。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 学习目标与旧容器的空缺

C++03 已有 `vector`、`list`、`map` 等容器，但固定长度数组仍常用原生数组，哈希容器没有标准接口，单向链表依赖第三方实现，把对象放入容器还经常先构造临时对象再复制。

C++11 增加 `array`、`forward_list`、无序关联容器和 `emplace` 系列接口。读完后，你应该能够根据连续性、查找方式、引用稳定性和构造成本选择它们，而不是只比较渐进复杂度。

## 新设施速览

| 设施 | 解决的问题 |
| --- | --- |
| `array<T, N>` | 为固定长度连续数组提供标准容器接口 |
| `forward_list<T>` | 提供低额外开销的单向链表 |
| `unordered_map/set` | 提供基于哈希的平均常数时间查找 |
| `emplace` | 从构造参数直接建立容器元素 |

## 先根据存储需求选择容器

以下片段只对比写法；完整、可运行的程序见后文。

```text
// 固定长度：原生数组 vs 有标准容器接口的数组
int old_values[3] = {1, 2, 3};
std::array<int, 3> values{{1, 2, 3}};
// 从构造参数建立元素，而不是先建立一个临时 pair
records.emplace("Ada", 37);
```

array 不自动变长，元素仍在对象内部；它可查询 size 并传给标准算法。unordered_map 按哈希查找，平均查找成本与有序 map 不同，也不保持键的排序。emplace 有时减少临时对象，但不保证总比 insert 快；根据是否需要排序、引用稳定性和实际负载选择。

## 第一个完整示例

下面使用 `array` 保存固定数据，用 `unordered_map` 建立姓名到年龄的映射，并通过 `emplace` 构造键值元素。

```cpp example id="cpp11-containers" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada=37, sum=6"
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

程序输出 `Ada=37, sum=6`。`array` 大小属于类型的一部分且存储连续；无序容器只保证平均常数复杂度，不保证遍历顺序；`emplace` 可以避免某些临时对象，但并不天然比移动插入更快。

## `array` 的对象模型

`std::array<T, N>` 是包裹内建数组的聚合式容器，没有独立堆分配。它提供迭代器、`size()`、比较和赋值等标准容器接口，同时大小 `N` 参与类型系统。不同长度的 `array` 不是同一类型，适合固定协议字段和栈上小型集合。

元素连续并不等于对象一定在栈上：作为类成员或动态对象成员时，它跟随宿主对象存储。`at()` 检查边界并抛异常，`operator[]` 越界是未定义行为。

array 是聚合，C++11 常见初始化写双层花括号以兼容聚合内含原生数组的实现。未显式给出的尾部元素执行值初始化；标量通常为零。默认初始化 `std::array<int,3> a;` 则与原生数组类似，元素可能未初始化。

`data()` 返回连续首地址，`begin/end` 支持算法，`front/back` 提供端点。对 `array<T,0>`，`begin()==end()` 且 `data()` 值由实现契约处理，调用 front/back 是未定义行为。

`fill(value)` 给所有元素赋值，`swap` 逐元素交换，复杂度与 N 线性而非交换两个指针。固定数组作为大对象成员时，swap 成本不能按 vector 的常数时间直觉估算。

### 类型与 tuple 协议

`N` 参与类型，因此函数接收 `array<T, N>` 可在模板中取得编译期长度。标准还提供 `std::tuple_size`、`std::tuple_element` 和 `std::get<I>`，让固定数组参与元组式泛型访问；`I` 越界会在编译期失败。

数组赋值会复制/移动所有元素，内建数组则不能整体赋值。这使 array 更适合作为值类型返回和类成员，但大 N 按值传参仍可能有真实复制成本。

## `forward_list`：只保留向前链接

`std::forward_list<T>` 是单向链表。节点只需要保存“下一个节点”链接，不提供反向迭代、`back()` 或常数时间 `size()`。它适合需要频繁在已知位置之后插入/删除、且希望降低双向链表节点开销的场景。

单向结构使操作围绕“前一个位置”设计，因此提供 `before_begin()`、`insert_after()`、`erase_after()` 和 `splice_after()`。删除当前节点时必须持有它的前驱迭代器；这与 `list::erase(current)` 的接口不同。

节点式存储通常保持未删除元素的引用和迭代器稳定，但遍历缓存局部性弱、每节点分配成本高。若主要操作是顺序遍历，小型数据即使在中间插入，`vector` 仍可能更快，应以访问模式和基准决定。

## 无序容器的典型实现

`unordered_map` 通常由桶数组和节点组成。哈希值决定桶，再通过相等比较解决碰撞。平均查找复杂度 O(1)，最坏可退化为 O(n)。负载因子超过阈值时会 rehash，重新组织桶并使迭代器失效。

键类型必须满足：相等的键产生相同哈希值。修改已存储键会破坏桶不变量，因此键以 `const` 暴露。哈希随机化、桶数量和遍历顺序都不是可移植接口，不能用无序容器输出稳定序列。

C++11 提供 `unordered_set`、`unordered_multiset`、`unordered_map`、`unordered_multimap`。唯一键版本插入返回 `iterator` 与 `bool` 组成的二元组，多重版本允许等价键并返回相应迭代器。`operator[]` 只属于 map 类唯一键容器，会在缺失时默认构造 mapped value。

哈希函数与 `key_equal` 必须一致：若 `key_equal(a, b)` 为 `true`，两者的哈希值必须相等；反向不要求，碰撞由桶内相等比较消解。自定义大小写不敏感相等时，哈希也必须使用同样规范化。

攻击者可控键若造成大量碰撞，平均 O(1) 会退化并形成拒绝服务。实现是否随机化不由标准保证，安全边界可使用更强哈希、限制输入或选择有序容器。

### 桶接口

`bucket(key)` 查询某键所属桶，`bucket_size(i)` 与局部迭代器可观察桶内容，主要用于诊断哈希质量。业务逻辑不应依赖桶编号，因为 rehash、实现和运行配置都会改变它。

`load_factor()` 等于 `size() / bucket_count()` 的浮点比值，`max_load_factor()` 控制触发重哈希的目标阈值。降低阈值通常增加内存换更短碰撞链，不是越低越好。

## `emplace` 的构造路径

`emplace(args...)` 把参数转发给元素构造函数，允许直接在节点或目标存储位置构造。对于 `vector`，扩容仍可能移动已有元素；对于关联容器，键已存在时是否已经构造临时节点取决于具体接口和实现。C++17 的 `try_emplace` 更明确地避免已存在键时构造映射值。

直接 `push_back(value)` 对已有对象通常更清晰，移动优化后成本也可能相同。不要为了“看起来更快”而把所有插入改成 `emplace`，尤其要警惕它允许显式构造函数参与，从而接受原本会被接口阻止的隐式输入。

顺序容器的 `emplace_back(args...)` 在尾部构造，`emplace(pos,args...)` 在指定位置构造并可能移动后续元素。C++11 的 `emplace_back` 返回 `void`（后续标准才返回引用），不能写依赖返回新元素的可移植 C++11 代码。

关联容器的 `value_type` 往往是 `pair<const Key, Mapped>`。复杂时可用 `piecewise_construct` 加两个 tuple 分别构造 key 和 mapped，避免先形成完整 pair。语法冗长，C++17 的 `try_emplace` 对 map 场景更直接。

完美转发允许 `explicit` 构造函数参与直接初始化，这既是能力也是接口宽化。`vector<Widget>.emplace_back(42)` 可能合法，而 `push_back(42)` 因 `explicit Widget(int)` 不合法；代码审查要确认调用意图。

构造新元素抛异常时，容器按各操作提供相应保证；若 vector 扩容且元素移动可能抛、又不可复制，强保证可能受限。元素的 noexcept 移动性质影响容器策略。

## 失效、异常与容量

容器选择必须同时考虑引用稳定性、连续性、查找模式和分配次数。`vector` 扩容会使全部指针、引用、迭代器失效；节点式关联容器通常只使被删除节点失效；无序容器 rehash 会使迭代器失效，但元素引用通常仍有效。

工程中应提前 `reserve` 降低可预测扩容，在暴露容器元素引用前记录失效条件，并用需求选择容器，而不是只按渐进复杂度表格选择。

`reserve` 改变 capacity 不改变 size，不构造元素；`resize` 改变 size，会构造或析构元素。混淆两者会导致性能浪费或逻辑元素意外出现。`shrink_to_fit` 在 C++11 是非绑定请求，不能依赖它必然释放内存。

vector 扩容通常按几何增长但因子未标准化。实时/低延迟代码应预留上限或使用固定存储，不能从某个实现的 1.5/2 倍策略推断可移植延迟。

deque 分段存储，随机访问常数但不保证全体元素连续；`list`/`forward_list` 节点稳定但每节点分配与缓存局部性较差。array、vector、deque 都是不同失效/布局契约，不只是复杂度差异。

容器线程安全保证允许多个线程只读不同/同一容器，某些不同元素修改有受限规则，但结构修改通常需要外部同步。`vector<bool>` 位代理使“不同元素”也可能共享机器字，尤其不能套用普通元素直觉。

## 哈希策略接口

无序容器公开 `bucket_count`、`load_factor`、`max_load_factor`、`reserve` 和 `rehash`，让调用方观察或影响桶策略。`reserve(n)` 面向期望元素数量，容器据最大负载因子选择足够桶；`rehash(n)` 直接要求桶数量至少满足约束。

调用 `reserve` 不是正确性的要求，而是性能规划。它可能立即分配并使迭代器失效。元素引用和指针在 rehash 后仍保持有效，但依赖遍历顺序的代码本来就不具备可移植性。

```cpp example id="cpp11-unordered-emplace" std="c++11" file="main.cpp" kind="single" compilers="all" output="inserted=true, existing=false, size=2"
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

还应评估元素大小、数量分布、遍历频率、分配器、序列化顺序和异常保证。小数据线性扫描 vector 往往比哈希节点更快，渐进复杂度不是唯一成本模型。

API 若只需要遍历，不应暴露具体容器类型；C++11 可用迭代器对或模板 Range 约定。若需要所有权转移，按值/move 容器；若需要固定连续只读视图，C++20 span 才提供标准统一类型。

测试要主动触发 vector 扩容、unordered rehash、重复键、哈希碰撞和零长度 array，验证保存的迭代器/引用没有越界使用。

## 容器增强速查

| 设施 | 关键契约 |
| --- | --- |
| `array<T,N>` | 固定长度聚合式容器，大小进入类型 |
| `array::at` | 越界抛异常，`operator[]` 不检查 |
| `array::data` | 连续存储指针，空数组不可据此解引用 |
| `unordered_map` | 平均常数查找，最坏情况仍可能线性 |
| `bucket_count` | 当前桶数快照，不等于元素数 |
| `load_factor` | 元素数/桶数，rehash 策略由最大负载控制 |
| `reserve(n)` | 为至少 n 元素调整桶规划，可能使迭代器失效 |
| `rehash(n)` | 请求至少相应桶结构，不改变键值对象语义 |
| `emplace` | 原位构造候选，冲突时成本依具体容器/版本规则 |
| `emplace_back` | 在序列尾部构造，扩容仍使引用/迭代器失效 |
| 哈希一致性 | 相等键必须产生相同哈希 |
| 自定义键 | hash 与 equality 必须表达同一等价关系 |

## 容器增强专项审查

- array 的 N 是否属于接口契约而非运行期数据？
- 空 array 是否仍调用 front/back？
- unordered 自定义 hash 与 equality 是否完全一致？
- 对抗性输入是否可能退化哈希复杂度？
- reserve/rehash 后是否仍保存旧迭代器？
- emplace 参数是否真避免临时而非先在调用点构造？
- 插入冲突时构造成本和实参移动状态是否明确？
- vector 扩容后旧元素引用是否失效？
- `max_load_factor` 调整是否导致后续 rehash 峰值？
- 是否错误依赖 unordered 遍历顺序稳定？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/containers.md
```

## 权威资料

- [容器库要求](https://eel.is/c++draft/containers)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
