# `from_chars` 与 `to_chars`

阅读前建议先了解：[字符串视图](string-view.md)及指针半开区间；不需要先学区域设置实现。本篇介绍的新增能力属于 C++17；后续版本差异会另行标注。

## 学习目标与传统转换接口的取舍

C++14 的字符串流表达力强，但会携带区域设置和格式状态，且可能分配；`stoi` 一族接受字符串对象并用异常报告普通输入失败；`strtol` 一族依赖 C 风格终止和全局错误状态。协议解析和批量序列化通常更需要明确边界、无分配以及可直接检查的错误结果。

C++17 的 `from_chars` 与 `to_chars` 在调用方提供的字符范围上工作，不跳过空白、不要求空字符结尾、不使用区域设置，也不通过异常报告格式错误。它们是低层转换原语，不负责字段切分、前缀识别或输出缓冲区增长。

读完后，你应能同时检查错误码与停止指针，处理部分消费和缓冲区不足，并理解整数与浮点重载的格式及工具链边界。

## 最小接口

```text
auto parsed = std::from_chars(first, last, value, base);
auto written = std::to_chars(first, last, value, base);

// result.ptr：停止或写入结束位置
// result.ec ：std::errc{}、invalid_argument 或 result_out_of_range 等
```

## 从高层字符串转换到区间解析

以下片段只对比写法；完整、可运行的程序见后文。

```text
// 传统接口：std::stoi(text)，可能抛异常
// C++17：接收明确的字符区间，并返回位置与错误码
int value = 0;
auto result = std::from_chars(first, last, value);
if (result.ec == std::errc{} && result.ptr == last) { /* 完整解析 */ }
```

from_chars 不自动跳过前导空白，行为不等同于 stoi；成功也不一定消费整串。适合协议与配置中的可控数字区间，避免区域设置和转换接口自身的分配；需要本地化、空白容忍或详细错误信息时，应在上层明确处理。to_chars 则要求调用者提供足够输出空间。

## 第一个完整示例

示例要求十进制输入被完整消费，再把同一个整数写成十六进制。输出缓冲区由调用方拥有，最终视图长度由返回指针计算。

```cpp example id="cpp17-charconv" std="c++17" file="main.cpp" kind="single" compilers="all" output="value=42, hex=2a"
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

程序输出 `value=42, hex=2a`。解析成功只说明形成了一个值；首个检查还要求 `ptr` 到达输入末尾。写入成功后，`written.ptr - buffer.data()` 才是有效字符数。浮点字符转换虽然属于 C++17，但早期标准库实现支持较晚，跨工具链时应特别验证。

## 设计目标

传统流转换受区域设置、格式状态和动态分配影响，`stoi` 等接口通过异常报告普通输入错误。`charconv` 面向底层缓冲区，调用方提供 `[first, last)`，函数返回停止位置和 `errc`，整个过程不要求空字符结尾。

整数 `from_chars` 默认十进制，可指定 2 到 36 的基数。它不会跳过前导空白，也不会自动识别 `0x` 前缀；这些策略必须由解析器明确处理。这种严格性让协议行为可预测。

接口只接收裸字符范围，不读取区域设置，也不接受格式流状态。对整数解析，负号只在目标是有符号类型时按规则接受，前导加号不作为普通整数模式的一部分。指定基数 16 时，输入 `0x2a` 不会把 `0x` 当作自动前缀；调用方要先处理协议前缀。

```cpp example id="cpp17-from-chars-prefix" std="c++17" file="main.cpp" kind="single" compilers="all" output="value=42, rest=ms"
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

### 整数语法的精确边界

整数 `from_chars` 的匹配模式刻意接近 `strtol` 的 C 区域设置语法，但去掉了前导空白，并且只有负号在有符号目标中按规则识别。基数不是零，因此没有“根据前缀自动推断八进制或十六进制”的模式。若协议允许 `+42`、`0x2a` 或下划线分隔，必须先由上层语法明确消费或拒绝这些部分。

解析到目标类型范围之外时，函数报告 `result_out_of_range` 且不会把截断、饱和或回绕值当作成功结果。使用较宽临时类型再窄化不是等价替代，因为它可能接受协议本应拒绝的表示。应直接以最终目标类型调用并检查错误。

`char` 的符号性由实现决定。解析字节型整数时，选择 `signed char`、`unsigned char` 或固定宽度整数可以更清楚地表达范围；把文本数字解析到普通 `char` 容易产生平台差异。

## 底层与性能

接口无区域设置、无分配、无异常，便于实现为紧凑整数循环或高效浮点算法，并适合在热路径批量转换。实际速度仍应测量；错误处理、缓冲区管理和后续字符串构造也属于总成本。

浮点重载的标准化和库实现成熟度比整数晚，老工具链可能缺失或行为问题更多。项目的最低编译器矩阵必须实际运行边界测试。

整数解析的概念性循环是：把当前累积值乘以基数，再加下一位，并在每步前检测是否会越界。高质量实现会利用无符号算术、分支优化或批量处理，但必须维持精确错误语义。自己手写循环很容易在最小负数、基数边界和溢出检查上出错。

整数格式化可通过重复除以基数获得逆序数字，再反转或从缓冲区后部写入。标准接口允许实现采用查表和成组数字转换。因为调用方拥有缓冲区，成功路径不需要构造临时字符串。

### 浮点重载

浮点 `to_chars` 可以选择 `chars_format::scientific`、`fixed`、`hex` 或 `general`，并可指定精度。未指定精度的某些重载要求产生足以往返恢复的最短表示。`from_chars` 的格式参数会限制可接受形式，十六进制模式的前缀规则也不能简单类推 C 库 `strtod`。

浮点舍入、极值、负零、无穷和 NaN 文本都需要以目标实现和标准规则实测。早期 C++17 标准库曾只实现整数重载，因此仅“编译器支持 C++17”不代表浮点 `charconv` 完整可用。

`chars_format::scientific` 要求指数部分，`fixed` 不接受指数部分；`general` 允许实现按规则选择定点或科学计数，按位组合 `fixed | scientific` 则表示两种形式均可接受。十六进制浮点模式并不把 `0x` 当作匹配模式的一部分，这一点与很多 C 风格解析经验不同。

未指定精度的浮点 `to_chars` 以“往返到同一类型”的表示要求为核心，并在满足条件的表示中遵循最短及舍入规则；指定精度后则按格式和精度生成。它不是面向最终用户的本地化排版工具，不提供千位分隔、本地小数点或字段宽度。

### 缓冲区策略与批处理

调用方提供缓冲区使接口适合栈上固定数组、网络包空闲区或批处理大缓冲区。若空间不足，`to_chars` 不会自动分配或增长容器；一种稳健封装是在足够保守的固定上限内写入，再按返回指针追加到输出。对任意精度或复杂浮点格式，应提供可重试增长路径。

批量解析时可以让上一项返回的 `ptr` 成为下一步词法分析起点，避免创建子字符串。此时要明确分隔符由哪一层消费，并保证每轮都推进指针，否则错误恢复循环可能停在同一字符无限重试。

## 与其他转换接口的选择

`stringstream` 适合需要区域设置、流式组合和丰富格式状态的场景；`stoi` 家族接收拥有字符串并通过异常报告失败；C 函数家族常依赖结尾零字符及全局/线程区域设置。`charconv` 的优势是调用方控制边界、格式严格、无分配且错误码返回。

这也意味着更多责任落在调用方：决定是否允许空白、正号、前缀、部分消费和单位后缀，管理输出缓冲区，并把错误码映射成领域诊断。底层协议解析器通常值得集中封装这些策略，而不是在每个调用点重复指针运算。

## 示例解析与测试清单

示例同时检查错误码和完整消费，再把整数以十六进制写入固定缓冲区，并通过返回指针构造精确长度视图。测试至少覆盖空输入、正负边界、溢出、非法字符、部分输入、最小缓冲区和不同基数。

## 转换结果速查

| 情况 | `ptr` / `ec` 语义 |
| --- | --- |
| 完整成功 | ptr == last，ec 为空 |
| 部分成功 | ptr 指向首个未消费字符，ec 为空 |
| 无匹配字符 | ptr == first，`invalid_argument` |
| 超出目标范围 | `result_out_of_range`，目标值不可当成功使用 |
| 整数前导空白 | 不跳过，通常无匹配 |
| 整数前导 `+` | 普通整数语法不自动接受 |
| base=16 的 `0x` | 不自动消费前缀 |
| `to_chars` 成功 | ptr 指向写入末尾，不补 `\0` |
| 输出空间不足 | `value_too_large`，调用方需扩大缓冲区 |
| 浮点格式 | 受 `chars_format` 与标准库实现成熟度影响 |

## Charconv 专项审查问题

- 是否同时检查 ec 和要求的完整消费 ptr==last？
- 前导空白、正号、进制前缀由哪一层处理？
- 部分消费是协议需要还是必须拒绝的尾随垃圾？
- 范围错误后是否错误使用未成功的目标值？
- `to_chars` 缓冲区容量是否覆盖符号和极值？
- 输出后是否错误假设库补写了零字符？
- base 是否严格位于 2 到 36？
- 浮点格式/精度是否与往返要求一致？
- 最低标准库是否真实实现所用浮点重载？
- 批量解析错误路径是否保证指针继续推进或退出？

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp17/charconv.md
```

## 权威资料

- [P0067R5：字符转换](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0067r5.html)
- [工作草案：Primitive numeric conversions](https://eel.is/c++draft/charconv)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
