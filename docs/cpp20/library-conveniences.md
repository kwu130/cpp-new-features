# 字符串和容器常用增强

字符串加入 `starts_with`、`ends_with`，关联容器加入 `contains`，并提供统一的 `erase`/`erase_if`，让常见意图更直接。

<!-- example id="cpp20-library-conveniences" std="c++20" file="main.cpp" kind="single" compilers="all" output="valid=true, remaining=2" -->
```cpp
#include <iostream>
#include <map>
#include <string>
#include <vector>

int main() {
    const std::string filename = "report.md";
    const std::map<std::string, int> versions{{"cpp20", 20}};
    std::vector<int> values{1, 2, 3, 4};
    std::erase_if(values, [](int value) { return value % 2 == 0; });

    const bool valid = filename.starts_with("report")
        && filename.ends_with(".md")
        && versions.contains("cpp20");
    std::cout << "valid=" << std::boolalpha << valid
              << ", remaining=" << values.size() << '\n';
}
```

`contains` 只回答键是否存在，不返回元素；随后还要访问值时，单次 `find` 更合适。前后缀检查按字符序列比较，不处理路径规范化或大小写规则。

## `starts_with` 与 `ends_with`

字符串和 `string_view` 的前后缀检查接受字符、字符串视图等形式，语义是长度检查后比较对应字符区间。复杂度与被比较前后缀长度线性相关，不进行区域设置、Unicode 规范化或大小写折叠。

解析协议固定 ASCII 标记时它们很合适；处理用户自然语言、文件系统大小写或组合 Unicode 字符时需要更高层文本库。后缀名判断也不等于安全文件类型验证。

`basic_string` 和 `basic_string_view` 都提供这些成员。字符重载只比较一个元素；字符串/视图重载按 char_traits 的序列比较。空前缀和空后缀总能匹配任何字符串，包括空字符串。

实现通常先比较长度，再调用 traits compare 或等价循环，不创建子字符串。相较 `find(prefix)==0`，接口直接表达方向，也避免后缀检查中的无符号减法边界。

它们不消费输入。解析器若匹配后还要前进，可在确认 starts_with 后对 string_view 调用 `remove_prefix`；拥有 string 直接 erase 会移动字符，频繁解析更适合视图游标。

路径后缀应优先使用 filesystem::path 的 extension/stem 语义，并了解多重扩展；字符串 ends_with 只适合协议 token 或已经定义为纯字符规则的场景。

## 关联容器 `contains`

`contains(key)` 等价于 `find(key) != end()` 的意图表达，复杂度沿用容器查找：有序关联容器通常 O(log n)，无序容器平均 O(1)。透明比较器存在时可进行异构查找，避免临时构造完整键类型。

若检查后立即再次 `at` 或 `find`，会做两次查找且并发外部修改时可能有竞态。需要元素时直接保存一次 `find` 结果；只需布尔判断才用 `contains`。

有序 `map/set` 及多重版本、无序关联容器都获得 contains。多重容器只回答至少存在一个等价键，不返回数量；需要数量用 count，需要遍历全部等价元素用 equal_range。

### 异构查找

有序容器比较器提供 `is_transparent`（例如 `std::less<>`），且能比较查询类型与 key_type 时，contains 可接受异构键。这样 `map<string, ...>` 能用 string_view 或 `const char*` 查询而不构造临时 string。

无序容器的异构查找还要求哈希器和相等器透明，并保证不同表示的等价值产生相同哈希。只把 equality 设透明、却让 hash 按不同编码计算，会破坏桶查找。

透明比较不是自动免分配保证；比较器/哈希器实现仍可能构造对象。标准设施配合 string/string_view 通常能直接观察字符，用户类型应为所有组合写一致测试。

contains 是 const 查询，但并发安全规则不变：多个只读操作可并发，任何线程修改容器时仍需外部同步。contains 后再访问也不是原子“检查并使用”。

## `erase` 与 `erase_if`

统一非成员 `erase(container, value)` 和 `erase_if(container, predicate)` 封装不同容器正确的删除惯用法，并返回删除数量。对 `vector` 等顺序容器通常执行移动压缩，复杂度 O(n)，被删位置后的引用和迭代器失效。

谓词可能按实现需要被调用，不能修改容器结构或依赖固定调用次数。删除大型对象会执行析构和移动，批量操作仍应评估延迟峰值。

<!-- example id="cpp20-erase-count" std="c++20" file="main.cpp" kind="single" compilers="all" output="removed=3, left=2" -->
```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 2, 3, 2};
    const auto removed = std::erase(values, 2);
    std::cout << "removed=" << removed
              << ", left=" << values.size() << '\n';
}
```

非成员 `erase` 封装了顺序容器的 erase-remove 惯用法并返回删除数量。它不是只删除第一个匹配项；示例的三个 2 全部移除，剩余元素顺序保持为 1、3。

不同容器的实现策略沿用其结构：vector/string 移动压缩并擦除尾部，list/forward_list 可逐节点删除，关联容器主要提供 erase_if 而不是按 mapped/value 的统一 erase。接口名字统一不代表复杂度或失效规则统一。

对 vector，未删除元素可能被移动赋值到前面，被删点及之后的迭代器/引用通常失效；容量通常不因 erase 自动收缩。对 list，只有被删节点的迭代器/引用失效。必须按具体容器规则审计。

谓词应是对元素的只读分类。修改键会破坏关联容器不变量，修改容器本身会使遍历失效；抛异常时哪些元素已经移动/删除取决于具体容器算法保证，不能假定事务回滚。

## 其他相关便利增强

C++20 还让许多标准库组件 constexpr 化，并为 map/unordered_map 等加入更一致的接口，但每项归属应单独核对。本文只聚焦高频的前后缀、contains 与统一擦除，避免把后续标准设施误列为 C++20。

特别注意 `string::contains` 是 C++23，不属于 C++20；C++20 的 contains 指关联容器。字符串包含子串仍使用 `find(...) != npos`，不能因容器 contains 已存在就假设字符串也有。

`std::ssize` 在 C++20 提供有符号长度，适合与有符号索引/差值比较，避免 `size_t` 与负值警告；`std::to_array` 从内建数组生成 `std::array` 并正确推导长度。这些小工具同样以减少易错样板为目标。

`std::midpoint` 和 `std::lerp` 分别提供降低整数溢出风险的中点、浮点线性插值。它们属于数值便利设施，使用时仍需阅读舍入、单调性和指针重载前置条件。

## 示例解析与工程实践

示例组合字符串检查、映射存在性和向量条件删除。便利接口减少样板代码，但不会改变底层复杂度、编码语义或失效规则。代码审查仍需问：是否重复查找、文本规则是否足够、删除后是否保存了悬空迭代器，以及谓词是否纯净。

## 权威资料

- [P0458R2：关联容器 contains](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0458r2.html)
- [P1209R0：统一容器擦除](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1209r0.html)
- [工作草案：Container requirements](https://eel.is/c++draft/container.requirements)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
