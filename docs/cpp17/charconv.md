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

## 返回结果的完整解释

成功时 `ec` 为空，`ptr` 指向第一个未消费字符。没有可匹配字符返回 `invalid_argument`，结果值保持未修改；超出目标类型范围返回 `result_out_of_range`。只检查错误码而不检查 `ptr == last` 会错误接受 `42xyz` 这样的部分输入。

`to_chars` 写入调用方缓冲区，不添加结尾空字符。空间不足返回 `value_too_large`，调用方应扩大缓冲区或按目标类型预留可靠上限。

## 底层与性能

接口无区域设置、无分配、无异常，便于实现为紧凑整数循环或高效浮点算法，并适合在热路径批量转换。实际速度仍应测量；错误处理、缓冲区管理和后续字符串构造也属于总成本。

浮点重载的标准化和库实现成熟度比整数晚，老工具链可能缺失或行为问题更多。项目的最低编译器矩阵必须实际运行边界测试。

## 示例解析与测试清单

示例同时检查错误码和完整消费，再把整数以十六进制写入固定缓冲区，并通过返回指针构造精确长度视图。测试至少覆盖空输入、正负边界、溢出、非法字符、部分输入、最小缓冲区和不同基数。

## 权威资料

- [P0067R5：字符转换](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0067r5.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
