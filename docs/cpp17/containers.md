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

<!-- example id="cpp17-node-insert-conflict" std="c++17" file="main.cpp" kind="single" compilers="all" output="inserted=false, existing=2, recovered=1" -->
```cpp
#include <iostream>
#include <map>
#include <string>
#include <utility>

int main() {
    std::map<std::string, int> source{{"key", 1}};
    std::map<std::string, int> destination{{"key", 2}};

    auto node = source.extract("key");
    auto result = destination.insert(std::move(node));

    if (result.inserted || result.node.empty()) {
        return 1;
    }
    const int recovered = result.node.mapped();
    std::cout << std::boolalpha
              << "inserted=" << result.inserted
              << ", existing=" << result.position->second
              << ", recovered=" << recovered << '\n';
}
```

唯一键冲突时，插入返回对象的 `inserted` 为假，`position` 指向目标容器中已有元素，失败节点则回到 `result.node`。所有权没有丢失，调用方可以改键后重试、放回源容器或让句柄析构。忽略返回对象会直接销毁未插入节点，这可能不是业务期望。

### 节点句柄接口

节点句柄可移动但不可复制，默认构造或成功插入后的句柄为空，可用 `empty()` 或显式布尔转换查询。映射容器节点提供 `key()` 与 `mapped()`，集合节点提供 `value()`；`get_allocator()` 暴露相关分配器信息。

`extract(iterator)` 按位置解除节点，关联容器版本通常是摊销常数复杂度；`extract(key)` 还要执行查找。无序容器提取不会触发元素复制，但后续插入仍可能触发 rehash。

指向被提取元素的指针和引用保持其对象身份，但节点被句柄拥有期间不能按普通容器元素方式使用；成功插入兼容容器后它们重新指向插入元素。原迭代器在提取时失效，不能因地址没变就继续使用。

### `merge`

`merge` 批量尝试从兼容源容器转移节点。唯一键容器中与目标冲突的节点留在源容器，多重键容器可接收更多等价键。操作结束后两个容器都仍有效，但元素分布取决于冲突结果。

源和目标可以使用不同比较器或哈希策略的某些兼容类型组合，但节点/分配器前置条件仍需满足。不要在遍历源容器的同时假定每个节点必然移动；合并后重新检查两边内容。

## `try_emplace` 与 `insert_or_assign`

`try_emplace(key, args...)` 只在键不存在时用参数构造映射值，尤其适合不可复制对象或昂贵构造。与 `emplace(key, expensive())` 不同，调用表达式里的 `expensive()` 仍可能在进入函数前求值；要真正延迟，应传构造参数而非已构造结果。

`insert_or_assign` 在缺失时插入，在存在时对映射值赋值，返回迭代器和是否插入。它比 `operator[] = value` 更适合映射值不可默认构造或需要区分插入/覆盖的场景。

两者都有接收左值键、右值键和带 hint 的重载。`try_emplace` 在键冲突时不会移动右值键，也不会用映射值构造参数创建对象；这让调用方可以在失败后继续使用传入对象。不过，传给函数的普通表达式仍在调用前求值，只有映射值的构造由容器延迟。

`insert_or_assign` 的布尔结果表示是否新插入，而不是赋值是否改变了值。存在分支要求映射值可由给定对象赋值；缺失分支要求能构造新元素。它不会默认构造 mapped_type，因此比 `operator[]` 支持更多类型。

hint 重载的提示错误不会破坏正确性，只可能失去性能收益。对有序容器，正确相邻位置可减少查找工作；无序容器没有同样的顺序 hint 语义。

## 迭代器与异常保证

提取只使被提取元素的迭代器失效，其他元素通常保持有效。节点处于句柄中时，原指向元素的指针/引用虽然可能仍指向对象，但在重新插入前使用条件受标准约束，应避免跨所有权状态长期保存。

插入节点如果比较器、哈希、分配或其他规定操作抛出，句柄所有权和容器状态应按具体重载的异常保证处理。业务代码必须保留可恢复节点对象，不能在同一复杂表达式里把它移动后丢弃所有句柄路径。

对无序容器，成功插入可能 rehash，使所有迭代器失效，但元素引用/指针的稳定性按容器规则另行判断。有序节点式容器通常保持其他元素迭代器有效。写通用容器适配器时，应读取目标容器的精确失效表，而不是把“节点容器”当统一保证。

## 选择接口的决策顺序

只读查找使用 `find`；需要缺失时默认构造并返回引用才使用 `operator[]`；仅缺失时按参数构造选择 `try_emplace`；无论是否存在都要写入选择 `insert_or_assign`；已有完整 `value_type` 时可用 `insert`/`emplace`；需要改键或跨容器保留对象身份才引入节点句柄。

接口选择会直接表达碰撞策略。把所有写入都写成 `operator[]` 会隐藏默认构造与覆盖；把所有写入写成 `emplace` 又可能让读者误判冲突时构造成本。根据业务语义选择，而不是根据名字新旧选择。

## 示例解析与实践

示例提取节点、修改映射值、转移到另一个 map，再明确覆盖。工程中节点句柄适合改键、容器合并和避免昂贵对象搬迁；普通插入仍优先使用更简单接口。每次都检查重复键和分配器契约。

## 权威资料

- [P0083R3：节点句柄](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0083r3.pdf)
- [工作草案：Associative containers](https://eel.is/c++draft/associative.reqmts)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
