# `string_view`

`string_view` 是不拥有字符数据的轻量视图，适合只读参数、解析切片和避免临时字符串分配。

<!-- example id="cpp17-string-view" std="c++17" file="main.cpp" kind="single" compilers="all" output="cpp17" -->
```cpp
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

## 构造与生命周期

可从字符串字面量、`std::string` 和指针长度构造。字面量具有静态生命周期，因此视图安全；绑定普通字符串时，字符串销毁、移动导致缓冲区变化或修改触发重分配后，视图可能悬空。

最危险的形式是从返回临时 `std::string` 的表达式构造视图：完整表达式结束时字符串销毁，视图仍看似包含原地址。`string_view` 没有引用计数，调试器也无法自动判断地址已经失效。

## 空字符与 C API

视图切片不保证末尾是 `\0`，`data()` 在 C++17 对空视图甚至无需指向可解引用存储。把 `data()` 直接传给只接收 C 字符串的函数可能越过视图边界读取。应使用长度感知接口，或显式构造 `std::string(view)`。

## 接口设计

同步、只读且不保存参数的函数适合按值接收 `string_view`，这样同时接受字面量和字符串且无分配。若函数要保存文本，应复制到拥有类型，或在接口契约中明确调用方生命周期。返回视图只在底层存储由更长寿命对象拥有时安全。

## 示例解析与检查清单

示例的配置字符串在视图使用期间一直存活，`substr` 只创建后半段窗口。审查时画出每个视图指向的所有者，检查所有可能重分配操作，确认下游 API 是否接受长度，并避免用视图跨异步边界携带临时数据。
