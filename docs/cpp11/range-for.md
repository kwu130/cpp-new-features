# 范围 `for`

范围 `for` 直接遍历数组或提供 `begin`/`end` 的对象，消除了手写迭代器边界的样板代码。

<!-- example id="cpp11-range-for" std="c++11" file="main.cpp" kind="single" compilers="all" output="2 4 6" -->
```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3};
    for (auto& value : values) {
        value *= 2;
    }

    for (const auto& value : values) {
        std::cout << value << (value == values.back() ? '\n' : ' ');
    }
}
```

只读遍历通常写成 `const auto&`，原地修改写成 `auto&`。直接写 `auto` 会复制每个元素。遍历期间不要执行可能使当前迭代器失效的容器修改操作。

## 学习目标与展开模型

范围 `for` 不是一种新的容器协议，而是编译器生成普通迭代器循环的语法糖。理解展开形式有助于判断生命周期、查找 `begin`/`end` 的方式以及修改容器时的风险。

C++11 的概念性展开可写成：

```text
auto&& range = range_expression;
for (auto begin = begin-expr, end = end-expr; begin != end; ++begin) {
    item-declaration = *begin;
    loop-body
}
```

数组使用内建边界；类类型优先查找成员 `begin()`/`end()`；其他类型通过关联查找找到自由函数。这里不是简单调用 `std::begin`，因此为自定义类型实现同命名自由函数时应放在类型关联命名空间。

隐藏 range 变量保证范围表达式只求值一次。`for (auto x : make_range())` 不会每次迭代重新调用工厂；begin/end 从保存的结果取得。工厂副作用发生在进入循环时。

C++11 概念展开中的 begin 与 end 常在同一声明中推导，因而要求相同类型。自定义 sentinel 与 iterator 异型结束协议要到 C++17 范围 for 放宽后才自然支持。

### 名称查找优先级

若类作用域中同时能找到名为 begin 和 end 的成员名称，展开走成员形式，即使它们不是可调用函数（例如枚举成员），可能阻止 ADL 自由函数方案。为范围类型选择这两个名称时应保留协议用途。

自由 begin/end 通过 ADL 在类型关联命名空间查找，不做普通无条件 `std::begin(range)` 调用。适配第三方类型时，把非成员函数放进该类型命名空间要遵守扩展权限；不能随意向 std 添加普通重载。

内建数组由编译器知道元素数量，不调用 begin/end。数组必须是完整已知界类型；退化为指针后长度信息消失，裸指针不能单独进入范围 for。

## 生命周期与引用选择

隐藏变量 `auto&& range` 会延长直接绑定临时范围的生命周期。例如遍历一个按值返回的 `vector` 是安全的。但在 C++23 之前，临时范围内部某些中间临时对象的生命周期未必一并延长；链式调用返回内部引用时尤其要小心。

循环变量决定每次解引用后的行为：

- `auto item`：复制元素，修改副本不影响容器。
- `auto& item`：引用可修改元素，不能绑定返回纯右值的迭代器代理。
- `const auto& item`：不复制且只读，是最常用选择。
- `auto&& item`：保留代理和值类别，泛型范围代码更通用。

循环变量声明在每次迭代建立并在循环体结束销毁。`auto item` 对昂贵元素反复复制/析构，`const auto&` 通常避免；但若迭代器解引用返回临时值，const 引用只延长该次迭代临时寿命，不能保存到循环外。

`auto&` 对 `vector<bool>` 等代理迭代器可能无法绑定，因为解引用返回临时代理对象；`auto&&` 可绑定代理并保留写入能力。通用算法不能假定 range reference 永远是 `value_type&`。

遍历 map 时元素类型是 `pair<const Key, Mapped>`。若显式写错成 `pair<Key,Mapped> const&`，可能创建每轮转换临时并隐藏复制；用 `const auto&` 能准确匹配真实元素类型。

### 临时范围的细节

隐藏 `auto&& range` 会延长直接绑定到它的临时容器寿命，所以按值返回 vector 后遍历是安全的。但若范围表达式先调用返回内部引用的成员，拥有临时可能在绑定前已析构，C++11 不会递归延长所有中间对象。

安全做法是把拥有结果先命名成局部变量，再从它取得子范围/引用。不要把“范围 for 会延长临时”概括成所有链式表达式都安全。

## 性能与失效规则

语法糖本身没有额外运行时开销，`begin` 和 `end` 通常只求值一次。真正成本来自循环变量是否复制，以及迭代器操作。容器扩容、删除当前元素或重排元素可能使隐藏迭代器失效；此时应改用显式迭代器循环并采用该容器规定的删除模式。

缓存 end 意味着循环中即使某种容器插入不使 begin 失效，原 end 是否仍代表新范围也要按失效规则分析。不得用范围 for 实现“遍历时不断 push_back 直到条件”，vector 扩容和缓存终点都会破坏逻辑。

修改元素值在迭代器稳定且不改变容器结构时通常安全；修改关联容器 key 不允许，mapped value 可按锁/单线程协议修改。排序/rehash/swap 等结构操作应在循环外进行。

编译器生成的循环与手写等价形式拥有相同向量化机会。`auto` 复制小标量可能比引用更易优化，性能选择仍应结合元素类型和生成代码，而非绝对规则。

## 示例解析与检查清单

主示例第一轮使用 `auto&` 原地加倍，第二轮使用 `const auto&` 读取。实践中还要确认范围表达式只求值一次是否符合预期、自定义 `begin/end` 是否返回兼容哨兵，以及循环体是否改变容器结构。

## 为用户类型提供范围协议

自定义类型不必继承任何基类。只要能通过成员或关联查找得到 `begin` 与 `end`，且迭代器支持比较、递增和解引用，就可以进入范围 `for`。成员方案适合类型自己拥有遍历语义；自由函数方案适合适配无法修改的类型。

C++11 展开中开始和结束迭代器需要能以同一 `auto` 声明形式表示；C++17 放宽为不同类型，为哨兵范围铺路。编写以 C++11 为最低版本的类型时，不应依赖异构 sentinel。

<!-- example id="cpp11-custom-range" std="c++11" file="main.cpp" kind="single" compilers="all" output="sum=10" -->
```cpp
#include <cstddef>
#include <iostream>

class Numbers {
public:
    Numbers(int* data, std::size_t size) : data_(data), size_(size) {}
    int* begin() { return data_; }
    int* end() { return data_ + size_; }

private:
    int* data_;
    std::size_t size_;
};

int main() {
    int storage[] = {1, 2, 3, 4};
    Numbers numbers(storage, 4);
    int sum = 0;
    for (const int value : numbers) {
        sum += value;
    }
    std::cout << "sum=" << sum << '\n';
}
```

这个范围只借用外部数组，`Numbers` 不能比 `storage` 活得更久。它的迭代器是裸指针，因此元素连续、随机访问且没有额外对象；这属于该实现选择，不是范围 `for` 对所有迭代器的要求。

const 对象遍历需要 const 限定的 begin/end，返回只读或合适迭代器。只提供非 const 成员会让 `const Numbers` 不能范围遍历；接口测试应覆盖两种 cv 形式。

最小迭代器需支持前置递增、解引用和与 end 比较；返回类型/操作的精确要求由展开表达式决定。若还要进入标准算法，应进一步满足对应 Iterator 要求，能用于 range for 不等于完整 ForwardIterator。

借用型范围应在类型名/文档中明确不拥有 data，复制范围只复制指针和长度。所有者移动/销毁/重分配后，范围和已取迭代器一并失效。

## 删除元素时为什么要回到显式循环

范围 `for` 隐藏了当前迭代器，无法接收 `erase` 返回的下一个有效迭代器。对 `vector`、`list`、关联容器执行条件删除时，应使用该容器规定的显式迭代器模式，或后续标准提供的 `erase_if`。在隐藏循环内修改结构会让下一次递增访问失效状态。

vector 常用 erase-remove 惯用法批量删除；关联/链表容器常写 `it = container.erase(it)`，保留分支才 `++it`。不同容器 erase 返回规则和复杂度需要查具体版本。

仅 `break`/`continue` 不会破坏隐藏迭代器；保存 `&item` 到循环外则依赖容器后续稳定性。代码评审应把循环体中所有可能间接修改容器的函数调用也纳入检查。

## 循环变量与范围速查

| 写法 | 元素语义 |
| --- | --- |
| `for (auto x : r)` | 每轮复制/移动一个元素值 |
| `for (auto& x : r)` | 可修改原元素，不接受 const 元素修改 |
| `for (const auto& x : r)` | 只读引用并避免大型元素复制 |
| `for (auto&& x : r)` | 泛型代码保留代理/引用类别 |
| 内建数组 | 编译器直接使用数组边界 |
| 普通类范围 | 按规则查找 begin/end 成员或 ADL 函数 |
| 临时完整范围 | 循环绑定的范围对象寿命按规则覆盖循环 |
| 返回内部引用的临时链 | 内部子对象仍可能先悬空，需单独审计 |
| 循环内结构修改 | 依具体容器失效规则，常导致迭代器失效 |
| `vector<bool>` | 解引用是代理，`auto&`/`auto&&` 行为需测试 |

## Range-for 专项审查

- 循环变量是否因按值导致昂贵复制或切片？
- 需要修改元素时是否明确使用非 const 引用？
- 泛型代理元素是否应使用 auto&&？
- 临时范围内部子对象是否在整个循环期间仍存活？
- 自定义 begin/end 是否通过正确成员/ADL 路径找到？
- begin 与 end 类型是否满足 C++11 同型要求？
- 循环体修改容器是否使当前迭代器失效？
- vector<bool> 等代理是否被误当成真正 bool&？
- 锁保护范围是否覆盖整个遍历而非只获取 begin？
- 需要索引时是否应改用显式迭代而非隐藏计数？

## 权威资料

- [范围 for 语句](https://eel.is/c++draft/stmt.ranged)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
