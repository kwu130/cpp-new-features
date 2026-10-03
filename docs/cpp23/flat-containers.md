# flat_map 与 flat_set：用顺序存储维护有序查找

阅读前建议先了解：[关联容器](../cpp11/containers.md)、[迭代器失效](../prerequisites.md#迭代器与算法)、[结构化绑定](../cpp17/control-flow.md)。本篇介绍的新增能力属于 C++23。

## 为什么需要另一种有序容器

std::map 适合频繁增删且需要稳定元素引用的场景；vector 的紧凑存储适合遍历，但自己维护排序与查找需要额外代码。C++23 的 flat_map、flat_set 及对应 multi 版本提供顺序存储上的有序关联接口。

它们不是无序哈希容器，也不是承诺所有操作比 map 快。先建立“查找靠有序，插入可能搬移”的成本模型，再决定用途。

## flat_map：查找接口仍像 map

传统 `std::map<std::string, int>` 可以处理本例相同查询；替换成 flat_map 时，接口相近但存储和失效规则发生变化。

```cpp example id="cpp23-flat-map" std="c++23" file="main.cpp" kind="single" compilers="all" output="alice=2" requires="__cpp_lib_flat_map>=202207"
#include <cassert>
#include <flat_map>
#include <iostream>
#include <string>
int main() {
    std::flat_map<std::string, int> counts{{"bob", 1}, {"alice", 2}};
    const auto found = counts.find("alice");
    assert(found != counts.end());
    std::cout << "alice=" << found->second << '\n';
}
```

默认 flat_map 分别用 vector 存键与值，并维持两份序列对应；迭代器访问得到键/值引用组成的代理，而不是节点中一个永久存在的 pair。不要假定能取出与 std::map 完全相同的 value_type& 或 pair 地址。

find 对默认随机访问存储执行对数级比较查找；插入为了保持顺序通常需线性搬移元素。比较器仍需满足严格弱序：互相都不小于的键视为等价，不必逐字节相等。

## flat_set：有序且唯一

```cpp example id="cpp23-flat-set" std="c++23" file="main.cpp" kind="single" compilers="all" output="keys=1 2 3" requires="__cpp_lib_flat_set>=202207"
#include <flat_set>
#include <iostream>
int main() {
    std::flat_set<int> keys{3, 1, 2, 2};
    bool first = true;
    std::cout << "keys=";
    for (int key : keys) {
        std::cout << (first ? "" : " ") << key;
        first = false;
    }
    std::cout << '\n';
}
```

输出按序且去掉重复的 2。flat_multiset 允许等价键重复，flat_multimap 允许同键多个值，选择它们依据业务语义，不只是性能。

## 批量建立与所有权

适合读多写少、小中型查找表或一次装载后大量遍历。可以利用已有排序数据降低建立成本，但 sorted_unique/sorted_equivalent 标签是调用方的前置承诺，不会替你验证任意输入是否符合排序和唯一性。

flat_map 的 extract/replace 接口涉及键值两份容器，必须共同维持长度对应、排序及唯一性等不变量。不要只修改一边，或为了快而跳过输入验证。本篇最小示例使用普通初始化，让容器建立排序。

## 失效与异常边界

插入、删除、扩容会按底层顺序容器规则让迭代器/引用失效；不能套用节点式 map 插入后引用通常稳定的习惯。修改键会破坏查找顺序，接口限制键修改；按引用保存值也需要考虑后续搬移。

元素移动、比较器或 allocator 可以抛异常，不能笼统保证每个操作都有同一强异常保证。默认连续存储可能改善遍历局部性，但 key/value 两份存储、元素尺寸和修改频率决定实际成本。修改密集或要求地址稳定时应继续评估 map。

这些标准容器是 C++23；第三方同名设施可能更早存在，但接口、代理类型及失效保证未必相同。

## 权威资料

- [flat_map](https://eel.is/c++draft/flat.map)、[flat_set](https://eel.is/c++draft/flat.set)
- [P0429R9：flat_map](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p0429r9.pdf)
- [P1222R4：flat_set](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p1222r4.pdf)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/flat-containers.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
