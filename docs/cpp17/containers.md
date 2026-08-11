# 容器接口增强

关联容器加入节点句柄，可在不复制元素的情况下转移节点；`try_emplace` 和 `insert_or_assign` 更明确地区分“缺失时构造”与“存在时覆盖”。

<!-- example id="cpp17-containers" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=43" -->
```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> source;
    source.try_emplace("answer", 42);

    auto node = source.extract("answer");
    node.mapped() += 1;
    std::map<std::string, int> destination;
    destination.insert(std::move(node));
    destination.insert_or_assign("answer", 43);

    std::cout << "answer=" << destination.at("answer") << '\n';
}
```

节点只能在兼容的容器和分配器条件下转移。`try_emplace` 在键已存在时不会构造映射值，适合构造成本高或不可移动的值。

## 节点句柄的所有权

`extract` 把节点从容器中解除链接并返回拥有该节点的移动专用句柄。元素对象通常保持原地址且不进行复制/移动，句柄析构时若未重新插入，会负责销毁节点。

关联容器中键在容器内是 `const`，但提取后可通过节点句柄修改键，再插回容器，容器会按新键重新定位。插入可能因键重复失败，返回结果中仍保留节点所有权，调用方必须处理。

节点跨容器转移要求节点类型和分配器兼容。不要假设任意比较器、哈希器或内存资源组合都能零成本合并。

## `try_emplace` 与 `insert_or_assign`

`try_emplace(key, args...)` 只在键不存在时用参数构造映射值，尤其适合不可复制对象或昂贵构造。与 `emplace(key, expensive())` 不同，调用表达式里的 `expensive()` 仍可能在进入函数前求值；要真正延迟，应传构造参数而非已构造结果。

`insert_or_assign` 在缺失时插入，在存在时对映射值赋值，返回迭代器和是否插入。它比 `operator[] = value` 更适合映射值不可默认构造或需要区分插入/覆盖的场景。

## 迭代器与异常保证

提取只使被提取元素的迭代器失效，其他元素通常保持有效。节点处于句柄中时，原指向元素的指针/引用虽然可能仍指向对象，但在重新插入前使用条件受标准约束，应避免跨所有权状态长期保存。

## 示例解析与实践

示例提取节点、修改映射值、转移到另一个 map，再明确覆盖。工程中节点句柄适合改键、容器合并和避免昂贵对象搬迁；普通插入仍优先使用更简单接口。每次都检查重复键和分配器契约。

## 权威资料

- [P0083R3：节点句柄](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0083r3.pdf)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
