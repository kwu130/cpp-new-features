# 容器接口增强

## 学习目标与关联容器更新问题

C++14 的 `map::emplace` 已能原地构造元素，但当键已存在时，传入的映射值实参仍可能提前构造；更新现有值又常写成一次查找加条件分支。把元素从一个关联容器搬到另一个容器时，通常还要移动或复制值，容器内为排序保持 `const` 的键也无法直接修改。

C++17 用节点句柄暴露已分配节点的临时所有权，并加入 `try_emplace`、`insert_or_assign` 和 `merge`。这些接口分别表达“转移节点”“仅缺失时构造”“无论是否存在都得到指定值”，选择应由业务意图决定。

读完后，你应能追踪提取与插入失败时的节点所有权，区分三种插入/更新接口的构造行为，并检查分配器、键冲突、迭代器与异常保证。

## 最小接口

```text
auto node = source.extract(key);                    // source 不再拥有节点
auto result = destination.insert(std::move(node)); // 失败时节点在 result.node
destination.merge(source);                          // 可转移的节点离开 source

map.try_emplace(key, mapped_constructor_arguments...);
map.insert_or_assign(key, mapped_value);
```

## 第一个完整示例

示例先延迟构造映射值，再提取节点、在容器外修改映射值、插入目标容器，最后用覆盖接口把值设为确定结果。

```cpp example id="cpp17-containers" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=43"
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

程序输出 `answer=43`。提取后 `source` 不再拥有 `answer` 节点；成功插入后传入的句柄为空，所有权归 `destination`。节点只能在兼容的容器和分配器条件下转移；`try_emplace` 在键已存在时不会构造映射值。

## 节点句柄的所有权

`extract` 把节点从容器中解除链接并返回拥有该节点的移动专用句柄。元素对象通常保持原地址且不进行复制/移动，句柄析构时若未重新插入，会负责销毁节点。

关联容器中键在容器内是 `const`，但提取后可通过节点句柄修改键，再插回容器，容器会按新键重新定位。插入可能因键重复失败，返回结果中仍保留节点所有权，调用方必须处理。

节点跨容器转移要求节点类型和分配器兼容。不要假设任意比较器、哈希器或内存资源组合都能零成本合并。

```cpp example id="cpp17-node-insert-conflict" std="c++17" file="main.cpp" kind="single" compilers="all" output="inserted=false, existing=2, recovered=1"
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

节点句柄的具体类型由容器定义，不能假定 `map<K,V>::node_type` 与任意其他容器节点类型相同。标准为若干兼容关联容器组合规定可转移接口，例如唯一键与多重键版本之间的 merge，但这不是任意实现容器之间的通用节点 ABI。

插入节点时，若句柄的分配器与目标容器分配器不满足规定的相等条件，会违反前置条件，而不是自动深拷贝到新分配器。安全封装应在资源边界处阻止这种操作；调试断言可以比较分配器，但不能代替发布版本中的设计保证。

### `merge`

`merge` 批量尝试从兼容源容器转移节点。唯一键容器中与目标冲突的节点留在源容器，多重键容器可接收更多等价键。操作结束后两个容器都仍有效，但元素分布取决于冲突结果。

源和目标可以使用不同比较器或哈希策略的某些兼容类型组合，但节点/分配器前置条件仍需满足。不要在遍历源容器的同时假定每个节点必然移动；合并后重新检查两边内容。

有序容器把每个成功节点按目标比较器重新定位，因此源比较器认定的键顺序不会被保留。无序容器则按目标哈希和相等谓词判断冲突，并可能 rehash。目标的键等价关系若比源更粗，多个源节点可能只移动一部分。

`merge` 不创建目标已有等价键的第二份副本（对唯一键容器），也不销毁冲突节点。它适合“尽可能吸收，剩余继续处理”的工作流；若业务要求冲突时报错并完全回滚，需在操作前检测或构建显式事务层。

## `try_emplace` 与 `insert_or_assign`

`try_emplace(key, args...)` 只在键不存在时用参数构造映射值，尤其适合不可复制对象或昂贵构造。与 `emplace(key, expensive())` 不同，调用表达式里的 `expensive()` 仍可能在进入函数前求值；要真正延迟，应传构造参数而非已构造结果。

`insert_or_assign` 在缺失时插入，在存在时对映射值赋值，返回迭代器和是否插入。它比 `operator[] = value` 更适合映射值不可默认构造或需要区分插入/覆盖的场景。

两者都有接收左值键、右值键和带 hint 的重载。`try_emplace` 在键冲突时不会移动右值键，也不会用映射值构造参数创建对象；这让调用方可以在失败后继续使用传入对象。不过，传给函数的普通表达式仍在调用前求值，只有映射值的构造由容器延迟。

`insert_or_assign` 的布尔结果表示是否新插入，而不是赋值是否改变了值。存在分支要求映射值可由给定对象赋值；缺失分支要求能构造新元素。它不会默认构造 `mapped_type`，因此比 `operator[]` 支持更多类型。

hint 重载的提示错误不会破坏正确性，只可能失去性能收益。对有序容器，正确相邻位置可减少查找工作；无序容器没有同样的顺序 hint 语义。

### 右值参数并不等于延迟求值

表达式 `map.try_emplace(key, make_value())` 会在进入函数前调用 `make_value()`；标准只保证键冲突时不从这些参数构造 `mapped_type`。真正希望避免昂贵工厂执行时，可以先 `find`，或把惰性工厂封装在 mapped type 的构造参数协议中。需要权衡额外查找与构造成本。

相对地，`try_emplace(key, constructor_arg1, constructor_arg2)` 在缺失分支直接用参数构造值，避免先创建临时 `mapped_type`。这对包含 `mutex` 等不可移动成员的 mapped type 尤其重要，只要它能由给定参数原位构造。

`insert_or_assign` 的存在分支调用赋值而不是销毁再重建，这会保留 mapped 对象身份，但其内部资源和引用失效取决于赋值运算。观察者持有 `&it->second` 时地址通常仍是同一节点内成员，持有其内部字符串数据指针则可能因赋值重分配而失效。

## 迭代器与异常保证

提取只使被提取元素的迭代器失效，其他元素通常保持有效。节点处于句柄中时，原指向元素的指针/引用虽然可能仍指向对象，但在重新插入前使用条件受标准约束，应避免跨所有权状态长期保存。

插入节点如果比较器、哈希、分配或其他规定操作抛出，句柄所有权和容器状态应按具体重载的异常保证处理。业务代码必须保留可恢复节点对象，不能在同一复杂表达式里把它移动后丢弃所有句柄路径。

对无序容器，成功插入可能 rehash，使所有迭代器失效，但元素引用/指针的稳定性按容器规则另行判断。有序节点式容器通常保持其他元素迭代器有效。写通用容器适配器时，应读取目标容器的精确失效表，而不是把“节点容器”当统一保证。

## 选择接口的决策顺序

只读查找使用 `find`；需要缺失时默认构造并返回引用才使用 `operator[]`；仅缺失时按参数构造选择 `try_emplace`；无论是否存在都要写入选择 `insert_or_assign`；已有完整 `value_type` 时可用 `insert`/`emplace`；需要改键或跨容器保留对象身份才引入节点句柄。

接口选择会直接表达碰撞策略。把所有写入都写成 `operator[]` 会隐藏默认构造与覆盖；把所有写入写成 `emplace` 又可能让读者误判冲突时构造成本。根据业务语义选择，而不是根据名字新旧选择。

C++17 尚未提供关联容器的 `contains`；只检查存在性时使用 `find(key) != end()` 或 `count(key) != 0`。把 C++20 的便利接口误写进 C++17 示例会破坏最低标准契约。异构查找是否避免构造临时键，则由透明比较器/哈希器及具体重载支持决定。

节点句柄适合修改键，是因为键离开容器后不再参与有序/哈希不变量。通过 `const_cast` 修改容器内键会破坏查找结构并导致未定义行为；提取—修改—重插入是标准化的安全路径，且必须处理新键冲突。

## 示例解析与实践

示例提取节点、修改映射值、转移到另一个 map，再明确覆盖。工程中节点句柄适合改键、容器合并和避免昂贵对象搬迁；普通插入仍优先使用更简单接口。每次都检查重复键和分配器契约。

## 关联容器增强速查

| 接口 | 冲突/所有权语义 |
| --- | --- |
| `extract(iterator)` | 解除一个节点，返回移动专用句柄 |
| `extract(key)` | 先查找再提取，未找到返回空句柄 |
| `node.empty()` | 判断句柄是否拥有节点 |
| map `node.key()` | 节点离开容器后可安全改键 |
| map `node.mapped()` | 访问映射值 |
| `insert(node)` | 成功转移所有权；唯一键冲突会返还节点 |
| `merge(source)` | 尽量转移，唯一键冲突项留在 source |
| `try_emplace` | 仅缺键时构造 mapped value |
| `insert_or_assign` | 缺键插入，已有键对 mapped value 赋值 |
| 分配器兼容 | 不兼容节点转移不是自动深拷贝 |

## 容器增强专项审查问题

- 节点句柄分配器是否与目标容器兼容？
- 插入冲突时是否保留并处理返回的未插入节点？
- 提取后是否错误继续使用原迭代器？
- 修改 key 后是否按目标比较/哈希重新插入？
- merge 后是否检查源中仍留有冲突节点？
- `try_emplace` 是否传构造参数而非先执行昂贵工厂？
- `insert_or_assign` 的赋值分支是否满足 mapped 赋值要求？
- 无序插入 rehash 后是否仍保存旧迭代器？
- 是否误用 C++20 contains 破坏 C++17 基线？
- 改键是否使用 extract 而非 `const_cast` 破坏不变量？

## 权威资料

- [P0083R3：节点句柄](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0083r3.pdf)
- [工作草案：Associative containers](https://eel.is/c++draft/associative.reqmts)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
