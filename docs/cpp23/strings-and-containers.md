# 字符串与容器的日常增强

阅读前建议先了解：[容器与迭代器](../prerequisites.md#迭代器与算法)、[string_view](../cpp17/string-view.md)。本篇介绍的新增能力属于 C++23。

## 减少查找与填充的样板代码

C++23 的 string/string_view contains 直接回答“是否包含子串”；resize_and_overwrite 允许直接填充字符串缓冲区；容器新增接收范围的构造与插入接口。三类能力分别解决查找、写入和范围传递，不能因都在标准库中就混成一个示例。

## contains：表达包含关系

传统写法 `text.find(word) != std::string_view::npos` 仍然可用；contains 让意图更直接，结果相同。

```cpp example id="cpp23-string-contains" std="c++23" file="main.cpp" kind="single" compilers="all" output="old=true, modern=true" requires="__cpp_lib_string_contains>=202011"
#include <cassert>
#include <iostream>
#include <string_view>
int main() {
    constexpr std::string_view text = "modern C++";
    const bool old_result = text.find("C++") != std::string_view::npos;
    const bool modern_result = text.contains("C++");
    assert(old_result == modern_result);
    std::cout << std::boolalpha << "old=" << old_result << ", modern=" << modern_result << '\n';
}
```

contains 不返回位置；需要位置或继续切片时用 find。搜索区分大小写，按字符序列比较，不提供 Unicode 规范化。它与 C++20 关联容器 contains 不是同一个版本新增能力。

## resize_and_overwrite：填充后报告实际长度

过去可以建立临时数组再复制到 string，或 resize 后逐字符填充。新接口把可写缓冲区和长度交给回调，回调返回最终字符串长度。

```cpp example id="cpp23-string-overwrite" std="c++23" file="main.cpp" kind="single" compilers="all" output="text=hello" requires="__cpp_lib_string_resize_and_overwrite>=202110"
#include <cstddef>
#include <iostream>
#include <string>
int main() {
    std::string text;
    text.resize_and_overwrite(8, [](char* buffer, std::size_t) noexcept {
        buffer[0] = 'h'; buffer[1] = 'e'; buffer[2] = 'l';
        buffer[3] = 'l'; buffer[4] = 'o';
        return std::size_t{5};
    });
    std::cout << "text=" << text << '\n';
}
```

申请可写长度 8，只初始化最终保留的 5 个字符并返回 5，结果为 hello。回调不要读取未初始化的字符，不要越界写；返回长度必须在允许范围内。回调抛出异常违反接口要求，本例显式 noexcept；字符串自身的分配仍可能失败。

不要保留回调里的 buffer 指针或重入修改同一个 string。接口可能降低多余的初始化与复制，但具体容量、分配次数和性能取决于实现与真实数据。

## from_range 与 insert_range：传入整个范围

旧接口传 begin/end 迭代器对。C++23 用 from_range 标签区分范围构造；不同容器还提供 insert_range、append_range、prepend_range 或 assign_range 中适合它们的操作。

```cpp example id="cpp23-container-ranges" std="c++23" file="main.cpp" kind="single" compilers="all" output="values=1 2 3 4" requires="__cpp_lib_containers_ranges>=202202"
#include <array>
#include <cassert>
#include <iostream>
#include <ranges>
#include <vector>
int main() {
    const std::array first{1, 2};
    const std::array second{3, 4};
    std::vector<int> old_values(first.begin(), first.end());
    std::vector<int> values(std::from_range, first);
    assert(values == old_values);
    values.append_range(second);
    std::cout << "values=";
    for (std::size_t index = 0; index < values.size(); ++index)
        std::cout << (index ? " " : "") << values[index];
    std::cout << '\n';
}
```

from_range 不是惰性 View，构造会消费范围并建立容器元素。vector 的 append_range 在末尾追加，旧的引用与迭代器仍遵循扩容失效规则；范围式拼写没有提供自动防悬空机制。输入范围与目标容器重叠时需查具体操作前置条件，不要默认允许 self-append。

## 右值 substr 与版本边界

C++23 为 basic_string::substr 增加右值限定重载，允许从将不再使用的字符串生成子串时复用资源。但它仍返回拥有型 string，不是 string_view；是否复用及成本不能保证。string_view::substr 一直返回借用窗口，需要源字符存活。

适合容器接口与填充缓冲区的局部改造。allocator、元素转换和异常保证仍需按具体容器检查；新拼写不改变元素是否可复制、是否会移动或是否会分配的事实。

## 权威资料

- [字符串查找](https://eel.is/c++draft/string.contains)、[字符串容量与 overwrite](https://eel.is/c++draft/string.capacity)
- [容器范围要求](https://eel.is/c++draft/container.reqmts)、[vector](https://eel.is/c++draft/vector)
- [P1072R10：resize_and_overwrite](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p1072r10.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/strings-and-containers.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
