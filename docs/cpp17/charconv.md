# `from_chars` 与 `to_chars`

字符转换接口不依赖区域设置、不分配内存，也不通过异常报告普通解析失败，适合高性能协议和文本处理。

<!-- example id="cpp17-charconv" std="c++17" file="main.cpp" kind="single" compilers="all" output="value=42, hex=2a" -->
```cpp
#include <array>
#include <charconv>
#include <iostream>
#include <string_view>

int main() {
    constexpr std::string_view input = "42";
    int value = 0;
    const auto parsed = std::from_chars(input.data(), input.data() + input.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != input.data() + input.size()) {
        return 1;
    }

    std::array<char, 16> buffer{};
    const auto written = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value, 16);
    if (written.ec != std::errc{}) {
        return 1;
    }
    std::cout << "value=" << value << ", hex="
              << std::string_view(buffer.data(), static_cast<std::size_t>(written.ptr - buffer.data())) << '\n';
}
```

`from_chars` 不会自动要求消费完整输入，调用者应同时检查错误码和返回指针。浮点字符转换虽然属于 C++17，但早期标准库实现支持较晚，跨工具链时应特别验证。

## 设计目标

传统流转换受区域设置、格式状态和动态分配影响，`stoi` 等接口通过异常报告普通输入错误。`charconv` 面向底层缓冲区，调用方提供 `[first, last)`，函数返回停止位置和 `errc`，整个过程不要求空字符结尾。

整数 `from_chars` 默认十进制，可指定 2 到 36 的基数。它不会跳过前导空白，也不会自动识别 `0x` 前缀；这些策略必须由解析器明确处理。这种严格性让协议行为可预测。

接口只接收裸字符范围，不读取区域设置，也不接受格式流状态。对整数解析，负号只在目标是有符号类型时按规则接受，前导加号不作为普通整数模式的一部分。指定基数 16 时，输入 `0x2a` 不会把 `0x` 当作自动前缀；调用方要先处理协议前缀。

<!-- example id="cpp17-from-chars-prefix" std="c++17" file="main.cpp" kind="single" compilers="all" output="value=42, rest=ms" -->
```cpp
#include <charconv>
#include <iostream>
#include <string_view>

int main() {
    constexpr std::string_view input = "42ms";
    int value = 0;
    const auto result = std::from_chars(
        input.data(), input.data() + input.size(), value);

    if (result.ec != std::errc{}) {
        return 1;
    }

    const std::string_view rest(
        result.ptr,
        static_cast<std::size_t>(input.data() + input.size() - result.ptr));
    std::cout << "value=" << value << ", rest=" << rest << '\n';
}
```

部分消费有时是错误，有时正是解析协议所需。这里数值解析器停在 `m`，上层再解释单位后缀；若接口契约要求“整个字段只能是整数”，就必须像首个示例一样验证 `ptr == last`。

## 返回结果的完整解释

成功时 `ec` 为空，`ptr` 指向第一个未消费字符。没有可匹配字符返回 `invalid_argument`，结果值保持未修改；超出目标类型范围返回 `result_out_of_range`。只检查错误码而不检查 `ptr == last` 会错误接受 `42xyz` 这样的部分输入。

`to_chars` 写入调用方缓冲区，不添加结尾空字符。空间不足返回 `value_too_large`，调用方应扩大缓冲区或按目标类型预留可靠上限。

两个返回结构都刻意保持简单：指针给出已处理边界，`error_code` 给出无异常状态。失败不会抛出解析异常。对 `from_chars`，`invalid_argument` 时 `ptr == first`；范围错误时 `ptr` 仍指向匹配字符序列之后，便于调用方定位，但目标值不能当作成功结果使用。

对整数 `to_chars`，基数同样为 2 到 36，超过 9 的数字使用小写拉丁字母表示。无符号目标没有负号；有符号负数先输出 `-` 再输出幅值。缓冲区范围必须有效且不与被读取对象形成违反接口要求的重叠。

固定宽度整数的十进制最大字符数可以根据 `numeric_limits<T>::digits10` 留出符号和额外位，也可使用足够大的 `array<char, N>`。若转换类型是模板参数，应把容量计算封装并用最大、最小值做测试。

## 底层与性能

接口无区域设置、无分配、无异常，便于实现为紧凑整数循环或高效浮点算法，并适合在热路径批量转换。实际速度仍应测量；错误处理、缓冲区管理和后续字符串构造也属于总成本。

浮点重载的标准化和库实现成熟度比整数晚，老工具链可能缺失或行为问题更多。项目的最低编译器矩阵必须实际运行边界测试。

整数解析的概念性循环是：把当前累积值乘以基数，再加下一位，并在每步前检测是否会越界。高质量实现会利用无符号算术、分支优化或批量处理，但必须维持精确错误语义。自己手写循环很容易在最小负数、基数边界和溢出检查上出错。

整数格式化可通过重复除以基数获得逆序数字，再反转或从缓冲区后部写入。标准接口允许实现采用查表和成组数字转换。因为调用方拥有缓冲区，成功路径不需要构造临时字符串。

### 浮点重载

浮点 `to_chars` 可以选择 `chars_format::scientific`、`fixed`、`hex` 或 `general`，并可指定精度。未指定精度的某些重载要求产生足以往返恢复的最短表示。`from_chars` 的格式参数会限制可接受形式，十六进制模式的前缀规则也不能简单类推 C 库 `strtod`。

浮点舍入、极值、负零、无穷和 NaN 文本都需要以目标实现和标准规则实测。早期 C++17 标准库曾只实现整数重载，因此仅“编译器支持 C++17”不代表浮点 `charconv` 完整可用。

## 与其他转换接口的选择

`stringstream` 适合需要区域设置、流式组合和丰富格式状态的场景；`stoi` 家族接收拥有字符串并通过异常报告失败；C 函数家族常依赖结尾零字符及全局/线程区域设置。`charconv` 的优势是调用方控制边界、格式严格、无分配且错误码返回。

这也意味着更多责任落在调用方：决定是否允许空白、正号、前缀、部分消费和单位后缀，管理输出缓冲区，并把错误码映射成领域诊断。底层协议解析器通常值得集中封装这些策略，而不是在每个调用点重复指针运算。

## 示例解析与测试清单

示例同时检查错误码和完整消费，再把整数以十六进制写入固定缓冲区，并通过返回指针构造精确长度视图。测试至少覆盖空输入、正负边界、溢出、非法字符、部分输入、最小缓冲区和不同基数。

## 权威资料

- [P0067R5：字符转换](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0067r5.html)
- [工作草案：Primitive numeric conversions](https://eel.is/c++draft/charconv)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
