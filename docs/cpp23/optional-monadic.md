# optional 串联操作：减少有值检查的嵌套

阅读前建议先了解：[optional](../cpp17/vocabulary-types.md)、[Lambda](../cpp11/lambdas.md)。本篇介绍的新增能力属于 C++23。

## 为什么需要它

optional 是 C++17 类型，C++23 增加 and_then、transform 和 or_else。它们处理连续几步“有值才继续”的流程，让每层 if 不必重复；不会增加错误原因，也不会把 optional 变成 expected。

以前可以这样写，片段只展示流程：

```text
std::optional<int> result;
if (input) {
    auto checked = positive(*input);
    if (checked) result = *checked * 2;
}
```

## 最小示例：校验后再映射

```cpp example id="cpp23-optional-monadic" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=42, fallback=0" requires="__cpp_lib_optional>=202110"
#include <cassert>
#include <iostream>
#include <optional>
std::optional<int> positive(int value) {
    if (value <= 0) return std::nullopt;
    return value;
}
int main() {
    const std::optional<int> input = 21;
    int calls = 0;
    auto pipeline = [&](std::optional<int> value) {
        return value.and_then(positive)
            .transform([&](int number) { ++calls; return number * 2; });
    };
    auto good = pipeline(input);
    auto empty = pipeline(std::nullopt).or_else([] { return std::optional<int>{0}; });
    assert(calls == 1);
    std::cout << "value=" << good.value() << ", fallback=" << empty.value() << '\n';
}
```

and_then 的回调返回 optional，避免形成嵌套的 optional<optional<int>>。transform 的回调返回普通值，由库包装新 optional。空输入会跳过这两个回调；or_else 只在无值时提供备用 optional，回调没有值参数。

这里正常路径与传统嵌套 if 的结果相同，区别是流程的组合方式。assert 检查空输入没有额外执行成功映射；不会为了演示而读取空值。

## 接口与适用场景

| 操作 | 回调输入 | 回调结果 | 执行条件 |
| --- | --- | --- | --- |
| and_then | 当前值 | optional<U> | 有值 |
| transform | 当前值 | 普通 U | 有值 |
| or_else | 无参数 | 与当前接口要求匹配的 optional | 无值 |

适合多个可选查找、校验和转换。只有一次简单判断时 if 更易读；需要区分无输入、格式错误和超范围时应考虑 [expected](expected.md)。

## 引用、异常与成本

操作有不同 cv/ref 重载，回调接收值的方式与调用对象有关。对左值 optional 调用时可借用内部值，对右值调用时可移动；不要把回调返回的引用当成得到自动寿命管理的新对象。C++23 optional 不支持引用元素类型。

回调抛出的异常继续传播，不会自动转成 nullopt。value_or 的参数会在函数调用前求值，昂贵的备用操作需要惰性执行时，使用 or_else 更适合。链式写法仍按步骤调用代码，不能保证更少分配或更快。

原 optional 的 bool 检查、解引用与 value() 行为保持不变。C++26 的 optional 作为范围等后续能力不属于本篇。

## 权威资料

- [optional 串联操作](https://eel.is/c++draft/optional.monadic)
- [P0798R8](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p0798r8.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/optional-monadic.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
