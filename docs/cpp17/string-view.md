# `string_view`

`string_view` 是不拥有字符数据的轻量视图，适合只读参数、解析切片和避免临时字符串分配。

```cpp example id="cpp17-string-view" std="c++17" file="main.cpp" kind="single" compilers="all" output="cpp17"
#include <iostream>
#include <string>
#include <string_view>

std::string_view value_after(std::string_view text, char separator) {
    const auto position = text.find(separator);
    return position == std::string_view::npos ? std::string_view{} : text.substr(position + 1);
}

int main() {
    const std::string configuration = "standard=cpp17";
    const std::string_view value = value_after(configuration, '=');
    std::cout << value << '\n';
}
```

视图不延长底层字符串生命周期，也不保证以空字符结尾。不要返回指向局部 `std::string` 的视图；调用要求 C 字符串的 API 时应显式构造拥有数据的字符串。

## 表示与复杂度

`string_view` 典型实现只保存 `const char*` 和长度，复制成本为两个机器字，不分配也不复制字符。`substr` 只调整指针和长度，通常 O(1)；比较和搜索仍需检查字符，复杂度取决于操作。

它只提供只读字符视图，不拥有数据，也不会自动验证编码。一个 UTF-8 文本的 `size()` 返回字节数量，不是 Unicode 字符数量。

`string_view` 满足连续字符序列的接口预期，提供 `begin/end`、`operator[]`、`at`、`front/back`、`data/size` 等观察操作。`operator[]` 不检查边界，`at` 越界会抛出 `out_of_range`。`remove_prefix` 和 `remove_suffix` 直接移动窗口边界，不修改底层字符。

类型本身通常可平凡复制，按值传参比传 `const string_view&` 更自然。标准规定的是行为和复杂度，不强制内部恰好两个机器字；代码不应依赖具体布局或把它直接序列化。

### 字符类型、traits 与字面量

`string_view` 是 `basic_string_view<char>` 的别名；标准还提供 `wstring_view`、`u16string_view` 和 `u32string_view`。模板的第二个参数是字符 traits，比较、长度计算和搜索都通过 traits 描述字符操作。两个视图只有在字符类型和 traits 兼容时才能直接使用同一组运算，不能把不同编码宽度当作可互换字符串。

`std::literals::string_view_literals` 中的 `"text"sv` 直接按字面量的编译期长度构造视图，因此能保留字面量中的内嵌零字符；普通 `"text"` 转换则使用以零结尾的构造路径。后缀只改变结果类型，不改变字符存储仍属于静态生命周期这一事实。

许多观察和切片操作在 C++17 已是 `constexpr`，所以固定协议关键字可以在常量求值中比较或切片。不过字符数据仍必须在相应求值环境中可访问，`string_view` 也不会因此获得所有权。

```cpp example id="cpp17-string-view-consume" std="c++17" file="main.cpp" kind="single" compilers="all" output="payload=42"
#include <iostream>
#include <string_view>

bool consume_prefix(std::string_view& input, std::string_view prefix) {
    if (input.size() < prefix.size() ||
        input.compare(0, prefix.size(), prefix) != 0) {
        return false;
    }
    input.remove_prefix(prefix.size());
    return true;
}

int main() {
    std::string_view input = "value:42";
    if (!consume_prefix(input, "value:")) {
        return 1;
    }
    std::cout << "payload=" << input << '\n';
}
```

`remove_prefix` 只修改视图对象中的起始位置和长度，字符串字面量完全没有变化。这种“游标视图”适合递进式解析：每成功识别一个 token 就消费前缀，剩余输入仍由同一底层缓冲区提供。

## 构造与生命周期

可从字符串字面量、`std::string` 和指针长度构造。字面量具有静态生命周期，因此视图安全；绑定普通字符串时，字符串销毁、移动导致缓冲区变化或修改触发重分配后，视图可能悬空。

最危险的形式是从返回临时 `std::string` 的表达式构造视图：完整表达式结束时字符串销毁，视图仍看似包含原地址。`string_view` 没有引用计数，调试器也无法自动判断地址已经失效。

字符串发生重分配后，所有指向旧缓冲区的视图都失效。即使没有重分配，擦除、插入和替换也可能让视图所表示的逻辑区间改变。移动字符串后的视图是否仍可用于原内容不能靠经验判断，应依据容器失效规则并尽量避免跨修改保存视图。

视图可以合法包含嵌入的零字符，因为长度独立保存。由 `const char*` 单参数构造时长度通过字符特征计算，遇到首个零停止；要观察含零缓冲区必须使用指针加长度构造。

默认构造的空视图与指向某个合法地址但长度为零的视图在逻辑内容上相同。不要对空视图调用 `front()`、`back()` 或解引用 `begin()`。

由空指针调用单指针构造不是“创建空视图”的便捷写法，因为该构造需要计算零结尾字符序列的长度；应使用默认构造或 `{}`。指针加长度构造同样要求范围满足接口前置条件，非零长度不能配空指针，且整个范围必须可读。

返回视图时最可靠的判断不是“被返回对象是不是 `string_view`”，而是“返回范围的最终所有者是谁”。返回字符串字面量、静态表或调用者传入缓冲区的子视图可以成立；返回局部字符串、按值形参内部缓冲区或临时格式化结果的视图会悬空。成员函数返回成员字符串的视图时，契约应说明对象销毁或相关成员修改会使结果失效。

## 空字符与 C API

视图切片不保证末尾是 `\0`，`data()` 在 C++17 对空视图甚至无需指向可解引用存储。把 `data()` 直接传给只接收 C 字符串的函数可能越过视图边界读取。应使用长度感知接口，或显式构造 `std::string(view)`。

输出视图时，流插入重载会使用长度，不需要结尾零字符。与 C API 交互时优先选择同时接收指针和长度的函数；不得已调用 `strlen`/`printf("%s")` 风格接口时，应创建拥有的 `std::string` 并使用其 `c_str()`。

`data()` 返回的指针不能用于写入，即便底层所有者是可修改字符串。`string_view` 的元素类型是只读字符；需要可写连续窗口应使用迭代器对、容器引用，或 C++20 的适当 `span<char>`。

## 比较、搜索与切片

`compare` 和关系运算按字典序工作，搜索接口包括 `find`、`rfind`、`find_first_of`、`find_first_not_of` 等。未找到时返回 `npos`，它是 `size_type` 的最大值。对 `npos + 1` 做算术会环绕，因此必须先判断再计算切片起点。

`substr(pos, count)` 返回新视图；`pos > size()` 时抛出异常，`count` 超过剩余长度时自动截断。重复切片不会形成所有权链，每个结果都直接依赖原始字符存储。

哈希容器支持 `hash<string_view>`，但把视图作为长期键通常危险：键所指字符若变化，哈希和相等关系会失去容器要求的不变量。除非底层存储稳定且内容不可变，键应复制为 `string`。

不同来源但内容相同的视图按字符内容比较，而不是按地址比较。哈希也必须与内容相等保持一致，因此构造临时查找视图通常很便宜；但 C++17 标准容器的异构查找能力还取决于比较器或哈希器接口，不能仅因存在 `string_view` 就假定 `unordered_map<string, ...>` 会无分配接受它。

`copy(destination, count, pos)` 会把字符复制到调用方缓冲区并返回实际数量，但不会自动补零。它与 `substr` 的区别是前者产生字符副本、后者产生新的非拥有窗口。需要持久保存结果时，直接构造 `string(view)` 往往比手动管理裸缓冲区更安全。

### 失效规则的实用模型

可以把视图看成一对迭代器的压缩表示：任何会使对应字符指针失效的操作，也会使视图中相关指针失效。字符串 `reserve`、增长型追加或赋值可能重分配；`shrink_to_fit` 也不能被当作地址稳定承诺。即使指针没有失效，修改底层字符仍会立即改变视图观察到的内容。

相反，复制或移动“视图对象”只复制观察窗口，不影响底层字符，也不会让旧视图失效。失效与所有者的存储操作相关，而不是与视图自身的复制次数相关。

## 接口设计

同步、只读且不保存参数的函数适合按值接收 `string_view`，这样同时接受字面量和字符串且无分配。若函数要保存文本，应复制到拥有类型，或在接口契约中明确调用方生命周期。返回视图只在底层存储由更长寿命对象拥有时安全。

构造 `string_view` 本身不会把整数、路径或任意可打印对象转换成文本，它不是格式化接口。API 同时需要所有权和视图语义时，可提供分别命名的重载或在边界统一复制，避免把生命周期责任隐含在调用约定中。

异步任务、回调注册和队列会把使用时点推迟到调用返回之后，通常不应直接捕获调用者传入的视图。先复制到任务拥有的 `string`，再在任务内部建立短生命周期视图。

## 示例解析与检查清单

示例的配置字符串在视图使用期间一直存活，`substr` 只创建后半段窗口。审查时画出每个视图指向的所有者，检查所有可能重分配操作，确认下游 API 是否接受长度，并避免用视图跨异步边界携带临时数据。

## 观察接口速查

| 接口 | 复杂度/边界 |
| --- | --- |
| `data()` | 返回首字符指针，不保证切片末尾有零字符 |
| `size()/length()` | O(1) 元素数，不是 Unicode 字符数 |
| `operator[]` | 不检查边界 |
| `at()` | 越界抛 out_of_range |
| `substr(pos,n)` | O(1) 新视图，仍依赖同一所有者 |
| `remove_prefix(n)` | O(1) 移动窗口起点，需满足前置条件 |
| `remove_suffix(n)` | O(1) 缩短窗口，需满足前置条件 |
| `find` | 未找到返回 npos，先判断再做加法 |
| `copy` | 复制字符但不自动补零 |
| `hash<string_view>` | 按内容哈希；长期键仍需稳定底层存储 |

## String view 专项审查问题

- 每个视图最终指向哪个拥有者，拥有者活多久？
- 是否从临时 string 或局部按值形参返回视图？
- 所有者 reserve/append/erase 后是否仍使用旧视图？
- data() 是否错误传给要求零结尾的 C API？
- 切片是否包含嵌入零并被下游正确按长度处理？
- `npos + 1` 是否在未检查时发生无符号环绕？
- 空视图是否仍调用 front/back 或解引用 begin？
- 异步任务是否直接捕获调用者视图而未复制？
- 哈希容器长期键的字符内容是否会变化？
- UTF-8 size 是否被误解释成 Unicode 字符数量？

## 权威资料

- [N3921：string_view](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2014/n3921.html)
- [工作草案：basic_string_view](https://eel.is/c++draft/string.view)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
