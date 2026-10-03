# expected：同时表达结果与错误

阅读前建议先了解：[optional 与 variant](../cpp17/vocabulary-types.md)、[Lambda](../cpp11/lambdas.md)。本篇介绍的新增能力属于 C++23。

## 为什么不用特殊返回值

返回 -1、false 或空 optional 可以表示失败，但调用方未必知道原因。输出参数把值与状态分散到不同位置；异常适合某些边界，却不总符合“失败很常见，调用方应分支处理”的接口设计。

C++23 的 expected<T, E> 在同一个对象里保存成功值 T 或错误 E。它不是异步 Future，也不会自动记录日志或强迫调用方检查。

## 最小示例：从文本读取整数

传统接口可写 `bool parse(text, value, error)`。下面把两种结果一起返回，成功和错误路径都可以直接观察：

```cpp example id="cpp23-expected-basic" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=42, error=invalid integer" requires="__cpp_lib_expected>=202202"
#include <charconv>
#include <expected>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>
std::expected<int, std::string> parse(std::string_view text) {
    int value = 0;
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
    if (error != std::errc{} || end != text.data() + text.size())
        return std::unexpected(std::string("invalid integer"));
    return value;
}
int main() {
    auto good = parse("42");
    auto bad = parse("oops");
    if (good && !bad) std::cout << "value=" << *good << ", error=" << bad.error() << '\n';
}
```

本例检查了整个字符串是否消费完，避免把 42abc 当成成功。unexpected 明确选择错误分支，普通整数选择值分支；T 与 E 即使同型也仍需这种状态区分。optional 只有“有/无”，expected 增加可解释的错误。

本函数实际允许负整数；若业务要求正数，还要单独验证 value > 0。类型包装不会补上领域规则。

## 用 transform 与 and_then 串联步骤

这些操作常称为 monadic（按成功或失败状态串联计算）操作，不需要先学习函数式编程理论。transform 把成功值映射为普通新值，and_then 的回调返回新的 expected，失败时跳过后续成功回调。

```cpp example id="cpp23-expected-monadic" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=42, error=negative" requires="__cpp_lib_expected>=202211"
#include <cassert>
#include <expected>
#include <iostream>
#include <string>
std::expected<int, std::string> checked(int value) {
    if (value < 0) return std::unexpected(std::string("negative"));
    return value;
}
int main() {
    int calls = 0;
    auto twice = [&](int value) { ++calls; return value * 2; };
    auto good = checked(20).transform(twice)
        .and_then([](int value) { return checked(value + 2); });
    auto bad = checked(-1).transform(twice);
    assert(calls == 1);
    assert(good && !bad);
    std::cout << "value=" << *good << ", error=" << bad.error() << '\n';
}
```

错误路径没有调用 twice，错误继续传播。or_else 处理错误并返回新的 expected；transform_error 改变错误类型。接口的基础支持宏为 202202，包含这组串联操作的支持宏为 202211；不能只检查头文件存在。

## 注意事项与内部模型

使用 `*result`、`result->member` 前先确认有值；error() 只在错误状态读取。value() 在错误状态会抛 bad_expected_access<E>，并非无异常读取。expected<void, E> 表示成功时无需返回数据。C++23 不支持 expected<T&, E>，若要借用对象应明确使用指针或 reference_wrapper 及其寿命契约。

expected 始终保存值或错误，没有 variant 式的 valueless_by_exception 状态。内部通常是联合存储加状态，但布局不是标准保证；值/错误本身仍可能分配或抛异常。回调抛出的异常不会自动变成 E，要在明确的异常边界转换。

适合解析、校验和预期会失败的操作。跨 API 选择统一错误类型，避免每层重复包装；只有“是否存在”而不关心原因时 optional 更直接。

## 权威资料

- [expected](https://eel.is/c++draft/expected)
- [P0323R12：expected](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p0323r12.html)
- [P2505R5：expected 的串联操作](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p2505r5.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/expected.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
